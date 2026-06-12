#!/usr/bin/env python3
# ==============================================================================
# Script Name: chat_client.py
# Description: Interactive python client for Ollama running local LLMs
#              optimized for CPU on Arm64.
# ==============================================================================

import sys
import json
import requests

OLLAMA_HOST = "http://localhost:11434"

def get_installed_models():
    """Fetches the list of installed models from Ollama."""
    try:
        response = requests.get(f"{OLLAMA_HOST}/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return [m["name"] for m in models]
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to Ollama server. Is it running?")
        print("Please start it with 'sudo systemctl start ollama' or run 'ollama serve'.")
        sys.exit(1)
    except Exception as e:
        print(f"Error checking models: {e}")
    return []

def stream_chat(model_name, prompt):
    """Sends a prompt to the Ollama chat API and streams the output."""
    url = f"{OLLAMA_HOST}/api/chat"
    payload = {
        "model": model_name,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "stream": True
    }
    
    print(f"\nPrompt: {prompt}")
    print(f"Model: {model_name}")
    print("Response: ", end="", flush=True)

    try:
        response = requests.post(url, json=payload, stream=True, timeout=180)
        if response.status_code != 200:
            print(f"\nError: API returned status code {response.status_code}")
            return

        for line in response.iter_lines():
            if line:
                chunk = json.loads(line.decode("utf-8"))
                content = chunk.get("message", {}).get("content", "")
                print(content, end="", flush=True)
        print("\n")

    except requests.exceptions.Timeout:
        print("\nError: Request timed out. The model might be loading or the prompt is too large.")
    except Exception as e:
        print(f"\nError streaming response: {e}")

def main():
    models = get_installed_models()
    if not models:
        print("Error: No models found. Please pull a model first (e.g. 'ollama pull phi3:mini').")
        sys.exit(1)

    print("Available Local Models:")
    for idx, model in enumerate(models):
        print(f" [{idx}] {model}")

    # Default to the first available model
    selected_model = models[0]
    print(f"\nDefaulting to model: {selected_model}")
    print("Type your prompt and press Enter. Type 'exit' or 'quit' to end the session.")
    print("-" * 60)

    while True:
        try:
            prompt = input("\nYou: ").strip()
            if not prompt:
                continue
            if prompt.lower() in ["exit", "quit"]:
                print("Exiting chat client. Goodbye!")
                break
            stream_chat(selected_model, prompt)
        except KeyboardInterrupt:
            print("\nExiting chat client. Goodbye!")
            break

if __name__ == "__main__":
    main()
