#!/usr/bin/env python3
"""Execute the Python/Node.js SDK page code blocks, not duplicated examples.

Install openai for Python and run npm ci before use. Requires TOKENLAB_API_KEY.
Makes four live Chat Completions requests (ordinary + streaming, each SDK).
"""

import argparse
import os
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent
MARKER = "===TOKENLAB_STREAM_EXAMPLE==="


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdk", choices=("all", "python", "node"), default="all")
    args = parser.parse_args()
    if not os.environ.get("TOKENLAB_API_KEY"):
        raise RuntimeError("Set TOKENLAB_API_KEY first")
    examples = [
        ("Python", "sdks/python-openai.mdx", "python", [sys.executable, "-"],
         f'print("{MARKER}", flush=True)'),
        ("Node.js", "sdks/nodejs-openai.mdx", "javascript",
         ["node", "--input-type=module", "-"], f'console.log("{MARKER}");'),
    ]
    for name, page, language, command, separator in examples:
        if args.sdk == "python" and name != "Python":
            continue
        if args.sdk == "node" and name != "Node.js":
            continue
        source = (ROOT / page).read_text(encoding="utf-8")
        blocks = re.findall(r"```" + language + r"\n(.*?)\n```", source, re.S)
        if len(blocks) != 2:
            raise RuntimeError(f"Expected two code blocks in {page}")
        program = ("\n" + separator + "\n").join(blocks)
        result = subprocess.run(command, input=program, text=True, encoding="utf-8",
                                capture_output=True, cwd=ROOT, timeout=300,
                                env={**os.environ, "PYTHONIOENCODING": "utf-8"})
        if result.returncode:
            raise RuntimeError(f"{name} example failed: {result.stderr[-2000:]}")
        parts = result.stdout.split(MARKER)
        if len(parts) != 2 or not all(part.strip() for part in parts):
            raise RuntimeError(f"{name}: empty ordinary or streaming output")
        print(f"PASS {name}: exact documented ordinary + streaming examples; "
              f"output lengths {[len(part.strip()) for part in parts]}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except (RuntimeError, subprocess.TimeoutExpired) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
