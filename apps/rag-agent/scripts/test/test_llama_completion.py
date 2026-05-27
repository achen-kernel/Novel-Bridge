"""Test llama-server with raw completion (non-chat) endpoint."""
import asyncio, json
import httpx


async def main():
    client = httpx.AsyncClient(timeout=120)

    # Test raw completion
    print("=== Raw completion ===")
    payload = {
        "prompt": "Hello, my name is",
        "temperature": 0.3,
        "max_tokens": 50,
        "stream": False,
    }
    r = await client.post("http://127.0.0.1:18080/v1/completions", json=payload)
    data = r.json()
    text = data.get("choices", [{}])[0].get("text", "")
    print(f"Text repr: {repr(text)}")
    print(f"Text length: {len(text)}")
    if text:
        print(f"Text: {text[:300]}")
    else:
        print("EMPTY - full response keys:", list(data.keys()))
        print(json.dumps(data, indent=2, ensure_ascii=False)[:1000])

    # Test with explicit stop
    print("\n=== Raw completion with stop ===")
    payload["stop"] = ["\n"]
    payload["prompt"] = "Once upon a time"
    r = await client.post("http://127.0.0.1:18080/v1/completions", json=payload)
    data = r.json()
    text = data.get("choices", [{}])[0].get("text", "")
    print(f"Text repr: {repr(text)}")
    print(f"Text length: {len(text)}")
    if text:
        print(f"Text: {text[:300]}")

    # Try with add_generation_prompt
    print("\n=== Chat with add_generation_prompt ===")
    payload2 = {
        "messages": [{"role": "user", "content": "hi"}],
        "temperature": 0.3,
        "max_tokens": 50,
        "stream": False,
        "add_generation_prompt": True,
    }
    r = await client.post("http://127.0.0.1:18080/v1/chat/completions", json=payload2)
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print(f"Content repr: {repr(content)}")
    print(f"Content length: {len(content)}")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
