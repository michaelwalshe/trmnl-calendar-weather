"""Render src/*.liquid locally with the sample payload from .trmnlp.yml.

This is a stand-in for `trmnlp serve` when Ruby/Docker are not available. It uses
python-liquid with a date filter that behaves like Ruby's (epoch %s, string
parsing, offsets preserved), which is what the hosted renderer runs.

    uv run --with python-liquid --with pyyaml --with python-dateutil \
        tools/render.py [full|half_horizontal|half_vertical|quadrant]

Writes _build/<view>.html - open it in a browser to check the layout.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dateutil import parser as dtparser
from liquid import Environment

ROOT = Path(__file__).resolve().parent.parent


def _to_dt(value):
    if value is None:
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(int(value), tz=timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text in ("now", "today"):
        return datetime.now(timezone.utc)
    if text.lstrip("-").isdigit():
        return datetime.fromtimestamp(int(text), tz=timezone.utc)
    try:
        parsed = dtparser.parse(text)
    except (ValueError, OverflowError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def ruby_date(value, fmt):
    """Ruby Liquid's date filter: parses strings/epochs, supports %s."""
    dt = _to_dt(value)
    if dt is None:
        return value
    fmt = str(fmt).replace("%s", str(int(dt.timestamp())))
    return dt.strftime(fmt)


SKELETON = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="utf-8">
    <link rel="stylesheet" href="https://trmnl.com/css/latest/plugins.css">
    <script src="https://trmnl.com/js/latest/plugins.js"></script>
    <style>
      body {{ margin: 0; background: #ddd; }}
      .screen {{ width: 800px; height: 480px; overflow: hidden; }}
    </style>
  </head>
  <body class="environment trmnl">
    <div class="screen screen--1bit">
      <div class="view view--{view}">
        {markup}
      </div>
    </div>
  </body>
</html>
"""


def main() -> int:
    view = sys.argv[1] if len(sys.argv) > 1 else "full"
    data_file = Path(sys.argv[2]) if len(sys.argv) > 2 else ROOT / ".trmnlp.yml"
    template_path = ROOT / "src" / f"{view}.liquid"
    if not template_path.exists():
        print(f"no such template: {template_path}")
        return 1

    config = yaml.safe_load(data_file.read_text(encoding="utf-8")) or {}
    data = dict(config.get("variables") or {})
    for key, value in (config.get("custom_fields") or {}).items():
        data.setdefault(key, value)

    env = Environment()
    env.filters["date"] = ruby_date
    markup = env.from_string(template_path.read_text(encoding="utf-8")).render(**data)

    out_dir = ROOT / "_build"
    out_dir.mkdir(exist_ok=True)
    stem = view if data_file.name == ".trmnlp.yml" else f"{view}-{data_file.stem}"
    out = out_dir / f"{stem}.html"
    out.write_text(SKELETON.format(view=view, markup=markup), encoding="utf-8")
    print(f"wrote {out} ({len(markup)} bytes of markup)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
