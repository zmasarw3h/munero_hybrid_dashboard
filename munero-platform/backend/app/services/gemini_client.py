"""
Minimal Gemini (Google Generative Language API) client.

Uses API key auth and httpx (already in requirements) to avoid pulling in heavy SDK deps.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional

import httpx


class GeminiClientError(RuntimeError):
    """Raised when Gemini API calls fail."""


@dataclass(frozen=True)
class GeminiClientConfig:
    api_key: str
    model: str
    base_url: str
    temperature: float
    max_output_tokens: int
    timeout_s: float
    retries: int


class GeminiClient:
    def __init__(self, config: GeminiClientConfig):
        self._config = config
        self._client = httpx.Client(timeout=self._config.timeout_s)

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:
            pass

    def _build_url(self, *, model: Optional[str] = None) -> str:
        base = self._config.base_url.rstrip("/")
        chosen_model = (model if model is not None else self._config.model).strip()
        if not chosen_model:
            raise GeminiClientError("Gemini model is not configured.")
        return f"{base}/models/{chosen_model}:generateContent"

    def _parse_text(self, payload: dict[str, Any]) -> str:
        candidates = payload.get("candidates") or []
        if not candidates:
            raise GeminiClientError("Gemini returned no candidates.")
        content = (candidates[0] or {}).get("content") or {}
        parts = content.get("parts") or []
        text_parts: list[str] = []
        for part in parts:
            if isinstance(part, dict) and isinstance(part.get("text"), str):
                text_parts.append(part["text"])
        text = "".join(text_parts).strip()
        if not text:
            raise GeminiClientError("Gemini returned empty text.")
        return text

    def generate_text(
        self,
        prompt: str,
        *,
        model: Optional[str] = None,
        max_output_tokens: Optional[int] = None,
    ) -> str:
        """
        Generate a text response from Gemini for a single user prompt.

        Notes:
        - Uses `x-goog-api-key` header to avoid leaking keys via URLs in logs/exceptions.
        - Retries on common transient failures (429/5xx) with exponential backoff.
        """
        api_key = (self._config.api_key or "").strip()
        if not api_key:
            raise GeminiClientError("LLM API key is not configured.")

        chosen_max_tokens = (
            int(max_output_tokens)
            if max_output_tokens is not None
            else int(self._config.max_output_tokens)
        )
        url = self._build_url(model=model)
        headers = {"x-goog-api-key": api_key}
        body = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": float(self._config.temperature),
                "maxOutputTokens": chosen_max_tokens,
            },
        }

        last_error: Optional[BaseException] = None
        backoff_s = 0.5
        attempts = max(0, int(self._config.retries)) + 1

        for attempt in range(attempts):
            try:
                response = self._client.post(url, headers=headers, json=body)

                status = response.status_code
                if status in (429, 500, 502, 503, 504) and attempt < attempts - 1:
                    time.sleep(backoff_s)
                    backoff_s = min(backoff_s * 2, 4.0)
                    continue

                if status < 200 or status >= 300:
                    raise GeminiClientError(f"Gemini request failed (status={status}).")

                data = response.json()
                if not isinstance(data, dict):
                    raise GeminiClientError("Gemini returned an unexpected response shape.")
                return self._parse_text(data)

            except (httpx.RequestError, ValueError, GeminiClientError) as exc:
                last_error = exc
                if attempt < attempts - 1:
                    time.sleep(backoff_s)
                    backoff_s = min(backoff_s * 2, 4.0)
                    continue
                if isinstance(exc, GeminiClientError):
                    raise
                raise GeminiClientError("Gemini request failed.") from exc

        raise GeminiClientError("Gemini request failed.") from last_error


def can_check_gemini_connection(
    *,
    api_key: str,
    model: str,
    base_url: str,
    timeout_s: float = 5.0,
) -> bool:
    """
    Best-effort connectivity check:
    - validates API key is present
    - hits the model resource (no token generation)
    """
    api_key = (api_key or "").strip()
    model = (model or "").strip()
    base_url = (base_url or "").strip().rstrip("/")
    if not api_key or not model or not base_url:
        return False

    url = f"{base_url}/models/{model}"
    headers = {"x-goog-api-key": api_key}
    try:
        with httpx.Client(timeout=timeout_s) as client:
            response = client.get(url, headers=headers)
        return 200 <= response.status_code < 300
    except Exception:
        return False
