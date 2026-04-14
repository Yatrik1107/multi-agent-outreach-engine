from __future__ import annotations

import json
import re
from typing import Any, TypeVar

from google import genai
from google.genai import types
from pydantic import BaseModel, ValidationError

from smartlead.core.settings import Settings

T = TypeVar("T", bound=BaseModel)


def _strip_json_fences(text: str) -> str:
    text = text.strip()
    m = re.match(r"^```(?:json)?\s*\n?(.*)\n?```$", text, re.DOTALL | re.IGNORECASE)
    if m:
        return m.group(1).strip()
    return text


class GeminiLLM:
    def __init__(self, settings: Settings) -> None:
        key = (settings.gemini_api_key or "").strip()
        if not key:
            raise ValueError("GEMINI_API_KEY (or GOOGLE_API_KEY) is required when live LLM is enabled.")
        self._client = genai.Client(api_key=key)
        self._model = (settings.gemini_model or "").strip() or "gemini-2.0-flash"

    def generate_text(self, system: str, user: str, temperature: float = 0.7) -> str:
        config = types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=user,
            config=config,
        )
        text = getattr(response, "text", None) or ""
        return text.strip()

    def generate_json(self, system: str, user: str, model_cls: type[T], temperature: float = 0.2) -> T:
        schema = model_cls.model_json_schema()
        schema_hint = json.dumps(schema, indent=2)
        augmented_system = (
            f"{system}\n\n"
            "Respond with ONLY valid JSON (no markdown fences) that conforms to this JSON Schema:\n"
            f"{schema_hint}"
        )
        config = types.GenerateContentConfig(
            system_instruction=augmented_system,
            temperature=temperature,
            response_mime_type="application/json",
        )
        response = self._client.models.generate_content(
            model=self._model,
            contents=user,
            config=config,
        )
        raw = getattr(response, "text", None) or ""
        raw = _strip_json_fences(raw)
        try:
            return model_cls.model_validate_json(raw)
        except ValidationError:
            data: Any = json.loads(raw)
            return model_cls.model_validate(data)