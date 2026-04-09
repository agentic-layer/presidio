# Combined REST API server for presidio analyzer and anonymizer.
# Analyzer routes adapted from:
#   https://github.com/microsoft/presidio/blob/main/presidio-analyzer/app.py
# Anonymizer routes adapted from:
#   https://github.com/microsoft/presidio/blob/main/presidio-anonymizer/app.py

import json
import logging
import os
from logging.config import fileConfig
from pathlib import Path

from flask import Flask, Response, request
from otel import setup_otel
from presidio_analyzer import (
    AnalyzerEngine,
    AnalyzerEngineProvider,
    AnalyzerRequest,
    BatchAnalyzerEngine,
)
from presidio_anonymizer import AnonymizerEngine, DeanonymizeEngine
from presidio_anonymizer.entities import InvalidParamError
from presidio_anonymizer.services.app_entities_convertor import AppEntitiesConvertor
from werkzeug.exceptions import BadRequest, HTTPException

DEFAULT_PORT = "8000"
DEFAULT_BATCH_SIZE = "500"
DEFAULT_N_PROCESS = "1"

LOGGING_CONF_FILE = "logging.ini"

CONTENT_TYPE_JSON = "application/json"


class Server:
    """HTTP server combining Presidio Analyzer and Anonymizer."""

    def __init__(self):
        fileConfig(Path(Path(__file__).parent, LOGGING_CONF_FILE))
        self.logger = logging.getLogger("presidio")
        self.logger.setLevel(os.environ.get("LOG_LEVEL", self.logger.level))
        setup_otel()
        self.app = Flask(__name__)

        conf_dir = Path(__file__).parent / "conf"
        analyzer_conf_file = os.environ.get(
            "ANALYZER_CONF_FILE", str(conf_dir / "analyzer.yaml")
        )
        nlp_engine_conf_file = os.environ.get(
            "NLP_CONF_FILE", str(conf_dir / "nlp.yaml")
        )
        recognizer_registry_conf_file = os.environ.get(
            "RECOGNIZER_REGISTRY_CONF_FILE", str(conf_dir / "recognizers.yaml")
        )

        self.logger.info("Starting analyzer engine")
        self.engine: AnalyzerEngine = AnalyzerEngineProvider(
            analyzer_engine_conf_file=analyzer_conf_file,
            nlp_engine_conf_file=nlp_engine_conf_file,
            recognizer_registry_conf_file=recognizer_registry_conf_file,
        ).create_engine()
        self.batch_engine = BatchAnalyzerEngine(self.engine)

        self.logger.info("Starting anonymizer engine")
        self.anonymizer = AnonymizerEngine()
        self.deanonymize_engine = DeanonymizeEngine()

        self._register_routes()

    def _register_routes(self):
        self._register_health_routes()
        self._register_analyzer_routes()
        self._register_anonymizer_routes()
        self._register_error_handlers()

    def _register_health_routes(self):
        @self.app.route("/health")
        def health() -> str:
            """Return basic health probe result."""
            return "Presidio service is up"

    def _validate_analyze_request(self, req_data: AnalyzerRequest):
        if not req_data.text:
            raise ValueError("No text provided")
        if not req_data.language:
            raise ValueError("No language provided")
        self.engine.get_supported_entities(req_data.language)

    def _run_analysis(self, req_data: AnalyzerRequest) -> Response:
        batch_request = isinstance(req_data.text, list)
        batch = req_data.text if batch_request else [req_data.text]

        iterator = self.batch_engine.analyze_iterator(
            texts=batch,
            batch_size=min(
                len(batch),
                int(os.environ.get("BATCH_SIZE", DEFAULT_BATCH_SIZE))
            ),
            language=req_data.language,
            correlation_id=req_data.correlation_id,
            score_threshold=req_data.score_threshold,
            entities=req_data.entities,
            return_decision_process=req_data.return_decision_process,
            ad_hoc_recognizers=req_data.ad_hoc_recognizers,
            context=req_data.context,
            allow_list=req_data.allow_list,
            allow_list_match=req_data.allow_list_match,
            regex_flags=req_data.regex_flags,
            n_process=min(
                len(batch),
                int(os.environ.get("N_PROCESS", DEFAULT_N_PROCESS))
            )
        )
        results = []
        for recognizer_result_list in iterator:
            _exclude_attributes_from_dto(recognizer_result_list)
            results.append(recognizer_result_list)

        return Response(
            json.dumps(
                results if batch_request else results[0],
                default=lambda o: o.to_dict(),
                sort_keys=True,
            ),
            content_type=CONTENT_TYPE_JSON,
        )

    def _register_analyzer_routes(self):
        @self.app.route("/analyze", methods=["POST"])
        def analyze() -> Response:
            """Execute the analyzer function."""
            try:
                req_data = AnalyzerRequest(request.get_json())
                self.logger.debug("Analyze request: %s", request.get_json())
                self._validate_analyze_request(req_data)
                response = self._run_analysis(req_data)
                self.logger.debug("Analyze response: %s", response.get_data(as_text=True))
                return response
            except TypeError as te:
                error_msg = (
                    f"Failed to parse /analyze request "
                    f"for AnalyzerEngine.analyze(). {te.args[0]}"
                )
                self.logger.error(error_msg)
                return Response(
                    json.dumps({"error": error_msg}),
                    status=400,
                    content_type=CONTENT_TYPE_JSON,
                )
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during execution of "
                    f"AnalyzerEngine.analyze(). {e}"
                )
                return Response(
                    json.dumps({"error": e.args[0]}),
                    status=500,
                    content_type=CONTENT_TYPE_JSON,
                )

        @self.app.route("/recognizers", methods=["GET"])
        def recognizers() -> Response:
            """Return a list of supported recognizers."""
            language = request.args.get("language")
            try:
                recognizers_list = self.engine.get_recognizers(language)
                names = [o.name for o in recognizers_list]
                return Response(
                    json.dumps(names),
                    status=200,
                    content_type=CONTENT_TYPE_JSON,
                )
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during execution of "
                    f"AnalyzerEngine.get_recognizers(). {e}"
                )
                return Response(
                    json.dumps({"error": e.args[0]}),
                    status=500,
                    content_type=CONTENT_TYPE_JSON,
                )

        @self.app.route("/supportedentities", methods=["GET"])
        def supported_entities() -> Response:
            """Return a list of supported entities."""
            language = request.args.get("language")
            try:
                entities_list = self.engine.get_supported_entities(language)
                return Response(
                    json.dumps(entities_list),
                    status=200,
                    content_type=CONTENT_TYPE_JSON,
                )
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during execution of "
                    f"AnalyzerEngine.supported_entities(). {e}"
                )
                return Response(
                    json.dumps({"error": e.args[0]}),
                    status=500,
                    content_type=CONTENT_TYPE_JSON,
                )

    def _register_anonymizer_routes(self):
        @self.app.route("/anonymize", methods=["POST"])
        def anonymize() -> Response:
            content = request.get_json()
            if not content:
                raise BadRequest("Invalid request json")

            anonymizers_config = AppEntitiesConvertor.operators_config_from_json(
                content.get("anonymizers")
            )
            if AppEntitiesConvertor.check_custom_operator(anonymizers_config):
                raise BadRequest("Custom type anonymizer is not supported")

            analyzer_results = AppEntitiesConvertor.analyzer_results_from_json(
                content.get("analyzer_results")
            )
            self.logger.debug("Anonymize request: %s", content)
            anonymizer_result = self.anonymizer.anonymize(
                text=content.get("text", ""),
                analyzer_results=analyzer_results,
                operators=anonymizers_config,
            )
            self.logger.debug("Anonymize response: %s", anonymizer_result.to_json())
            return Response(anonymizer_result.to_json(), mimetype=CONTENT_TYPE_JSON)

        @self.app.route("/deanonymize", methods=["POST"])
        def deanonymize() -> Response:
            content = request.get_json()
            if not content:
                raise BadRequest("Invalid request json")
            text = content.get("text", "")
            deanonymize_entities = AppEntitiesConvertor.deanonymize_entities_from_json(
                content
            )
            deanonymize_config = AppEntitiesConvertor.operators_config_from_json(
                content.get("deanonymizers")
            )
            self.logger.debug("Deanonymize request: %s", content)
            deanonymized_response = self.deanonymize_engine.deanonymize(
                text=text, entities=deanonymize_entities, operators=deanonymize_config
            )
            self.logger.debug("Deanonymize response: %s", deanonymized_response.to_json())
            return Response(
                deanonymized_response.to_json(), mimetype=CONTENT_TYPE_JSON
            )

        @self.app.route("/anonymizers", methods=["GET"])
        def anonymizers() -> Response:
            """Return a list of supported anonymizers."""
            return Response(
                json.dumps(self.anonymizer.get_anonymizers()),
                content_type=CONTENT_TYPE_JSON,
            )

        @self.app.route("/deanonymizers", methods=["GET"])
        def deanonymizers() -> Response:
            """Return a list of supported deanonymizers."""
            return Response(
                json.dumps(self.deanonymize_engine.get_deanonymizers()),
                content_type=CONTENT_TYPE_JSON,
            )

    def _register_error_handlers(self):
        @self.app.errorhandler(InvalidParamError)
        def invalid_param(err) -> Response:
            self.logger.warning(
                f"Request failed with parameter validation error: {err.err_msg}"
            )
            return Response(
                json.dumps({"error": err.err_msg}),
                status=422,
                content_type=CONTENT_TYPE_JSON,
            )

        @self.app.errorhandler(HTTPException)
        def http_exception(e) -> Response:
            return Response(
                json.dumps({"error": e.description}),
                status=e.code,
                content_type=CONTENT_TYPE_JSON,
            )

        @self.app.errorhandler(Exception)
        def server_error(e) -> Response:
            self.logger.error(f"A fatal error occurred during execution: {e}")
            return Response(
                json.dumps({"error": "Internal server error"}),
                status=500,
                content_type=CONTENT_TYPE_JSON,
            )


def _exclude_attributes_from_dto(recognizer_result_list):
    excluded_attributes = ["recognition_metadata"]
    for result in recognizer_result_list:
        for attr in excluded_attributes:
            if hasattr(result, attr):
                delattr(result, attr)


def create_app():
    """Create and return the combined presidio Flask application."""
    server = Server()
    return server.app


if __name__ == "__main__":
    """Run the app for development"""
    app = create_app()
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    app.run(host="0.0.0.0", port=port)
