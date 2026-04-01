from openai import OpenAI
import os

def call_openai(prompt: str) -> str:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
    print(f"Using OpenAI model: {model}")

    resp = client.responses.create(
        model=model,
        input=prompt
    )

    return resp.output_text
