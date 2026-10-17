"""Smoke test: talk to whatever model LM Studio has loaded."""
import os
from openai import OpenAI

client = OpenAI()  # base URL + key are injected by AI Harness
model = os.environ.get("AIHARNESS_MODEL") or client.models.list().data[0].id
print(f"Using model: {model}")

stream = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Say hello in one short sentence."}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
print()
