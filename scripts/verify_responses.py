#!/usr/bin/env python3
"""Live Responses checks. Uses TOKENLAB_API_KEY; no automatic retries."""

import json
import os
import sys
import urllib.error
import urllib.request


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def output_text(response):
    return "".join(
        part.get("text", "")
        for item in response.get("output", [])
        if item.get("type") == "message"
        for part in item.get("content", [])
        if part.get("type") == "output_text"
    )


def check_response(response):
    require(response.get("object") == "response", "Unexpected response object")
    require(response.get("model") == "gpt-6-astra", "Unexpected model")
    require(response.get("status") == "completed", "Response not completed")
    require(not response.get("error"), "Response contains error")
    require(output_text(response).strip() == "responses-ok", "Unexpected output text")
    usage = response.get("usage") or {}
    require(all(isinstance(usage.get(k), int) for k in
                ("input_tokens", "output_tokens", "total_tokens")), "Missing usage")


def events(response):
    """Decode complete SSE events, including multiline data fields."""
    data = []
    for raw in response:
        line = raw.decode("utf-8").rstrip("\r\n")
        if not line:
            if data:
                yield json.loads("\n".join(data))
                data = []
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))


def main():
    key = os.environ.get("TOKENLAB_API_KEY")
    require(bool(key), "Set TOKENLAB_API_KEY first")
    for stream in (False, True):
        payload = {"model": "gpt-6-astra", "input": "请只回复 responses-ok",
                   "stream": stream, "max_output_tokens": 64}
        request = urllib.request.Request(
            "https://na.tokenlab.sh/v1/responses",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Authorization": f"Bearer {key}",
                     "Content-Type": "application/json",
                     "Accept": "text/event-stream" if stream else "application/json"},
        )
        with urllib.request.urlopen(request, timeout=120) as response:
            require(response.status == 200, "Expected HTTP 200")
            if not stream:
                result = json.load(response)
                check_response(result)
            else:
                require("text/event-stream" in response.headers.get("Content-Type", ""),
                        "Expected SSE Content-Type")
                fragments = []
                completed = False
                for event in events(response):
                    kind = event.get("type")
                    require(kind not in {"error", "response.failed", "response.incomplete"}
                            and not event.get("error"), "Stream error: " + str(kind))
                    if kind == "response.output_text.delta":
                        fragments.append(event["delta"])
                    elif kind == "response.completed":
                        result = event["response"]
                        check_response(result)
                        require("".join(fragments) == output_text(result), "Delta mismatch")
                        completed = True
                        break
                require(completed, "Stream ended without response.completed")
            print(json.dumps({"result": "PASS", "stream": stream, "http_status": 200,
                              "id": result["id"], "text": output_text(result),
                              "usage": result["usage"]}, ensure_ascii=False))


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
