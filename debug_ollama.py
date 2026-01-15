
import os
from openai import OpenAI
import sys

# Mimic LLMFactory logic
base_url = "http://localhost:11434/v1"
api_key = "ollama"
model = "llama3"
# model = "llama3:8b" # Uncomment if the above fails

client = OpenAI(
    base_url=base_url,
    api_key=api_key,
)

print(f"Testing connection to {base_url} with model {model}...")

try:
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "user", "content": "Say hello!"}
        ],
    )
    print("Success!")
    print("Response:", response.choices[0].message.content)
except Exception as e:
    print("Failed!")
    print(e)
    # Check what models are available
    try:
        print("\nListing available models:")
        models = client.models.list()
        for m in models.data:
            print(f"- {m.id}")
    except Exception as list_e:
        print(f"Could not list models: {list_e}")
