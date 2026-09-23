#!/usr/bin/env python3
"""Verify the documented TokenLab OpenAI-compatible behavior.

Usage:
  TOKENLAB_API_KEY=sk-... python scripts/verify_api.py
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request


BASE_URL = os.environ.get("TOKENLAB_BASE_URL", "https://na.tokenlab.sh").rstrip("/")
API_KEY = os.environ.get("TOKENLAB_API_KEY")


def request(path: str, payload: dict | None = None, accept: str = "application/json"):
    if not API_KEY:
        raise SystemExit("缺少 TOKENLAB_API_KEY 环境变量")
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode()
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Accept": accept,
    }
    if body is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(BASE_URL + path, data=body, headers=headers, method="GET" if body is None else "POST")
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=120) as response:
                if accept == "text/event-stream":
                    chunks = []
                    for line in response:
                        chunks.append(line)
                        if b"data: [DONE]" in line:
                            break
                    return response.status, response.headers, b"".join(chunks)
                return response.status, response.headers, response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")
            if exc.code in {500, 502, 503, 504} and attempt < 3:
                print(f"WARN {path}: HTTP {exc.code}，{attempt}/2 次后重试", file=sys.stderr)
                time.sleep(attempt * 3)
                continue
            raise RuntimeError(f"{path} 返回 HTTP {exc.code}: {detail[:500]}") from exc


def main() -> int:
    status, _, raw = request("/v1/models")
    assert status == 200
    models = json.loads(raw)
    model_ids = {item["id"] for item in models.get("data", [])}
    assert "gpt-6-astra" in model_ids, f"模型列表中没有 gpt-6-astra: {sorted(model_ids)}"
    print("PASS models: gpt-6-astra available")

    payload = {
        "model": "gpt-6-astra",
        "messages": [{"role": "user", "content": "请只回复 verify-ok"}],
        "stream": False,
        "max_tokens": 16,
    }
    status, _, raw = request("/v1/chat/completions", payload)
    assert status == 200
    completion = json.loads(raw)
    assert completion.get("object") == "chat.completion"
    assert completion.get("model") == "gpt-6-astra"
    assert completion.get("choices"), "非流式响应缺少 choices"
    assert "usage" in completion
    print("PASS chat.completions: non-stream response shape")

    stream_payload = {**payload, "stream": True}
    stream_error = ""
    for attempt in range(1, 4):
        status, _, raw = request("/v1/chat/completions", stream_payload, "text/event-stream")
        assert status == 200
        text = raw.decode("utf-8", "replace")
        events = [line[6:].strip() for line in text.splitlines() if line.startswith("data: ")]
        json_events = [json.loads(event) for event in events if event != "[DONE]"]
        stream_error = next(
            (event.get("error", {}).get("message", "") for event in json_events if "error" in event),
            "",
        )
        if "data:" in text and "[DONE]" in text and not stream_error:
            assert any(event.get("model") == "gpt-6-astra" for event in json_events)
            print("PASS chat.completions: SSE stream and [DONE]")
            return 0
        if attempt < 3:
            print(f"WARN 流式响应未完成（{stream_error or '缺少 [DONE]'}），重试", file=sys.stderr)
            time.sleep(attempt * 3)
    raise RuntimeError(f"流式验证失败: {stream_error or '响应没有 [DONE]'}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AssertionError, RuntimeError, json.JSONDecodeError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
