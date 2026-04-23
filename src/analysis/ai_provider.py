"""Provider abstraction for AI narrative generation."""

from __future__ import annotations

import os
from typing import Any

from ai_providers.ai_router import generate_ai_response as route_ai_response
from dotenv import load_dotenv

load_dotenv()


def generate_ai_response(
    provider: str,
    system_role: str,
    prompt: str,
    expected_sections: list[str],
) -> dict[str, Any]:
    """Generate an AI response through the configured provider router."""

    normalized_provider = provider.strip().lower()
    full_prompt = (
        f"{system_role}\n\n"
        f"{prompt}\n\n"
        "Required output sections:\n"
        + "\n".join(f"- {section}" for section in expected_sections)
    )
    response_text = route_ai_response(normalized_provider, full_prompt)

    return {
        "provider": normalized_provider,
        "model": _resolve_model_name(normalized_provider),
        "content": response_text,
    }


def _resolve_model_name(provider: str) -> str:
    """Return the configured model identifier for the selected provider."""

    if provider == "openai":
        return os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    if provider == "oci":
        return os.getenv("OCI_MODEL_ID", "")
    return ""
