# Week + Weather — TRMNL plugin merge

A single TRMNL private plugin that draws a rolling-week time grid in the style of
Google Calendar's week view, under a weather strip with an hourly temperature
graph. It fetches nothing itself: the **Plugin Merge** strategy hands it the
parsed JSON of plugins you already have connected.

Three sources, all selected from dropdowns in the plugin's own settings:

| Field | Plugin | Supplies |
|---|---|---|
| `calendar_source` | Google Calendar | events, colours, and the display preferences set on that plugin |
| `weather_source` | Weather (any provider) | now, today, tomorrow |
| `hourly_source` | Weather Glance recipe | the next few hours, drawn as bars — optional |

**Target panel: 800×600, 2-bit greyscale** — a Kindle 4 in landscape, about
167 PPI. That is denser than the TRMNL original (800×480 at ~137 PPI), so type
is physically smaller for the same pixel size; the layout spends the extra
height on larger text rather than on more rows. Set **Screen height** if your
panel is a different size.

Preview renders, from the sample payload in `.trmnlp.yml`:

| Layout | File | Size |
|---|---|---|
| Full | `_build/full.png` | 800×600 |
| Full, stress payload | `_build/full-dense.png` | 800×600 |
| Half horizontal | `_build/half_horizontal.png` | 800×300 |
| Half vertical | `_build/half_vertical.png` | 400×600 |
| Quadrant | `_build/quadrant.png` | 400×300 |

## What the full layout shows

- A rolling week: today is the first column, seven columns by default. Set
  **First column** to `week` to pin column one to the start of your week.
- Hour rows covering the window your calendar plugin already computes
  (`scroll_time` … `scroll_time_end`), so the day fills the screen instead of
  wasting rows on 03:00. Override with **First hour** / **Last hour**. Each hour
  label is centred on its own gridline with a tick running into the grid, so
  there is no guessing whether a label names the row above it or below it.
- The window is capped at 14 hours (fewer on a short panel) so that one 06:00
  or 23:00 outlier cannot squeeze the working day into unreadable rows. When the
  window is inferred rather than asked for, empty hours are also trimmed off the
  tail. Events left outside it are counted in a `+N` badge on the day heading.
- Timed events as blocks positioned and sized by their real times. Blocks carry
  no start time — read across to the hour column, which is labelled in full
  (`9 AM`, `12 PM`) — so the width goes to the title instead. Overlapping events
  split the column the way Google Calendar does: only the events that actually
  collide get narrower. A fourth concurrent event becomes a `+1` badge rather
  than hiding a block.
- Every event label is 12px — one size throughout. The framework's pixel fonts
  come at 12, 16 and 21 only, so this is one step below the hour labels, which
  stay at 16px as the time reference. Blocks of 28px or more wrap to two lines.
  A block narrower than about 44px cannot hold a legible word, so it drops the
  title and becomes a solid marker instead of printing three characters and an
  ellipsis.
- **Each calendar gets its own greyscale edge bar** — solid, dark, mid, light,
  assigned per distinct `background_color`. The greys come from the framework's
  `--bg-gray-N-*` tokens, so on a 2-bit panel they resolve to real grey levels
  and on a 1-bit panel to dither tiles. Anything in progress is drawn inverted; anything with
  "Cancel" in the title gets a dashed outline instead of a solid one.
- Weekend columns and their all-day cells shaded with a pale tile; today's
  heading inverted. Both follow the `shade_weekends` and `highlight_today`
  settings on the calendar plugin. The heading text itself is never shaded — a
  tile behind 12px type breaks up the glyphs.
- All-day events in a band under the headings, one outlined chip per day
  covered, overflowing to `+N more`. Inversion is reserved for today and for
  anything in progress, so it keeps meaning something.
- A now-line with a marker dot across today's column, dashed ink-on-paper so it
  stays legible where it crosses an in-progress event, which is filled with ink —
  a solid line vanished there, exactly where it mattered most.
- Weather strip on the same column track as the grid: current conditions sit
  over today's column, tomorrow's high/low over tomorrow's column, and the
  hourly graph fills the columns after that. Without an hourly source the strip
  shrinks and the grid takes the space back.
- The graph is a row of **rounded pills: height is temperature, fill darkens as
  the sun goes down** — read from the weather source's own sunrise and sunset,
  falling back to 06:00/19:00 —

  | Fill | Hour |
  |---|---|
  | empty | full daylight |
  | light grey | within an hour of sunrise or sunset |
  | dark grey | twilight, up to two hours past |
  | solid | night |

  Those are the four levels a 2-bit panel renders flat, with no dither texture to
  muddy them at pill size; on 1-bit the middle two fall back to tiles. The ramp
  is monotonic through the evening, so the strip reads as dusk falling rather
  than as an arbitrary pattern. The nearest hour gets a ring around its pill
  rather than a different fill, so fill stays a pure daylight signal.
