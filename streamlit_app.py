"""App Engine — type an idea, get a working app.

Run:  streamlit run streamlit_app.py --server.port 8600
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from engine import generate, runner
from engine.spec import EXAMPLES, AppSpec, Field, parse_idea

st.set_page_config(page_title="App Engine", page_icon="🧱", layout="wide")

TYPES = ["text", "long_text", "number", "date", "select", "bool"]

if "spec" not in st.session_state:
    st.session_state.spec = None
if "preview" not in st.session_state:
    st.session_state.preview = None

st.title("🧱 App Engine")
st.caption("Describe the app you want. It gets parsed into a spec you can see and edit, then built into a running Streamlit app.")

left, right = st.columns([3, 2], gap="large")

def use_example(text: str) -> None:
    """Runs before the widget is instantiated, so it may set its value."""
    st.session_state.idea_text = text


with left:
    idea = st.text_area(
        "What should it do?",
        height=110,
        placeholder="e.g. A habit tracker with categories, weekly targets and streaks",
        key="idea_text",
    )
    st.caption("Examples")
    cols = st.columns(2)
    for i, example in enumerate(EXAMPLES[:6]):
        cols[i % 2].button(
            example, key=f"ex_{i}", use_container_width=True, on_click=use_example, args=(example,)
        )

    if st.button("Understand the idea", type="primary", disabled=not idea.strip()):
        try:
            st.session_state.spec = parse_idea(idea)
            st.session_state.preview = None
        except ValueError as exc:
            st.error(str(exc))

with right:
    st.markdown("**How this works**")
    st.markdown(
        "1. Your words → a spec (kind, entity, fields, categories)\n"
        "2. You edit the spec — nothing is hidden\n"
        "3. Build → a standalone Streamlit app on its own port\n"
        "4. It keeps its own SQLite data and can be downloaded"
    )
    st.caption("Deterministic by design: the same idea builds the same app.")

spec: AppSpec | None = st.session_state.spec

if spec:
    st.divider()
    st.subheader("What I understood")
    top = st.columns([2, 1, 1])
    name = top[0].text_input("App name", value=spec.name)
    kind = top[1].selectbox("Kind", ["records", "calculator"], index=0 if spec.kind == "records" else 1)
    entity = top[2].text_input("Entity", value=spec.entity, disabled=kind == "calculator")
    description = st.text_input("Description", value=spec.description)

    if kind == "records":
        st.markdown("**Fields**")
        frame = pd.DataFrame(
            [
                {
                    "name": f.name,
                    "label": f.label,
                    "type": f.type,
                    "options": ", ".join(f.options),
                    "required": f.required,
                }
                for f in spec.fields
            ]
        )
        edited = st.data_editor(
            frame,
            num_rows="dynamic",
            use_container_width=True,
            hide_index=True,
            column_config={
                "type": st.column_config.SelectboxColumn("type", options=TYPES, required=True),
                "options": st.column_config.TextColumn("options (comma separated)", width="medium"),
                "required": st.column_config.CheckboxColumn("required"),
            },
        )
        fields: list[Field] = []
        for _, row in edited.iterrows():
            field_name = str(row.get("name") or "").strip()
            if not field_name:
                continue
            fields.append(
                Field(
                    name=field_name,
                    label=str(row.get("label") or field_name.title()),
                    type=str(row.get("type") or "text"),
                    options=[o.strip() for o in str(row.get("options") or "").split(",") if o.strip()],
                    required=bool(row.get("required")),
                )
            )
        spec.fields = fields
        spec.categories = [o for f in fields if f.type == "select" for o in f.options]
    else:
        st.text_input("Formula (read-only)", value=spec.formula or "—", disabled=True)
        st.caption("Calculator specs use a fixed formula per template; edit the template to change maths.")

    spec.name = name
    spec.kind = kind
    spec.entity = entity
    spec.description = description
    spec.slug = generate.unique_slug(generate.slugify(name))

    st.divider()
    build_col, hint_col = st.columns([1, 3])
    with build_col:
        go = st.button("Build & run", type="primary", use_container_width=True)
    with hint_col:
        st.caption(f"Will be created at `apps/{spec.slug}` and served on a free port.")

    if go:
        if spec.kind == "records" and not spec.fields:
            st.error("Add at least one field before building.")
        else:
            folder = generate.build(spec)
            entry = runner.start(spec.slug)
            st.session_state.spec = spec
            if entry.get("status") == "running":
                st.session_state.preview = spec.slug
                st.success(f"Built and running at {runner.url(spec.slug)}")
            else:
                st.warning(f"Built at {folder}, but the app did not become healthy in time. Check the logs below.")

st.divider()
st.subheader("Your apps")
apps = runner.list_apps()
if not apps:
    st.caption("Nothing built yet.")
else:
    table = pd.DataFrame(
        [
            {
                "app": a["slug"],
                "status": a["status"],
                "port": a.get("port"),
                "started": a.get("started_at", ""),
            }
            for a in apps
        ]
    )
    st.dataframe(table, hide_index=True, use_container_width=True)

    chosen = st.selectbox("Select an app", [a["slug"] for a in apps])
    entry = next((a for a in apps if a["slug"] == chosen), None)

    buttons = st.columns(5)
    if buttons[0].button("Open", use_container_width=True):
        st.session_state.preview = chosen
    if buttons[1].button("Restart", use_container_width=True):
        runner.stop(chosen)
        runner.start(chosen)
        st.rerun()
    if buttons[2].button("Stop", use_container_width=True):
        runner.stop(chosen)
        st.rerun()
    if buttons[3].button("Delete", use_container_width=True):
        runner.delete(chosen)
        if st.session_state.preview == chosen:
            st.session_state.preview = None
        st.rerun()
    if buttons[4].button("Reload list", use_container_width=True):
        st.rerun()

    if entry:
        url = runner.url(chosen)
        if entry["status"] == "running" and url:
            st.markdown(f"**Running at** [{url}]({url})")
        else:
            st.warning(f"Status: {entry['status']}. Logs below.")

    with st.expander("Logs"):
        st.code(runner.tail_logs(chosen, 60) or "no logs yet")

preview_slug = st.session_state.preview
if preview_slug:
    entry = next((a for a in runner.list_apps() if a["slug"] == preview_slug), None)
    if entry and entry["status"] == "running":
        st.divider()
        st.subheader(f"Preview — {preview_slug}")
        st.caption("This is the generated app, running as its own process.")
        st.components.v1.iframe(runner.url(preview_slug), height=720, scrolling=True)
    elif entry:
        st.info(f"{preview_slug} is not running. Start it from the list above.")

st.divider()
st.caption(
    "Generated apps are plain Streamlit files on disk — `apps/<slug>/app.py` — with their own SQLite data. "
    "They keep working if this engine is stopped."
)
