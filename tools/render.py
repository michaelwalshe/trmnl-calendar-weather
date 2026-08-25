"""Render src/*.liquid locally with the sample payload from .trmnlp.yml.

This is a stand-in for `trmnlp serve` when Ruby/Docker are not available. It uses
python-liquid with a date filter that behaves like Ruby's (epoch %s, string
parsing, offsets preserved), which is what the hosted renderer runs.

    uv run --with python-liquid --with pyyaml --with python-dateutil \
        tools/render.py [full|half_horizontal|half_vertical|quadrant]

Writes _build/<view>.html and prints the headless-Chrome command that captures
it at the target device's exact size. The screen wrapper carries the same
classes the hosted renderer applies - device, bit depth, and the no-bleed class
that "Remove screen padding" sets - so the preview matches the panel rather than
a padded 780x460 approximation of it.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from pathlib import Path

import yaml
from dateutil import parser as dtparser
from liquid import Environment

ROOT = Path(__file__).resolve().parent.parent

# Framework device classes (see --screen-w/--screen-h in plugins.css). The
# default is the 800x600 Kindle geometry this plugin targets; screen--og is the
# 800x480 TRMNL original.
DEVICES = {
    "amazon_kindle_7": (800, 600),               # 6" 800x600 - Kindle 4/5/7 landscape
    "amazon_kindle_paperwhite_signature_11th_gen": (800, 600),
    "kobo_aura_hd": (800, 600),
    "nook_simple_touch": (800, 600),
    "inky_impression_13_3": (800, 600),
    "inkplate_13_spectra": (800, 600),
    "og": (800, 480),
    "ogv2": (800, 480),
}
DEFAULT_DEVICE = "amazon_kindle_7"
DEFAULT_BITS = 2


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
      .screen {{ width: var(--screen-w); height: var(--screen-h); overflow: hidden; }}
    </style>
  </head>
  <body class="environment trmnl">
    <div class="screen screen--no-bleed screen--{bits}bit screen--{device}">
      <div class="view view--{view}">
        {markup}
      </div>
    </div>
  </body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("view", nargs="?", default="full")
    ap.add_argument("data", nargs="?", default=None)
    ap.add_argument("--device", default=DEFAULT_DEVICE, choices=sorted(DEVICES))
    ap.add_argument("--bits", type=int, default=DEFAULT_BITS, choices=(1, 2, 4))
    args = ap.parse_args()

    view = args.view
    data_file = Path(args.data) if args.data else ROOT / ".trmnlp.yml"
    template_path = ROOT / "src" / f"{view}.liquid"
    if not template_path.exists():
        print(f"no such template: {template_path}")
        return 1

    config = yaml.safe_load(data_file.read_text(encoding="utf-8")) or {}
    data = dict(config.get("variables") or {})
    for key, value in (config.get("custom_fields") or {}).items():
        data.setdefault(key, value)
    # the template sizes its text against the panel height, so the preview has to
    # say which panel it is previewing; an explicit value in the payload wins
    data.setdefault("screen_height", str(DEVICES[args.device][1]))

    env = Environment()
    env.filters["date"] = ruby_date
    markup = env.from_string(template_path.read_text(encoding="utf-8")).render(**data)

    out_dir = ROOT / "_build"
    out_dir.mkdir(exist_ok=True)
    stem = view if data_file.name == ".trmnlp.yml" else f"{view}-{data_file.stem}"
    out = out_dir / f"{stem}.html"
    out.write_text(
        SKELETON.format(view=view, markup=markup, device=args.device, bits=args.bits),
        encoding="utf-8",
    )

    w, h = DEVICES[args.device]
    # a mashup cell only occupies part of the screen; clip the shot to it
    if view == "half_horizontal":
        h = h // 2
    elif view == "half_vertical":
        w = w // 2
    elif view == "quadrant":
        w, h = w // 2, h // 2
    print(f"wrote {out} ({len(markup)} bytes of markup)")
    sw, sh = DEVICES[args.device]
    print(f"  device {args.device} {sw}x{sh}, {args.bits}-bit; {view} cell {w}x{h}")
    print("  screenshot:")
    shot = out_dir / (stem + ".png")
    print(
        f"    chrome --headless=new --window-size={w},{h} --hide-scrollbars"
        f" --virtual-time-budget=8000 --screenshot={shot} {out.as_uri()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
