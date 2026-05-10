"""测试 DeepSeek API 连通性。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env")
except ImportError:
    pass

import requests


def main() -> None:
    api_key = os.environ.get("INDEX_SCORE_LLM_API_KEY", "")
    if not api_key:
        print("ERROR: INDEX_SCORE_LLM_API_KEY 未设置")
        sys.exit(1)

    masked = api_key[:10] + "..." + api_key[-4:] if len(api_key) > 14 else api_key
    print(f"API Key: {masked}")
    print(f"Key length: {len(api_key)}")

    base_url = "https://api.deepseek.com"
    model = "deepseek-v4-flash"

    print(f"\nSending request to {base_url}/chat/completions")
    print(f"Model: {model}")

    try:
        resp = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Reply with exactly: OK"}],
                "max_tokens": 10,
            },
            timeout=30,
        )
    except requests.exceptions.ConnectionError as exc:
        print(f"\nConnection failed: {exc}")
        sys.exit(1)
    except requests.exceptions.Timeout:
        print("\nRequest timed out (30s)")
        sys.exit(1)

    print(f"Status: {resp.status_code}")

    if resp.status_code == 200:
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
        returned_model = data.get("model", "unknown")
        print(f"Response: {reply}")
        print(f"Returned model: {returned_model}")
        print("\nConnectivity: OK")
    else:
        print(f"Error body: {resp.text[:500]}")
        sys.exit(1)


if __name__ == "__main__":
    main()
