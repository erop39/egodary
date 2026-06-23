"""Create GitHub release and upload transfer archive (uses git credentials)."""

from __future__ import annotations

import json
import mimetypes
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "erop39/promptgen"
TAG = "v0.1.21"
ROOT = Path(__file__).resolve().parents[1]
NOTES = ROOT / "release" / "notes-v0.1.21.md"
ARCHIVE = ROOT / "release" / "egodary-transfer-20260618-1754.zip"


def _git_credential_token() -> str:
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        text=True,
        capture_output=True,
        check=True,
    )
    username = password = None
    for line in proc.stdout.splitlines():
        if line.startswith("username="):
            username = line.split("=", 1)[1]
        elif line.startswith("password="):
            password = line.split("=", 1)[1]
    if not password:
        raise RuntimeError("No GitHub token from git credential helper")
    return password


def _request(method: str, url: str, token: str, data: bytes | None = None, headers: dict | None = None):
    req_headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "egodary-release-script",
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    with urllib.request.urlopen(req, timeout=120) as resp:
        body = resp.read()
        return resp.status, json.loads(body) if body else {}


def main() -> int:
    if not NOTES.is_file():
        print(f"Missing release notes: {NOTES}", file=sys.stderr)
        return 1
    if not ARCHIVE.is_file():
        print(f"Missing archive: {ARCHIVE}", file=sys.stderr)
        return 1

    token = _git_credential_token()
    body_text = NOTES.read_text(encoding="utf-8")

    # Skip if release already exists
    list_url = f"https://api.github.com/repos/{REPO}/releases/tags/{TAG}"
    try:
        status, existing = _request("GET", list_url, token)
        if status == 200 and existing.get("id"):
            print(f"Release {TAG} already exists: {existing.get('html_url')}")
            release = existing
        else:
            release = None
    except urllib.error.HTTPError as exc:
        if exc.code != 404:
            raise
        release = None

    if release is None:
        payload = json.dumps(
            {
                "tag_name": TAG,
                "name": TAG,
                "body": body_text,
                "draft": False,
                "prerelease": False,
            }
        ).encode("utf-8")
        status, release = _request(
            "POST",
            f"https://api.github.com/repos/{REPO}/releases",
            token,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        print(f"Created release {TAG}: {release.get('html_url')}")

    upload_url = release.get("upload_url", "").split("{")[0]
    asset_name = ARCHIVE.name
    content_type = mimetypes.guess_type(asset_name)[0] or "application/zip"
    asset_data = ARCHIVE.read_bytes()

    # Remove duplicate asset if re-running
    for asset in release.get("assets", []):
        if asset.get("name") == asset_name:
            _request("DELETE", asset["url"], token)
            print(f"Removed existing asset {asset_name}")

    status, asset = _request(
        "POST",
        f"{upload_url}?name={asset_name}",
        token,
        data=asset_data,
        headers={"Content-Type": content_type},
    )
    print(f"Uploaded asset: {asset.get('browser_download_url')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
