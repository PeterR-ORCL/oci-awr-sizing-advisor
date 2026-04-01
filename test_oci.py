import os
import oci
from dotenv import load_dotenv

# Load .env
load_dotenv()


def call_oci_genai(prompt: str) -> str:
    # Load OCI config
    config_profile = os.getenv("OCI_CONFIG_PROFILE", "DEFAULT")
    config = oci.config.from_file("~/.oci/config", config_profile)

    # Load environment variables
    region = os.getenv("OCI_REGION", "us-phoenix-1")
    compartment_id = os.getenv("OCI_COMPARTMENT_ID")
    model_id = os.getenv("OCI_MODEL_ID")

    if not compartment_id:
        raise ValueError("OCI_COMPARTMENT_ID is not set")
    if not model_id:
        raise ValueError("OCI_MODEL_ID is not set")

    # Endpoint
    endpoint = f"https://inference.generativeai.{region}.oci.oraclecloud.com"

    # Client
    client = oci.generative_ai_inference.GenerativeAiInferenceClient(
        config=config,
        service_endpoint=endpoint,
        retry_strategy=oci.retry.NoneRetryStrategy(),
        timeout=(10, 240),
    )

    # Build message
    content = oci.generative_ai_inference.models.TextContent()
    content.text = prompt

    message = oci.generative_ai_inference.models.Message()
    message.role = "USER"
    message.content = [content]

    # Chat request
    chat_request = oci.generative_ai_inference.models.GenericChatRequest()
    chat_request.api_format = (
        oci.generative_ai_inference.models.BaseChatRequest.API_FORMAT_GENERIC
    )
    chat_request.messages = [message]
    chat_request.max_tokens = 1200
    chat_request.temperature = 0.2
    chat_request.top_p = 1
    chat_request.top_k = 0

    # Chat details
    chat_detail = oci.generative_ai_inference.models.ChatDetails()
    chat_detail.serving_mode = (
        oci.generative_ai_inference.models.OnDemandServingMode(
            model_id=model_id
        )
    )
    chat_detail.chat_request = chat_request
    chat_detail.compartment_id = compartment_id

    # Call OCI
    response = client.chat(chat_detail)

    # Extract response text
    return response.data.chat_response.choices[0].message.content[0].text


# ---- RUN TEST ----
if __name__ == "__main__":
    result = call_oci_genai("Say OCI is working")
    print("\n=== OCI RESPONSE ===\n")
    print(result)
