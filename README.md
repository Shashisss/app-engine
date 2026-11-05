# App Engine

Type an idea → get a working Streamlit app, running on its own port.

```
"I want a habit tracker with categories and streaks"   →  a habit tracker
"expense logger with categories and a monthly chart"   →  an expense tracker
"loan repayment calculator"                            →  a working calculator
```

## Run it

```bash
pip install -r requirements.txt
streamlit run streamlit_app.py --server.port 8600
```

Open http://localhost:8600, type an idea (or click an example), press **Understand the idea**,
edit the parsed spec if you like, then **Build & run**. The generated app appears in the
preview pane and on its own port (8700, 8701, …).

## How it works

```
idea text
   │  engine/spec.py      keyword map → AppSpec (kind, entity, fields, categories)
   ▼
spec (visible and editable in the UI)
   │  engine/generate.py  Jinja2 template → apps/<slug>/app.py  (valid Python, standalone)
   ▼
process
   │  engine/runner.py    free port, subprocess, health check, registry.json, logs
   ▼
running app  →  preview iframe + direct URL
```

### The model (optional)

The checkbox **"Interpret with the model"** sends the idea to the local `opencode` CLI before the
keyword rules run — same provider this machine already uses, no API key to manage.

```
opencode run --standalone --format json --model opencode-go/deepseek-v4.1-flash "<prompt>"
```

- Default **on** when the CLI is present; uncheck for pure keyword rules (instant, offline).
- Anything the model returns is sanitised: whitelisted field types, valid identifiers, max 10
  fields, calculators restricted to the five known formulas. If it returns junk, times out or the
  CLI is missing, the rules parser takes over and the badge says "rules (fallback)".
- `APP_ENGINE_MODEL=opencode-go/<model>` to switch models, `APP_ENGINE_LLM=off` to disable.
- Results are memoised per idea, so reruns cost nothing.

Deliberate choices:

- **Deterministic, not model-driven.** The same idea always builds the same app. No API key,
  no drift, and the spec is shown so you can see exactly what was understood.
- **Generated apps are plain files.** `apps/<slug>/app.py` plus its own `app.sqlite`-style
  data file — they keep running when the engine stops, and can be zipped and handed over.
- **The spec is editable.** Fields, types, categories and required flags are all in a table
  before anything is generated.

## Templates

| Kind | Covers | What you get |
|---|---|---|
| `records` | habits, expenses, tasks, inventory, contacts, recipes, workouts, books, bookings, jobs, films, anything else | add form, search, filters, table, delete, totals, chart by category or month, CSV export |
| `calculator` | loan/EMI, BMI, savings growth, margin, unit price | inputs, formula, result, history table, CSV export |

The parser recognises ~12 domains plus 5 calculators; anything unrecognised becomes a generic
list with name / category / amount / date / notes rather than failing.

## Public links (container → browser)

`localhost` inside a container is not reachable from your browser, so every app gets its own
Cloudflare quick tunnel:

- on `Build & run`, the app is started and a tunnel is opened for its port — the public URL is
  stored in `apps/registry.json` and shown in the list;
- the preview pane uses the public URL, not `localhost`;
- the engine page itself can open a tunnel for port 8600 from the "make it shareable" panel.

```
APP_ENGINE_TUNNEL=0     disable tunnels (tests do this)
bin/cloudflared         the binary the engine shells out to (not committed)
```

Quick tunnels are ephemeral: their hostname changes if the tunnel process (or the container)
restarts. For a stable address, use a named Cloudflare tunnel or a real host.

## Layout

```
streamlit_app.py       the engine UI
engine/spec.py         idea → spec, examples, domain map
engine/generate.py     template rendering, slugs, build to disk
engine/runner.py       start/stop/status, port allocation, registry, logs
templates/             records_app.py.j2, calculator_app.py.j2
apps/                  generated apps (+ registry.json, _logs/)
tests/                 15 tests: parsing, rendering, boot and delete
```

## Tests

```bash
python -m pytest -q
```

Covers: every example parses, unknown ideas fall back, generated files compile, slugs stay
unique, and one test actually boots a generated app and waits for its health endpoint.
