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
from typing import Tuple

from flask import Flask, Response, jsonify, request
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

DEFAULT_PORT = "3000"
DEFAULT_BATCH_SIZE = "500"
DEFAULT_N_PROCESS = "1"

LOGGING_CONF_FILE = "logging.ini"


class Server:
    """HTTP server combining Presidio Analyzer and Anonymizer."""

    def __init__(self):
        fileConfig(Path(Path(__file__).parent, LOGGING_CONF_FILE))
        self.logger = logging.getLogger("presidio")
        self.logger.setLevel(os.environ.get("LOG_LEVEL", self.logger.level))
        self.app = Flask(__name__)

        analyzer_conf_file = os.environ.get("ANALYZER_CONF_FILE")
        nlp_engine_conf_file = os.environ.get("NLP_CONF_FILE")
        recognizer_registry_conf_file = os.environ.get("RECOGNIZER_REGISTRY_CONF_FILE")

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
        app = self.app

        @app.route("/health")
        def health() -> str:
            """Return basic health probe result."""
            return "Presidio service is up"

        # --- Analyzer routes ---

        @app.route("/analyze", methods=["POST"])
        def analyze() -> Tuple[str, int]:
            """Execute the analyzer function."""
            try:
                req_data = AnalyzerRequest(request.get_json())
                if not req_data.text:
                    raise Exception("No text provided")

                batch_request = isinstance(req_data.text, list)
                batch = req_data.text if batch_request else [req_data.text]

                if not req_data.language:
                    raise Exception("No language provided")
                else:
                    self.engine.get_supported_entities(req_data.language)

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
                    content_type="application/json",
                )
            except TypeError as te:
                error_msg = (
                    f"Failed to parse /analyze request "
                    f"for AnalyzerEngine.analyze(). {te.args[0]}"
                )
                self.logger.error(error_msg)
                return jsonify(error=error_msg), 400
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during execution of "
                    f"AnalyzerEngine.analyze(). {e}"
                )
                return jsonify(error=e.args[0]), 500

        @app.route("/recognizers", methods=["GET"])
        def recognizers() -> Tuple[str, int]:
            """Return a list of supported recognizers."""
            language = request.args.get("language")
            try:
                recognizers_list = self.engine.get_recognizers(language)
                names = [o.name for o in recognizers_list]
                return jsonify(names), 200
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during execution of "
                    f"AnalyzerEngine.get_recognizers(). {e}"
                )
                return jsonify(error=e.args[0]), 500

        @app.route("/supportedentities", methods=["GET"])
        def supported_entities() -> Tuple[str, int]:
            """Return a list of supported entities."""
            language = request.args.get("language")
            try:
                entities_list = self.engine.get_supported_entities(language)
                return jsonify(entities_list), 200
            except Exception as e:
                self.logger.error(
                    f"A fatal error occurred during execution of "
                    f"AnalyzerEngine.supported_entities(). {e}"
                )
                return jsonify(error=e.args[0]), 500

        # --- Anonymizer routes ---

        @app.route("/anonymize", methods=["POST"])
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
            anonymizer_result = self.anonymizer.anonymize(
                text=content.get("text", ""),
                analyzer_results=analyzer_results,
                operators=anonymizers_config,
            )
            return Response(anonymizer_result.to_json(), mimetype="application/json")

        @app.route("/deanonymize", methods=["POST"])
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
            deanonymized_response = self.deanonymize_engine.deanonymize(
                text=text, entities=deanonymize_entities, operators=deanonymize_config
            )
            return Response(
                deanonymized_response.to_json(), mimetype="application/json"
            )

        @app.route("/anonymizers", methods=["GET"])
        def anonymizers():
            """Return a list of supported anonymizers."""
            return jsonify(self.anonymizer.get_anonymizers())

        @app.route("/deanonymizers", methods=["GET"])
        def deanonymizers():
            """Return a list of supported deanonymizers."""
            return jsonify(self.deanonymize_engine.get_deanonymizers())

        # --- Error handlers ---

        @app.errorhandler(InvalidParamError)
        def invalid_param(err):
            self.logger.warning(
                f"Request failed with parameter validation error: {err.err_msg}"
            )
            return jsonify(error=err.err_msg), 422

        @app.errorhandler(HTTPException)
        def http_exception(e):
            return jsonify(error=e.description), e.code

        @app.errorhandler(Exception)
        def server_error(e):
            self.logger.error(f"A fatal error occurred during execution: {e}")
            return jsonify(error="Internal server error"), 500


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
    app = create_app()
    port = int(os.environ.get("PORT", DEFAULT_PORT))
    app.run(host="0.0.0.0", port=port)
