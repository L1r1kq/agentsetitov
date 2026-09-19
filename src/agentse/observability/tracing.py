from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterator

from agentse.config import get_settings

try:
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
except Exception:  # pragma: no cover
    trace = None  # type: ignore
    OTLPSpanExporter = None  # type: ignore
    Resource = None  # type: ignore
    TracerProvider = None  # type: ignore
    BatchSpanProcessor = None  # type: ignore


_TRACER_READY = False


def setup_tracing(service_name: str = "agentse") -> None:
    global _TRACER_READY
    settings = get_settings()
    if trace is None or OTLPSpanExporter is None:
        _TRACER_READY = False
        return
    # Без коллектора не шумим ретраями: file traces всё равно пишутся.
    import os

    if os.getenv("AGENTSE_OTEL_ENABLED", "false").lower() not in {"1", "true", "yes"}:
        _TRACER_READY = False
        return
    resource = Resource.create({"service.name": service_name, "service.version": "0.1.0"})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=f"{settings.otel_endpoint.rstrip('/')}/v1/traces")
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    _TRACER_READY = True


def _file_trace(event: dict[str, Any]) -> None:
    settings = get_settings()
    settings.traces_dir.mkdir(parents=True, exist_ok=True)
    day = datetime.now(UTC).date().isoformat()
    path = settings.traces_dir / f"{day}.jsonl"
    with path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, ensure_ascii=False) + "\n")


@contextmanager
def start_span(name: str, **attrs: Any) -> Iterator[dict[str, Any]]:
    span_id = uuid.uuid4().hex[:12]
    started = time.perf_counter()
    payload = {"name": name, "span_id": span_id, "attrs": attrs, "events": []}
    otel_span = None
    if _TRACER_READY and trace is not None:
        otel_span = trace.get_tracer("agentse").start_span(name)
        for key, value in attrs.items():
            otel_span.set_attribute(key, str(value)[:256])
    try:
        yield payload
    except Exception as exc:
        payload["error"] = repr(exc)
        if otel_span is not None:
            otel_span.record_exception(exc)
        raise
    finally:
        payload["duration_s"] = round(time.perf_counter() - started, 4)
        _file_trace(
            {
                "ts": datetime.now(UTC).isoformat(),
                "type": "span",
                "name": name,
                "span_id": span_id,
                "duration_s": payload["duration_s"],
                "attrs": attrs,
                "error": payload.get("error"),
            }
        )
        if otel_span is not None:
            otel_span.end()


def trace_event(name: str, **fields: Any) -> None:
    event = {
        "ts": datetime.now(UTC).isoformat(),
        "type": "event",
        "name": name,
        **fields,
    }
    _file_trace(event)
    if _TRACER_READY and trace is not None:
        span = trace.get_current_span()
        if span is not None:
            span.add_event(name, {k: str(v)[:256] for k, v in fields.items()})
