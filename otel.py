import logging
import os

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc._log_exporter import (
    OTLPLogExporter as GRPCLogExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import (
    OTLPMetricExporter as GRPCMetricExporter,
)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
    OTLPSpanExporter as GRPCSpanExporter,
)
from opentelemetry.exporter.otlp.proto.http._log_exporter import (
    OTLPLogExporter as HTTPLogExporter,
)
from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
    OTLPMetricExporter as HTTPMetricExporter,
)
from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
    OTLPSpanExporter as HTTPSpanExporter,
)
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk._logs import LoggerProvider
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SpanExporter, SpanExportResult
from opentelemetry._logs import set_logger_provider
from opentelemetry.sdk._logs import LoggingHandler


class FilteringSpanExporter(SpanExporter):
    """Wraps a SpanExporter and drops spans matching excluded URL paths."""

    def __init__(self, delegate: SpanExporter, excluded_paths: list[str]):
        self._delegate = delegate
        self._excluded_paths = excluded_paths

    def export(self, spans):
        filtered = [s for s in spans if not self._is_excluded(s)]
        if not filtered:
            return SpanExportResult.SUCCESS
        return self._delegate.export(filtered)

    def _is_excluded(self, span) -> bool:
        for path in self._excluded_paths:
            if path in span.name:
                return True
        return False

    def shutdown(self):
        self._delegate.shutdown()

    def force_flush(self, timeout_millis=None):
        return self._delegate.force_flush(timeout_millis)


def setup_otel() -> None:
    """Set up OpenTelemetry tracing, logging, and metrics."""
    logger = logging.getLogger(__name__)

    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        logger.info("OTEL exporter endpoint not set, skipping OpenTelemetry setup")
        return

    logger.info("Setting up OpenTelemetry")

    protocol = os.environ.get("OTEL_EXPORTER_OTLP_PROTOCOL", "http/protobuf")
    use_grpc = protocol.startswith("grpc")

    # Traces
    tracer_provider = TracerProvider()
    span_exporter = GRPCSpanExporter() if use_grpc else HTTPSpanExporter()
    span_exporter = FilteringSpanExporter(span_exporter, ["/health"])
    tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
    trace.set_tracer_provider(tracer_provider)

    # Logs
    LoggingInstrumentor().instrument()
    logger_provider = LoggerProvider()
    log_exporter = GRPCLogExporter() if use_grpc else HTTPLogExporter()
    logger_provider.add_log_record_processor(BatchLogRecordProcessor(log_exporter))
    set_logger_provider(logger_provider)
    handler = LoggingHandler(logger_provider=logger_provider)
    logging.getLogger().addHandler(handler)

    # Metrics
    metric_exporter = GRPCMetricExporter() if use_grpc else HTTPMetricExporter()
    reader = PeriodicExportingMetricReader(metric_exporter)
    meter_provider = MeterProvider(metric_readers=[reader])
    metrics.set_meter_provider(meter_provider)

    # Reduce urllib3 noise
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def instrument_flask_app(app) -> None:
    """Instrument a Flask app with OpenTelemetry tracing and metrics."""
    if not os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT"):
        return
    FlaskInstrumentor().instrument_app(app)

    from flask import request as flask_request

    @app.before_request
    def _otel_capture_request_body():
        span = trace.get_current_span()
        if span and span.is_recording() and flask_request.is_json:
            span.set_attribute("http.request.body", flask_request.get_data(as_text=True))

    @app.after_request
    def _otel_capture_response_body(response):
        span = trace.get_current_span()
        if span and span.is_recording() and response.content_type and "application/json" in response.content_type:
            span.set_attribute("http.response.body", response.get_data(as_text=True))
        return response
