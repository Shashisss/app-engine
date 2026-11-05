"""App Engine — type an idea, get a working app.

Run:  streamlit run streamlit_app.py --server.port 8600
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from engine import auth, generate, limits, llm, runner, tunnels
from engine.spec import EXAMPLES, AppSpec, Field, parse_idea

st.set_page_config(page_title="App Engine", page_icon="🧱", layout="wide")

if auth.configured() and not st.session_state.get("authed"):
    st.title("🧱 App Engine")
    st.caption("Password required — this engine sits on a public link and can spend model quota.")
    with st.form("login"):
        candidate = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Enter", type="primary")
    if submitted:
        if auth.check(candidate):
            st.session_state.authed = True
            st.rerun()
        else:
            st.error("Wrong password.")
    st.stop()

TYPES = ["text", "long_text", "number", "date", "select", "bool"]

if "spec" not in st.session_state:
    st.session_state.spec = None
if "preview" not in st.session_state:
    st.session_state.preview = None
if "source" not in st.session_state:
    st.session_state.source = ""

st.title("🧱 App Engine")

_engine_public = tunnels.url_for(8600)
if _engine_public:
    st.caption(f"Public link for this engine: {_engine_public}")
elif tunnels.enabled():
    with st.expander("You are viewing this on localhost — make it shareable"):
        st.caption("Creates a Cloudflare quick tunnel for this page. Apps get their own links automatically.")
        if st.button("Create public link", key="mkengine"):
            with st.spinner("Opening a tunnel…"):
                link = tunnels.start(8600)
            if link:
                st.success(f"Public link: {link}")
            else:
                st.error("Could not create a tunnel — is cloudflared available?")

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

    status = llm.backend_status()
    use_llm = st.checkbox(
        f"Interpret with the model ({status['model']})" if status["available"] else "Model interpretation unavailable",
        value=status["available"],
        disabled=not status["available"],
        help="Off: keyword rules only, instant and deterministic. On: the model reads the idea first and falls back to rules if it fails.",
    )

    if st.button("Understand the idea", type="primary", disabled=not idea.strip()):
        spec = None
        source = "rules"
        if use_llm:
            with st.spinner("Reading the idea…"):
                spec = llm.interpret(idea)
            if spec:
                source = f"model · {status['model']}"
        if spec is None:
            try:
                spec = parse_idea(idea)
                source = "rules (fallback)" if use_llm else "rules"
            except ValueError as exc:
                st.error(str(exc))
                spec = None
        st.session_state.spec = spec
        st.session_state.source = source if spec else ""
        st.session_state.preview = None

with right:
    st.markdown("**How this works**")
    st.markdown(
        "1. Your words → a spec (kind, entity, fields, categories)\n"
        "2. You edit the spec — nothing is hidden\n"
        "3. Build → a standalone Streamlit app on its own port\n"
        "4. It keeps its own SQLite data and can be downloaded"
    )
    spent = limits.usage()
    st.caption(f"Model calls: {spent['last_hour']}/{spent['hourly_limit']} this hour, {spent['last_day']}/{spent['daily_limit']} today.")
    st.caption("Deterministic by design: the same idea builds the same app.")

spec: AppSpec | None = st.session_state.spec

if spec:
    st.divider()
    badge = f"  ·  parsed by {st.session_state.source}" if st.session_state.source else ""
    st.subheader("What I understood" + badge)
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
                "public": a.get("public_url", ""),
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
        public = runner.public_url(chosen)
        if entry["status"] == "running" and public:
            st.markdown(f"**Public link** [{public}]({public})   ·   local: `{url}`")
        elif entry["status"] == "running" and url:
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
        preview_url = runner.public_url(preview_slug) or runner.url(preview_slug)
        st.components.v1.iframe(preview_url, height=720, scrolling=True)
    elif entry:
        st.info(f"{preview_slug} is not running. Start it from the list above.")

st.divider()
if auth.configured() and st.button("Sign out"):
    st.session_state.authed = False
    st.rerun()

st.caption(
    "Generated apps are plain Streamlit files on disk — `apps/<slug>/app.py` — with their own SQLite data. "
    "They keep working if this engine is stopped."
)