- Locations appear inside long events when they are a real place rather than a
  Teams or Zoom link.

Half and quadrant layouts drop the grid — unreadable in a mashup cell — and show
compact agendas with a one-line weather header. They do not carry the calendar
tones. They share the full layout's weather-icon mapping but are otherwise still
laid out for the 800×480 original, so they leave dead space on a 600px panel.

## Installing this on your own account

Nothing in the markup is account-specific, so there is no code to edit:

1. **Connect the sources** — a Google Calendar plugin, a Weather plugin, and
   optionally the Weather Glance recipe. Each must sit on a playlist (hidden is
   fine) or its data never refreshes.
2. **Create the plugin** — Plugins → Private Plugin → New, strategy **Plugin
   Merge**, and tick **Remove screen padding**.
3. **Add the custom fields** from `src/settings.yml`, or push the whole project
   with `python tools/push.py`, which uploads them for you. The three
   `plugin_instance_select` fields are what make it installable: they render as
   dropdowns of *your* instances.
4. **Paste the markup** from `src/*.liquid` into the matching fields.
5. **Pick your three sources** in the plugin's own settings, save, then **Force
   Refresh**. Until they are picked the plugin shows a first-run message rather
   than an empty grid.

**Order matters:** re-uploading `settings.yml` replaces the field *definitions*,
which can clear the selected *values*. Push first, pick your sources second.

Every custom field is **required unless it says `optional: true`** — an empty
required field blocks the whole settings form from saving, which silently takes
the source pickers down with it. `hourly_source`, `hour_from`, `hour_to` and
`screen_height` are all marked optional for that reason; the two that stay
required are the calendar and the weather, which the plugin genuinely cannot
run without.

## Setting it up on TRMNL

1. **Connect the source plugins** and add each to a playlist. Hide them with the
   eyeball icon if you don't want their native screens — but they must stay on a
   playlist, because only playlist plugins sync fresh data.
2. Set the calendar instance's layout to **Week** (or rolling week). That is what
   makes it emit `scroll_time`, `scroll_time_end` and a week of events.
3. **Plugins → Private Plugin → New**, strategy **Plugin Merge**.
4. Add the custom fields from `src/settings.yml` — or push the whole project with
   `python tools/push.py`, which uploads them for you.
5. Paste `src/full.liquid` into the Full markup field, and the other three files
   into theirs if you use mashups.
6. Tick **Remove screen padding**; the grid is designed to bleed to the edges.
7. Save, pick your sources in the plugin's settings, then **Force Refresh**.

TRMNL aliases whatever the installer picks in a `plugin_instance_select` field
under that field's keyname, so **the keyname is the data**. Shapes differ by
source type: a native plugin exposes its snapshot flat (`calendar_source.events`)
while a private plugin or webhook source nests it
(`hourly_source.merge_variables.temperatures`). Each template resolves whichever
is present, the same way TRMNL's own recipes do:

```liquid
{%- assign cal = calendar_source.merge_variables | default: calendar_source -%}
```

**No plugin ids appear in the markup, by design.** An author's id means nothing
on an installer's account — a fork would resolve the alias and render blank — so
CI fails the build if one is reintroduced, mirroring the spec in
`usetrmnl/trmnl-liquid-components`. The Merge Variables dropdown
(`<plugin_keyname>_<plugin_setting_id>`) reaches the same data but pins the
plugin to one account, so it is only useful for one-off debugging.

Refresh cadence follows your playlist schedule: the sources refresh on their own
interval and the new values map into this plugin.

## Publishing

`trmnlp push` needs Ruby or Docker. `tools/push.py` speaks the same private API
with the standard library only:

```sh
python tools/push.py --dry-run   # check the key, list what would go up
python tools/push.py             # create or update the plugin
python tools/push.py --id 12345  # push to a specific existing plugin
```

It reads `TRMNL_API_KEY` from the environment or `.env` (gitignored), uploads
`src/*` as a flat zip, and writes the server's canonical `settings.yml` back over
the local one — that is how the plugin id persists, so later pushes update in
place. That rewrite drops the comments from `src/settings.yml`; `git diff` shows
exactly what changed.

### From CI

`.github/workflows/push-trmnl.yml` follows the workflow `trmnlp init` scaffolds:
a **lint** job on every PR and push, and a **push** job that runs
`trmnlp push --force` from `main`. It needs the `TRMNL_API_KEY` repository
secret. CI uses the official gem rather than `tools/push.py`, which exists for
local pushes on machines without Ruby.

