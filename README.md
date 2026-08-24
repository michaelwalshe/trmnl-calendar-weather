# Week + Weather — TRMNL plugin merge

A single TRMNL private plugin that draws a rolling-week time grid in the style of
Google Calendar's week view, with a thin weather strip across the top. Both halves
come from plugins you already have connected: the native calendar plugin supplies
the events, the native weather plugin supplies conditions and the two-day forecast.
The plugin itself fetches nothing — it uses the **Plugin Merge** strategy, which
hands your other plugins' parsed JSON to your own markup.

Preview renders (from the sample payload, not live data):

| Layout | File |
|---|---|
| Full, 800×480 | `_build/full.png` |
| Full, stress payload | `_build/full-dense.png` |
| Half horizontal | `_build/half_horizontal.png` |
| Half vertical | `_build/half_vertical.png` |
| Quadrant | `_build/quadrant.png` |

## What the full layout shows

- A rolling week: today is the first column, seven columns by default. Set
  **First column** to `week` to pin column one to the start of your week instead.
- Hour rows for a window derived from your calendar plugin's own scroll time, so
  the day fills the screen instead of wasting rows on 02:00. Override with the
  **First hour** / **Last hour** fields.
- Timed events as bordered blocks positioned and sized by their real times.
  Overlapping events split the column the way Google Calendar does — only the
  events that actually collide get narrower. Anything currently in progress is
  drawn inverted. A fourth concurrent event becomes a `+1` badge rather than
  hiding a block.
- All-day events in a band under the day headings, one chip per day covered,
  overflowing to `+N more`.
- Today's column carries a now-line with a marker dot.
- Weather strip: current icon, temperature, conditions, feels-like and humidity,
  then today's and tomorrow's high/low.

Half and quadrant layouts drop the grid — it is unreadable below 800×480 — and
show compact agendas with the same weather line, so the plugin still behaves in
a mashup.

## Setting it up on TRMNL

1. **Connect the two source plugins** (Calendar with a Google account, and
   Weather) if you have not already, and add each to a playlist. Hide them with
   the eyeball icon if you don't want to see their native screens — but they must
   stay on a playlist, because only playlist plugins sync fresh data.
2. Set the calendar instance's layout to **Week**. That makes it emit
   `scroll_time` / `scroll_time_end` and a week's worth of events, which is what
   this plugin reads.
3. **Plugins → Private Plugin → New**, strategy **Plugin Merge**.
4. Add two custom fields via the form builder, or import `src/settings.yml`:
   - `calendar_source`, type `plugin_instance_select`, `plugin_keyname: google_calendar`
   - `weather_source`, type `plugin_instance_select`, `plugin_keyname: weather`
   Plus the optional `days`, `week_start`, `hour_from`, `hour_to` fields.
5. **Edit Markup** and paste `src/full.liquid` into the Full field (and the other
   three files into their fields if you plan to use mashups).
6. Tick **Remove screen padding** — the grid is designed to bleed to the edges.
7. Save, pick your two sources in the plugin's settings, then **Force Refresh**.

No form fields? The template falls back to hard-coded merge variables. Open the
Merge Variables dropdown in the markup editor, find the nodes named
`<plugin_keyname>_<plugin_setting_id>` (e.g. `google_calendar_12345`), and edit
the two `assign` lines at the top of the template.

Refresh cadence follows your playlist schedule: the source plugins refresh on
their own interval and the new values map into this plugin.

## Local preview

`trmnlp` is the official dev server, and `.trmnlp.yml` in this repo already holds
a sample merge payload so the grid renders without touching your account:

```sh
gem install trmnl_preview     # needs Ruby >= 3.4
trmnlp serve                  # http://localhost:4567
```

Or via Docker, with no local Ruby:

```sh
docker run --pull always -p 4567:4567 -v "$(pwd):/plugin" trmnl/trmnlp serve --bind 0.0.0.0
```

If neither is available, `tools/render.py` renders the templates with
python-liquid and a Ruby-compatible `date` filter:

```sh
uv run --with python-liquid --with pyyaml --with python-dateutil \
    tools/render.py full                      # writes _build/full.html
uv run --with python-liquid --with pyyaml --with python-dateutil \
    tools/render.py full sample/dense.yml     # a deliberately awkward payload
```

The PNGs in `_build/` were produced from that HTML with headless Chrome:

```sh
chrome --headless=new --window-size=800,480 --hide-scrollbars \
    --screenshot=_build/full.png _build/full.html
```

## Customising the look

Everything visual lives in the `<style>` block at the top of each template.
The knobs worth knowing:

- `--ink` / `--paper` resolve through the framework's `--black` / `--white`
  tokens, so dark mode inverts correctly. Don't hard-code hex values.
- `--gut` (hour-label column), `--wx-h` (weather strip), `--head-h` (day
  headings) are plain pixel heights; the time grid takes the remainder.
- Text sizing uses the framework's `text--small` / `text--base` / `text--large`
  utilities rather than fixed font sizes, so the correct pixel font is picked per
  device and density. `settings.yml` pins `framework_version: '3.2'`.
- Event blocks are white with a black rule and a 4px black left edge. For the
  heavier native look, swap `.cw__ev` to `background: var(--ink); color: var(--paper)`.

## Data it relies on

From the calendar plugin: `events` (each with `summary`, `description`,
`all_day`, `start_full`, `end_full`, `start`, `end`), plus `today_in_tz`,
`scroll_time`, `scroll_time_end`, `first_day`, `time_format`,
`include_description`. From the weather plugin: `temperature`, `feels_like`,
`humidity`, `conditions`, `weather_image`, `today_weather_image`,
`tomorrow_weather_image`, and `forecast.today` / `forecast.tomorrow` with
`mintemp`, `maxtemp`, `day_override`.

The event list is accepted either as a flat array or as a hash grouped by date
label — both shapes exist in the wild — and is flattened before use. If your
payload turns out to be shaped differently, the grid says so on screen rather
than rendering blank. Check yours at
`https://trmnl.com/plugins/google_calendar?data=true&plugin_setting_id=<id>`.

Weather icons load from `https://trmnl.com/images/plugins/weather/<name>.svg`.
If `weather_image` already holds a full URL (the Tempest plugin does this), it is
used as-is.

## Known limitations

- Three side-by-side events per day; a fourth concurrent event is counted in a
  `+1` badge instead of being drawn.
- An event running past midnight is drawn on its start day only, clipped at the
  bottom of the grid, rather than continuing into the next column.
- Multi-day all-day events repeat as a chip on each day they cover rather than
  drawing one bar across the columns.
- `trmnlp lint` reports `LimitedInlineStyles`: it counts CSS property names
  anywhere in the markup and caps them at six, which a hand-built grid exceeds.
  It is advisory and only gates the optional GitHub Actions workflow.
- The now-line and the in-progress highlight need `trmnl.user.utc_offset`; if it
  is missing they fall back to server time, and the now-line is suppressed when
  the derived date disagrees with the calendar plugin's own date.

## References

- Plugin Data API and the Plugin Merge strategy — https://docs.trmnl.com/go/private-api/plugin-data
- Custom plugin form builder, incl. `plugin_instance_select` — https://help.trmnl.com/en/articles/10513740-custom-plugin-form-builder
- Framework 3.2 docs (view, layout, border, text size, tokens) — https://trmnl.com/framework
- Native plugin markup and data shapes — https://github.com/usetrmnl/plugins (`lib/calendar`, `lib/weather`)
- `trmnlp` dev server — https://github.com/usetrmnl/trmnlp
