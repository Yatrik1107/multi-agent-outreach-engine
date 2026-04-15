"""xAI Grok — dedicated provider module.

Uses the official OpenAI-compatible Chat Completions API at api.x.ai.
The `openai` Python package is only the HTTP client; this is not `OpenAILLM`.
"""

from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from openai import OpenAI
from pydantic import BaseModel, ValidationError

from smartlead.core.settings import Settings

T = TypeVar("T", bound=BaseModel)

XAI_BASE_URL = "https://api.x.ai/v1"


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*\n?(.*)\n?```$", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


class GrokLLM:
    """Same public methods as GeminiLLM / OpenAILLM: generate_text, generate_json."""

    def __init__(self, settings: Settings) -> None:
        key = (settings.grok_api_key or "").strip()
        if not key:
            raise ValueError(
                "GROK_API_KEY (or XAI_API_KEY) is required when LLM_PROVIDER=grok.",
            )
        self._client = OpenAI(api_key=key, base_url=XAI_BASE_URL)
        self._model = (settings.grok_model or "").strip() or "grok-2-latest"

    def generate_text(self, system: str, user: str, temperature: float = 0.7) -> str:
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
        )
        msg = response.choices[0].message
        return (msg.content or "").strip()

    def generate_json(self, system: str, user: str, model_cls: type[T], temperature: float = 0.2) -> T:
        schema = model_cls.model_json_schema()
        schema_hint = json.dumps(schema, indent=2)
        augmented_system = (
            f"{system}\n\n"
            "Respond with ONLY one JSON object (no markdown fences) that conforms to this JSON Schema. "
            "The response must be valid json.\n"
            f"{schema_hint}"
        )
        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": augmented_system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            response_format={"type": "json_object"},
        )
        raw = (response.choices[0].message.content or "").strip()
        raw = _strip_json_fences(raw)
        try:
            return model_cls.model_validate_json(raw)
        except ValidationError:
            data: Any = json.loads(raw)
            return model_cls.model_validate(data)