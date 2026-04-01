from ai_providers.openai_provider import call_openai
from ai_providers.oci_provider import call_oci_genai

def generate_ai_response(provider: str, prompt: str) -> str:
    if provider == "openai":
        return call_openai(prompt)

    elif provider == "oci":
        return call_oci_genai(prompt)

    else:
        raise ValueError(f"Unknown provider: {provider}")
