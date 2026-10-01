"""OpenTelemetry tracing with OpenInference attribute names so Arize Phoenix
renders LLM spans (model, tokens, input/output). No-op when no endpoint is set."""

import json
from contextlib import contextmanager
from typing import Any

from opentelemetry import trace

from raw.settings import get_settings

_configured = False


def setup_tracing() -> None:
    global _configured
    if _configured:
        return
    _configured = True
    endpoint = get_settings().otel_exporter_otlp_endpoint
    if not endpoint:
        return
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    provider = TracerProvider(resource=Resource.create({"service.name": "risk-assessment-workbench"}))
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint.rstrip("/") + "/v1/traces")))
    trace.set_tracer_provider(provider)


tracer = trace.get_tracer("raw")


@contextmanager
def span(name: str, kind: str = "CHAIN", **attrs: Any):
    with tracer.start_as_current_span(name) as s:
        s.set_attribute("openinference.span.kind", kind)
        for k, v in attrs.items():
            if v is None:
                continue
            s.set_attribute(k, v if isinstance(v, (str, int, float, bool)) else json.dumps(v, default=str)[:4000])
        yield s
