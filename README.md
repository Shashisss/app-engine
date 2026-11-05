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
