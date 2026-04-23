import os

try:
    from openai import OpenAI
except ModuleNotFoundError:
    OpenAI = None


def call_openai(prompt: str) -> str:
    if OpenAI is None:
        raise ImportError("The 'openai' package is required for the OpenAI provider.")

    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    print(f"Using OpenAI model: {model}")

    resp = client.responses.create(model=model, input=prompt)

    return resp.output_text
