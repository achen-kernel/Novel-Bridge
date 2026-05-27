"""Direct llama-server test to diagnose empty content."""
import asyncio, json
import httpx


async def main():
    client = httpx.AsyncClient(timeout=120)

    # Test 1: Simple greeting
    print("=== Test 1: Simple greeting ===")
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "temperature": 0.3,
        "max_tokens": 50,
        "stream": False,
    }
    r = await client.post("http://127.0.0.1:18080/v1/chat/completions", json=payload)
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print(f"Content repr: {repr(content)}")
    print(f"Content length: {len(content)}")
    print(f"Timings: {json.dumps(data.get('timings', {}), indent=2)}")
    print(f"Usage: {json.dumps(data.get('usage', {}), indent=2)}")

    # Test 2: Chinese prompt
    print("\n=== Test 2: Chinese ===")
    payload["messages"] = [{"role": "user", "content": "你好，请简单介绍一下你自己"}]
    r = await client.post("http://127.0.0.1:18080/v1/chat/completions", json=payload)
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print(f"Content repr: {repr(content)}")
    print(f"Content length: {len(content)}")
    print(f"Content preview: {content[:200]}")

    # Test 3: Full QA prompt (system + user)
    print("\n=== Test 3: System + User ===")
    payload["messages"] = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "孙悟空是谁？请用中文回答。"},
    ]
    payload["max_tokens"] = 200
    r = await client.post("http://127.0.0.1:18080/v1/chat/completions", json=payload)
    data = r.json()
    content = data["choices"][0]["message"]["content"]
    print(f"Content repr: {repr(content)}")
    print(f"Content length: {len(content)}")
    if content:
        print(f"Content: {content[:300]}")
    else:
        print("EMPTY RESPONSE")
        print(f"Timings: {json.dumps(data.get('timings', {}), indent=2)}")

    await client.aclose()


if __name__ == "__main__":
    asyncio.run(main())
