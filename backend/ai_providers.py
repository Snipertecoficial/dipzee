"""LLM providers behind a swappable AIProvider interface.

Mirrors the DataProvider abstraction in ``providers.py``: the rest of the app
(``routes_ai.py``) only calls ``get_ai_provider().generate(...)`` and never
imports a specific SDK, so switching providers is a config change, not a
code change.

Supported providers:
- ``anthropic`` — Claude models (Opus/Sonnet/Haiku) via the official SDK.
- ``gemini``    — Google Gemini models via ``google-generativeai``.
- ``openai``    — GPT models via the official SDK.

Keys/models are resolved from two places, DB taking priority:
1. ``db.app_settings`` doc ``{"id": "ai_providers"}`` — set from the SuperAdmin
   panel (Admin > IA), so ops can rotate keys without touching the server.
2. Environment variables (``ANTHROPIC_API_KEY`` etc.) — the deploy-time default,
   kept as a fallback so a VPS with only a configured ``.env`` still works.
"""
import logging
import os
from abc import ABC, abstractmethod
from typing import Optional

from database import db

logger = logging.getLogger(__name__)

# Hard ceiling on any single LLM call. Without this the SDKs fall back to their
# own multi-minute defaults, and a hung provider ties up the worker thread that
# routes_ai runs the call in. 45s comfortably covers a 1024-token completion.
LLM_TIMEOUT_SECONDS = 45


class AIProviderError(RuntimeError):
    """Raised when a provider is misconfigured or a completion call fails."""


class AIProvider(ABC):
    name: str

    @abstractmethod
    async def generate(self, system: str, user_text: str) -> str:
        """Return the raw text completion for a single-turn system+user prompt."""
        raise NotImplementedError


class AnthropicProvider(AIProvider):
    name = "anthropic"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def generate(self, system: str, user_text: str) -> str:
        from anthropic import AsyncAnthropic

        client = AsyncAnthropic(api_key=self._api_key, timeout=LLM_TIMEOUT_SECONDS)
        resp = await client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=system,
            messages=[{"role": "user", "content": user_text}],
        )
        parts = [block.text for block in resp.content if getattr(block, "type", None) == "text"]
        return "".join(parts)


class GeminiProvider(AIProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def generate(self, system: str, user_text: str) -> str:
        import google.generativeai as genai

        genai.configure(api_key=self._api_key)
        model = genai.GenerativeModel(model_name=self._model, system_instruction=system)
        resp = await model.generate_content_async(user_text, request_options={"timeout": LLM_TIMEOUT_SECONDS})
        return resp.text


class OpenAIProvider(AIProvider):
    name = "openai"

    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def generate(self, system: str, user_text: str) -> str:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=self._api_key, timeout=LLM_TIMEOUT_SECONDS)
        resp = await client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_text},
            ],
        )
        return resp.choices[0].message.content or ""


async def get_ai_settings() -> dict:
    """The admin-configured AI settings doc (empty dict if never saved)."""
    doc = await db.app_settings.find_one({"id": "ai_providers"})
    return (doc or {}).get("value") or {}


def _resolve(settings: dict, db_field: str, env_var: str) -> Optional[str]:
    return settings.get(db_field) or os.environ.get(env_var)


async def get_ai_provider() -> AIProvider:
    """Instantiate the configured provider (DB setting first, then ``.env``)."""
    settings = await get_ai_settings()
    provider = (settings.get("active_provider") or os.environ.get("AI_PROVIDER", "anthropic")).strip().lower()

    if provider == "anthropic":
        api_key = _resolve(settings, "anthropic_api_key", "ANTHROPIC_API_KEY")
        if not api_key:
            raise AIProviderError("ANTHROPIC_API_KEY not set")
        model = settings.get("anthropic_model") or os.environ.get("ANTHROPIC_MODEL", "claude-opus-4-8")
        return AnthropicProvider(api_key, model)

    if provider == "gemini":
        api_key = _resolve(settings, "google_api_key", "GOOGLE_API_KEY")
        if not api_key:
            raise AIProviderError("GOOGLE_API_KEY not set")
        model = settings.get("gemini_model") or os.environ.get("GEMINI_MODEL")
        if not model:
            raise AIProviderError("GEMINI_MODEL not set")
        return GeminiProvider(api_key, model)

    if provider == "openai":
        api_key = _resolve(settings, "openai_api_key", "OPENAI_API_KEY")
        if not api_key:
            raise AIProviderError("OPENAI_API_KEY not set")
        model = settings.get("openai_model") or os.environ.get("OPENAI_MODEL", "gpt-4o")
        return OpenAIProvider(api_key, model)

    raise AIProviderError(f"Unknown AI_PROVIDER '{provider}' (expected 'anthropic', 'gemini' or 'openai')")
