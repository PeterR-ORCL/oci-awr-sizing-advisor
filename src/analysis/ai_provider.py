"""Provider abstraction for AI narrative generation."""

from __future__ import annotations

import os

from openai import OpenAI


def generate_ai_response(
    provider: str,
    system_role: str,
    prompt: str,
    expected_sections: list[str],
) -> dict:
    """Generate an AI response through the selected provider."""

    normalized_provider = provider.strip().lower()

    if normalized_provider == "openai":
        return _generate_openai_response(
            system_role=system_role,
            prompt=prompt,
            expected_sections=expected_sections,
        )

    if normalized_provider == "oci":
        return {
            "provider": "oci",
            "model": None,
            "content": "OCI Generative AI provider not implemented yet.",
        }

    raise ValueError(f"Unsupported AI provider: {provider}")


def _generate_openai_response(
    system_role: str,
    prompt: str,
    expected_sections: list[str],
) -> dict:
    """Generate an AI narrative using the OpenAI provider."""

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required when provider is 'openai'.")

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    print(f"Using model: {model}")

    client = OpenAI(api_key=api_key)
    response = client.responses.create(
        model=model,
        instructions=system_role,
        input=(
            f"{prompt}\n\n"
            "Required output sections:\n"
            + "\n".join(f"- {section}" for section in expected_sections)
        ),
    )

    return {
        "provider": "openai",
        "model": model,
        "content": response.output_text,
    }