It adds one thing the scaffold does not have: a guard on the plugin id.
`trmnlp push` **creates a new plugin when it cannot find an id**, so a workflow
that ran without one would make a fresh duplicate every time. The id is resolved
from the `TRMNL_PLUGIN_ID` repository variable, or failing that from `id:` in
`src/settings.yml`; with neither, the run stops rather than guessing. To make the
plugin the first time, either:

- push once locally (`python tools/push.py`) and commit the `src/settings.yml`
  the server hands back, which is the id-bearing version; or
- run the workflow manually with **allow_create** ticked — it will create the
  plugin and commit the new `settings.yml` back to the branch itself. That
  commit is marked `[skip ci]`, because it touches `src/` and would otherwise
  retrigger the workflow that made it.

`--force` skips the "settings will be overwritten" confirmation, which has no
stdin on a runner.

**This repo is also connected to TRMNL's GitHub Sync app.** That syncs one way
automatically — saving the plugin in the TRMNL UI commits the server's
`settings.yml` here as *"Updated from TRMNL"*. The other direction is manual:
Sync only offers an import button. Automating that direction is what this
workflow is for. The push job skips commits authored by `trmnl-sync[bot]`, or
the two would chase each other: a push from here changes the plugin, which
triggers a sync commit, which would trigger another push. The settings write-back
also tolerates losing a race with the Sync app, since the id is committed
already and nothing is lost by skipping it.

Note that the Sync app writes the server's canonical `settings.yml`, which has
**no `custom_fields`** — the form definitions live only in this repo. Take care
not to let a sync commit drop them; that is what happened when plugin 455834 was
first created.

The write-back needs `contents: write`, which the workflow requests. If your
repository or organisation caps the `GITHUB_TOKEN` to read-only, set
`TRMNL_PLUGIN_ID` instead and the workflow never needs to commit.

## Local preview

`.trmnlp.yml` carries a sample merge payload shaped like the real thing, so the
grid renders without touching your account:

```sh
gem install trmnl_preview     # needs Ruby >= 3.4
trmnlp serve                  # http://localhost:4567
```

With no Ruby, `tools/render.py` renders the templates using python-liquid and a
Ruby-compatible `date` filter:

```sh
uv run --with python-liquid --with pyyaml --with python-dateutil     tools/render.py full                      # writes _build/full.html
uv run --with python-liquid --with pyyaml --with python-dateutil     tools/render.py full sample/dense.yml     # a deliberately awkward payload
```

It wraps the markup in the same classes the hosted renderer applies:
`screen--no-bleed` (what **Remove screen padding** sets), the bit depth, and the
device class carrying `--screen-w` / `--screen-h`. Defaults are
`--device amazon_kindle_7 --bits 2`, i.e. 800×600 2-bit; pass `--device og` for
the 800×480 original. Without those classes the preview renders 780×460 inside a
10px margin the panel does not have.

Each run prints the exact headless-Chrome command for that view, sized to the
device — mashup cells are clipped to their share of the screen:

```sh
chrome --headless=new --window-size=800,600 --hide-scrollbars     --virtual-time-budget=8000 --screenshot=_build/full.png _build/full.html
```

Both sample payloads pin `trmnl.system.timestamp_utc`, so renders are
reproducible. Without it the now-line, the in-progress highlight and therefore
the committed PNGs all drift with the wall clock.

**Do not put real calendar data in `.trmnlp.yml` or `sample/` — this repository
is public.** The sample events are invented; only their shape is real.

## Customising the look

Everything visual is in the `<style>` block at the top of each template:

- `--ink` / `--paper` resolve through the framework's `--black` / `--white`
  tokens, so dark mode inverts correctly. Don't hard-code hex values.
- Greys come from the framework's `--bg-gray-N-color` / `--bg-gray-N-image`
  pairs (N runs 1 lightest … 75 darkest) with `--dither-bg-size`. They drive the
  calendar edge bars, the graph bars and the weekend shading. Because they are
  the framework's own tokens they follow `--framework-bit-depth`: flat grey on a
  2-bit panel, dither tiles on 1-bit. Don't reintroduce the `gray-N.png` files —
  those are fixed 1-bit and cost four network fetches per render.
- `--gut`, `--wx-h`, `--head-h` are the hour-label column, weather strip and day
  heading heights in pixels; the grid takes what is left. `--gut` narrows
  automatically on a 24-hour clock, where the widest label is `23` not `12 PM`.
- Text uses the framework's `text--small` (12px) / `text--base` (16px) /
  `text--large` (21px) utilities. These are bitmap pixel fonts — TRMNL12,
  TRMNL16, TRMNL21 — so those three sizes are the only crisp ones; don't invent
  intermediate sizes. `settings.yml` pins `framework_version: '3.2'`.
