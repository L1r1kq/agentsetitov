from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

import httpx

from agentse.config import Settings, get_settings
from agentse.observability.metrics import LLM_LATENCY, LLM_REQUESTS, LLM_TOKENS


@dataclass
class LLMResult:
    text: str
    model: str
    latency_s: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    raw: dict[str, Any] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class OllamaClient:
    """Тонкий клиент native Ollama API. Без привязки к облачным ключам."""

    def __init__(self, settings: Settings | None = None, model: str | None = None) -> None:
        self.settings = settings or get_settings()
        self.model = model or self.settings.model
        self._client = httpx.Client(timeout=self.settings.timeout_s)

    def chat(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
        format_json: bool = False,
    ) -> LLMResult:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": self.settings.temperature if temperature is None else temperature,
                "num_predict": self.settings.max_tokens if max_tokens is None else max_tokens,
            },
        }
        if format_json:
            payload["format"] = "json"

        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        started = time.perf_counter()
        status = "ok"
        try:
            response = self._client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        except Exception:
            status = "error"
            LLM_REQUESTS.labels(model=self.model, status=status).inc()
            raise
        latency = time.perf_counter() - started
        text = (data.get("message") or {}).get("content") or ""
        prompt_tokens = int(data.get("prompt_eval_count") or 0)
        completion_tokens = int(data.get("eval_count") or 0)
        LLM_REQUESTS.labels(model=self.model, status=status).inc()
        LLM_LATENCY.labels(model=self.model).observe(latency)
        LLM_TOKENS.labels(model=self.model, kind="prompt").inc(prompt_tokens)
        LLM_TOKENS.labels(model=self.model, kind="completion").inc(completion_tokens)
        return LLMResult(
            text=text.strip(),
            model=self.model,
            latency_s=latency,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            raw=data,
        )

    def generate(self, prompt: str, **kwargs: Any) -> LLMResult:
        return self.chat([{"role": "user", "content": prompt}], **kwargs)

    def close(self) -> None:
        self._client.close()


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


def parse_json_object(text: str) -> dict[str, Any]:
    text = text.strip()
    try:
        value = json.loads(text)
        if isinstance(value, dict):
            return value
    except json.JSONDecodeError:
        pass
    match = _JSON_RE.search(text)
    if not match:
        raise ValueError(f"JSON object not found: {text[:240]}")
    value = json.loads(match.group(0))
    if not isinstance(value, dict):
        raise ValueError("parsed JSON is not an object")
    return value
