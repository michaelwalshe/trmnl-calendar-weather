"""Upload this plugin to TRMNL, the way `trmnlp push` does.

`trmnlp` needs Ruby or Docker, neither of which is installed here, so this
script speaks the same private API directly with the standard library only:

    POST /api/plugin_settings              create a private plugin (plugin_id 37)
    POST /api/plugin_settings/{id}/archive upload a flat zip of src/*

The server replies with the canonical settings.yml, including the plugin id,
which is written back to src/settings.yml so later pushes update in place
instead of creating a second plugin.

    python tools/push.py --dry-run     check the key and list what would go up
    python tools/push.py               create or update the plugin
    python tools/push.py --id 12345    push to a specific existing plugin

The API key is read from $TRMNL_API_KEY, or from a .env file in the project
root. Get one at https://trmnl.com/account.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE_URL = os.environ.get("TRMNL_BASE_URL", "https://trmnl.com")
PRIVATE_PLUGIN_ID = 37  # TRMNL's id for the "private plugin" type
USER_AGENT = "trmnl-calendar-weather-push/1"


def api_key() -> str:
    key = os.environ.get("TRMNL_API_KEY", "").strip()
    if key:
        return key
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TRMNL_API_KEY="):
                return line.split("=", 1)[1].strip().strip("'\"")
    sys.exit("no API key: set TRMNL_API_KEY or add it to .env")


def request(method: str, path: str, key: str, body=None, content_type=None):
    req = urllib.request.Request(f"{BASE_URL}/api/{path}", method=method, data=body)
    req.add_header("Authorization", f"Bearer {key}")
    req.add_header("User-Agent", USER_AGENT)
    if content_type:
        req.add_header("Content-Type", content_type)
    try:
        with urllib.request.urlopen(req) as response:
            payload = response.read()
    except urllib.error.HTTPError as err:
        sys.exit(f"{method} {path} failed: {err.code} {err.read().decode(errors='replace')[:500]}")
    except urllib.error.URLError as err:
        sys.exit(f"{method} {path} failed: {err.reason}")
    return json.loads(payload) if payload else {}


def src_files() -> list[Path]:
    return sorted(p for p in (ROOT / "src").glob("*") if p.is_file())


def build_archive(files: list[Path]) -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.name)  # flat: basenames only
    return buffer.getvalue()


def multipart(field: str, filename: str, payload: bytes) -> tuple[bytes, str]:
    boundary = uuid.uuid4().hex
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="{field}"; filename="{filename}"\r\n'
        "Content-Type: application/zip\r\n\r\n"
    ).encode()
    body = head + payload + f"\r\n--{boundary}--\r\n".encode()
    return body, f"multipart/form-data; boundary={boundary}"


def settings_id() -> str | None:
    """The plugin id the server assigned on a previous push, if any."""
    for line in (ROOT / "src" / "settings.yml").read_text(encoding="utf-8").splitlines():
        if line.startswith("id:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="check the key, upload nothing")
    parser.add_argument("--id", help="push to this existing plugin setting id")
    parser.add_argument("--name", default="Week and Weather", help="name used when creating")
    args = parser.parse_args()

    key = api_key()
    files = src_files()
    archive = build_archive(files)

    me = request("GET", "me", key).get("data", {})
    who = me.get("email") or me.get("name") or "unknown account"
    print(f"authenticated as {who}")

    plugin_id = args.id or settings_id()
    print(f"archive: {len(archive)} bytes, {len(files)} files -> {', '.join(f.name for f in files)}")
    print(f"target : {'plugin ' + plugin_id if plugin_id else 'a NEW private plugin'}")

    if args.dry_run:
        print("dry run, nothing uploaded")
        return 0

    created = False
    if not plugin_id:
        response = request(
            "POST",
            "plugin_settings",
            key,
            body=json.dumps({"name": args.name, "plugin_id": PRIVATE_PLUGIN_ID}).encode(),
            content_type="application/json",
        )
        plugin_id = str(response.get("data", {}).get("id", ""))
        if not plugin_id:
            sys.exit(f"could not read new plugin id from: {response}")
        created = True
        print(f"created plugin {plugin_id}")

    body, content_type = multipart("file", "plugin.zip", archive)
    response = request("POST", f"plugin_settings/{plugin_id}/archive", key, body=body, content_type=content_type)

    returned = response.get("data", {}).get("settings_yaml")
    if returned:
        (ROOT / "src" / "settings.yml").write_text(returned, encoding="utf-8")
        print("src/settings.yml updated from the server (keeps the plugin id)")

    print(f"uploaded. edit at {BASE_URL}/plugin_settings/{plugin_id}/edit")
    if created:
        print(f"remember to add it to a playlist: {BASE_URL}/playlists")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
