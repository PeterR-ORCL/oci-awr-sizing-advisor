"""Provider abstraction for AI narrative generation."""

from __future__ import annotations

import os

import oci
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


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
        return _generate_oci_response(
            system_role=system_role,
            prompt=prompt,
            expected_sections=expected_sections,
        )

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


def _generate_oci_response(
    system_role: str,
    prompt: str,
    expected_sections: list[str],
) -> dict:
    """Generate an AI narrative using OCI Generative AI."""

    config_profile = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
    region = os.getenv("OCI_REGION") or config["region"]
    compartment_id = os.getenv("OCI_COMPARTMENT_ID")
    model_id = os.getenv("OCI_MODEL_ID")

    if not compartment_id:
        raise ValueError("OCI_COMPARTMENT_ID is required when provider is 'oci'.")
    if not model_id:
        raise ValueError("OCI_MODEL_ID is required when provider is 'oci'.")

    print(f"Using model: {model_id}")

    config = oci.config.from_file(os.path.expanduser("~/.oci/config"), config_profile)
    endpoint = f"https://inference.generativeai.{region}.oci.oraclecloud.com"

    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240),
    )

    full_prompt = (
        f"{system_role}\n\n"
        f"{prompt}\n\n"
        "Required output sections:\n"
        + "\n".join(f"- {section}" for section in expected_sections)
    )

    content = oci.generative_ai_inference.models.TextContent()
    content.text = full_prompt

    message = oci.generative_ai_inference.models.Message()
    message.role = "USER"
    message.content = [content]

    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = (
        oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    )
    chat_request.messages = [message]
    chat_request.max_tokens = 1200
    chat_request.temperature = 0.2
    chat_request.top_p = 1
    chat_request.top_k = 0

    chat_detail = oci.generative_ai_inference.models.ChatDetails()
    chat_detail.serving_mode = oci.generative_ai_inference.models.OnDemandServingMode(
        model_id=model_id
    )
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = compartment_id

    response = client.chat(chat_detail)
    if response is None or response.data is None:
        raise RuntimeError("OCI Generative AI response did not include data.")
    response_data = response.data

    chat_response = response_data.chat_response
    if chat_response is None or not chat_response.choices:
        raise RuntimeError("OCI Generative AI response did not include choices.")

    choice = chat_response.choices[0]
    message = choice.message
    if message is None or not message.content:
        raise RuntimeError("OCI Generative AI response did not include content.")

    first_content = message.content[0]
    response_text = getattr(first_content, "text", None)
    if response_text is None:
        raise RuntimeError("OCI Generative AI response content did not include text.")

    return {
        "provider": "oci",
        "model": model_id,
        "content": response_text,
    }