- Event labels pin `line-height` to 1, so a label is exactly its font size tall.
  That is what lets a 30-minute block carry a line without shaving the
  descenders off it, and it is what sets the block height thresholds below.
- **Spacing comes from the framework's `p--N` / `px--N` / `m--N` utilities, not
  from CSS.** `trmnlp lint` gates the build on `LimitedInlineStyles`, which
  counts the strings `padding`, `margin`, `background-color`, `border-radius`,
  `justify-content`, `text-align`, `object-fit` and `font-size` anywhere in the
  markup — `<style>` blocks included — and caps them at six across all four
  templates. The scale is 4px per step (`p--1` = 4px). Two substitutions keep
  the rest honest: `background:` instead of `background-color:` (put the
  shorthand *before* any `background-image`, which it resets), and
  `place-content:` instead of `justify-content:` — equivalent here, because
  every one of these flex containers is single-line, where `align-content` has
  no effect.

## Data it relies on

**Calendar**: `events[]` with `summary`, `start_full`, `end_full`, `start`,
`end`, `all_day`, `location`, `background_color`; plus `today_in_tz` (a full
timestamp — only its UTC offset is read, because `trmnl.user.utc_offset` reads 0
on accounts with no time zone set; the date itself comes from the clock, so the
columns, the today highlight and the now-line cannot disagree), `scroll_time`,
`scroll_time_end`,
`first_day`, `time_format`, `shade_weekends`, `colorize_events`,
`highlight_today`.

**Weather**: `temperature`, `weather_image`, `tomorrow_weather_image`, and
`forecast.tomorrow` / `forecast.right_now`. (Feels-like and humidity are read by
the mashup layouts only — the full strip drops them for width.) Conditions fall back through
`conditions` → `right_now_conditions` → `forecast.right_now.conditions`, since
the Tempest provider omits the first. Icon values may be bare names or absolute
URLs, and either may be colour art; both are reduced to a slug and mapped onto
TRMNL's mono `wi-*` set, which is what survives a 2-bit panel. Unrecognised
values fall back to `wi-na`.

**Hourly**: the recipe is a *private* plugin, and a private plugin's merge
variable exposes the plugin **definition** (markup blob ids, custom field
values), not its data — the recipe's own output is one level down under
`merge_variables`, and may nest again under `data`. The template unwraps both
and only adopts a candidate that actually yields temperatures. Keys read:
`current_temp`, `temperatures` (array of arrays),
`timestamps_formatted` and `weather_icons` (which drives the pill fills — absent,
every pill takes the partly-cloudy level), read from the node directly or from
its `data` child.
Temperatures always come from this source when it has them — including the
headline figure — so the number and the graph agree; everything else (icon,
conditions, tomorrow's high/low) stays with the weather plugin.

To check your own payloads:
`https://trmnl.com/plugins/google_calendar?data=true&plugin_setting_id=<id>`.

## Known limitations

- Three side-by-side events per day; a fourth concurrent event is counted in a
  `+1` badge instead of being drawn.
- At seven columns a three-way overlap leaves ~35px per block, which cannot hold
  a word, so those render as unlabelled markers. Fewer day columns widens them.
  A two-way overlap keeps its label but fits only ten or so characters.
- An event running past midnight is drawn on its start day only, clipped at the
  bottom of the grid.
- Multi-day all-day events repeat as a chip on each day they cover rather than
  drawing one bar across the columns.
- Tones are assigned by sorted `background_color`, so a calendar's shade can move
  if a calendar has no events at all in the visible week.
- The strip, heading and all-day band are fixed pixel heights rather than
  multiples of the framework's `--ui-scale`, so they do not grow on a panel with
  a device scale other than 1. The grid itself takes whatever is left.
- The `+1` lane-spill badge sits in the bottom-right of its column and can cover
  the corner of the block beneath it. Window-overflow counts moved to the day
  heading for this reason; the spill count stays put because it belongs next to
  the stack it came from.
- Only the full layout has had the column-aligned weather strip, the no-times
  treatment and the 800×600 sizing; the mashup layouts still print a time per
  row, which is what makes sense in a list.
- The mashup layouts no longer reset `.layout` padding, so on the hosted
  renderer they pick up the framework's `var(--gap)` cell padding. The local
  harness has no `.layout` element, so that cannot be previewed here.

## References

- Plugin Data API and the Plugin Merge strategy — https://docs.trmnl.com/go/private-api/plugin-data
- Custom plugin form builder, incl. `plugin_instance_select` — https://help.trmnl.com/en/articles/10513740-custom-plugin-form-builder
- Framework 3.2 docs — https://trmnl.com/framework
- Native plugin markup and data shapes — https://github.com/usetrmnl/plugins
- `trmnlp` dev server — https://github.com/usetrmnl/trmnlp
