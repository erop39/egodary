"""Mark PR ready and merge to main."""

from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request

REPO = "erop39/promptgen"
PR_NUMBER = 1


def _token() -> str:
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True,
        check=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("password="):
            return line.split("=", 1)[1]
    raise RuntimeError("No GitHub token")


def _api(method: str, path: str, payload: dict | None = None) -> dict:
    headers = {
        "Authorization": f"Bearer {_token()}",
        "Accept": "application/vnd.github+json",
        "Content-Type": "application/json",
        "User-Agent": "egodary",
    }
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}",
        data=data,
        headers=headers,
        method=method,
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        body = resp.read()
        return json.loads(body) if body else {}


def main() -> int:
    ready = _api("PATCH", f"pulls/{PR_NUMBER}", {"draft": False})
    print(f"PR #{PR_NUMBER} draft={ready.get('draft')} url={ready.get('html_url')}")
    try:
        merged = _api(
            "PUT",
            f"pulls/{PR_NUMBER}/merge",
            {"commit_title": "Release v0.1.21", "merge_method": "merge"},
        )
        print(f"Merged: {merged.get('message')}")
    except urllib.error.HTTPError as exc:
        print(exc.read().decode(), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
