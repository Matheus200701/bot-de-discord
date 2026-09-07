from __future__ import annotations

import os
from typing import Any


def configure_observability() -> None:
    """Configure optional tracing, metrics and error reporting without leaking secrets."""
    service_name = os.getenv("OTEL_SERVICE_NAME", "discord-commerce-platform")
    environment = os.getenv("APP_ENV", "development")

    try:
        import sentry_sdk

        dsn = os.getenv("SENTRY_DSN")
        if dsn:
            def before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
                request = event.get("request")
                if isinstance(request, dict):
                    request.pop("cookies", None)
                    request.pop("headers", None)
                    request.pop("data", None)
                return event

            sentry_sdk.init(
                dsn=dsn,
                environment=environment,
                release=os.getenv("APP_VERSION") or None,
                traces_sample_rate=float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "0.05")),
                profiles_sample_rate=float(os.getenv("SENTRY_PROFILES_SAMPLE_RATE", "0")),
                send_default_pii=False,
                before_send=before_send,
            )
    except ImportError:
        pass

    try:
        from opentelemetry import metrics, trace
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({
            "service.name": service_name,
            "service.version": os.getenv("APP_VERSION", "unknown"),
            "deployment.environment.name": environment,
        })
        traces = TracerProvider(resource=resource)
        metrics_endpoint = os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT")
        traces_endpoint = os.getenv("OTEL_EXPORTER_OTLP_TRACES_ENDPOINT")

        if traces_endpoint:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            traces.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=traces_endpoint)))
        trace.set_tracer_provider(traces)

        readers = []
        if metrics_endpoint:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

            readers.append(PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=metrics_endpoint)))
        metrics.set_meter_provider(MeterProvider(resource=resource, metric_readers=readers))

        _instrument_frameworks()
    except ImportError:
        pass


def _instrument_frameworks() -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        # FastAPIInstrumentor is activated lazily by sitecustomize before app import.
        FastAPIInstrumentor().instrument()
    except (ImportError, RuntimeError):
        pass

    try:
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        SQLAlchemyInstrumentor().instrument()
    except (ImportError, RuntimeError):
        pass

    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
        HTTPXClientInstrumentor().instrument()
    except (ImportError, RuntimeError):
        pass


configure_observability()
