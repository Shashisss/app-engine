"""Turn a one-line idea into a buildable app specification.

Deliberately deterministic: keyword map in, spec out. No model call, no API key,
same idea always produces the same app — which makes it testable and lets the
person see exactly what the engine understood before it builds anything.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Field:
    name: str
    label: str
    type: str = "text"  # text | long_text | number | date | select | bool
    options: list[str] = field(default_factory=list)
    required: bool = False

    @property
    def key(self) -> str:
        return self.name

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AppSpec:
    name: str
    slug: str
    kind: str  # records | calculator
    entity: str
    entity_plural: str
    description: str
    fields: list[Field]
    categories: list[str] = field(default_factory=list)
    formula: str = ""  # calculator only: python expression over the inputs
    formula_label: str = ""
    idea: str = ""

    def as_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["fields"] = [f.as_dict() for f in self.fields]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSpec":
        payload = dict(data)
        payload["fields"] = [Field(**f) for f in payload.get("fields", [])]
        return cls(**payload)

    @property
    def numeric_field(self) -> str | None:
        return next((f.name for f in self.fields if f.type == "number"), None)

    @property
    def select_field(self) -> Field | None:
        return next((f for f in self.fields if f.type == "select"), None)

    @property
    def date_field(self) -> str | None:
        return next((f.name for f in self.fields if f.type == "date"), None)


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return cleaned or "app"


DEFAULTS: dict[str, dict[str, Any]] = {
    "habit": {
        "entity": "Habit",
        "fields": [
            ("name", "Habit", "text", True),
            ("category", "Category", "select", False),
            ("target", "Target per week", "number", False),
            ("streak", "Current streak", "number", False),
        ],
        "categories": ["Health", "Learning", "Work", "Personal"],
        "description": "Track habits, targets and streaks week by week.",
    },
    "expense": {
        "entity": "Expense",
        "fields": [
            ("name", "What was it", "text", True),
            ("amount", "Amount", "number", True),
            ("date", "Date", "date", True),
            ("category", "Category", "select", False),
            ("notes", "Notes", "long_text", False),
        ],
        "categories": ["Food", "Travel", "Bills", "Fun", "Other"],
        "description": "Log spending, see where it goes by category and over time.",
    },
    "task": {
        "entity": "Task",
        "fields": [
            ("name", "Task", "text", True),
            ("due", "Due", "date", False),
            ("priority", "Priority", "select", False),
            ("status", "Status", "select", False),
            ("notes", "Notes", "long_text", False),
        ],
        "categories": ["Low", "Medium", "High"],
        "description": "A task list with priorities, due dates and status.",
    },
    "inventory": {
        "entity": "Item",
        "fields": [
            ("name", "Item", "text", True),
            ("quantity", "Quantity", "number", True),
            ("unit_cost", "Unit cost", "number", False),
            ("supplier", "Supplier", "text", False),
            ("category", "Category", "select", False),
        ],
        "categories": ["Stock", "Consumable", "Equipment"],
        "description": "Stock levels, unit costs and stock value at a glance.",
    },
    "contact": {
        "entity": "Contact",
        "fields": [
            ("name", "Name", "text", True),
            ("company", "Company", "text", False),
            ("email", "Email", "text", False),
            ("phone", "Phone", "text", False),
            ("stage", "Stage", "select", False),
            ("notes", "Notes", "long_text", False),
        ],
        "categories": ["Lead", "In discussion", "Customer", "Dormant"],
        "description": "A lightweight CRM: contacts, stage and notes.",
    },
    "recipe": {
        "entity": "Recipe",
        "fields": [
            ("name", "Recipe", "text", True),
            ("cuisine", "Cuisine", "select", False),
            ("minutes", "Minutes", "number", False),
            ("servings", "Servings", "number", False),
            ("ingredients", "Ingredients", "long_text", False),
        ],
        "categories": ["Italian", "Indian", "Asian", "European", "Other"],
        "description": "Keep recipes with timings, servings and ingredients.",
    },
    "workout": {
        "entity": "Workout",
        "fields": [
            ("name", "Exercise", "text", True),
            ("date", "Date", "date", True),
            ("sets", "Sets", "number", False),
            ("reps", "Reps", "number", False),
            ("weight", "Weight (kg)", "number", False),
        ],
        "categories": ["Strength", "Cardio", "Mobility"],
        "description": "Log training sessions and watch the volume add up.",
    },
    "book": {
        "entity": "Book",
        "fields": [
            ("name", "Title", "text", True),
            ("author", "Author", "text", False),
            ("status", "Status", "select", False),
            ("rating", "Rating (1-5)", "number", False),
            ("finished", "Finished", "date", False),
        ],
        "categories": ["To read", "Reading", "Finished", "Dropped"],
        "description": "A reading list with status, ratings and finish dates.",
    },
    "booking": {
        "entity": "Booking",
        "fields": [
            ("name", "Who / what", "text", True),
            ("date", "Date", "date", True),
            ("slot", "Slot", "select", False),
            ("status", "Status", "select", False),
            ("notes", "Notes", "long_text", False),
        ],
        "categories": ["Morning", "Afternoon", "Evening"],
        "description": "Reservations by date and slot, with status.",
    },
    "job": {
        "entity": "Application",
        "fields": [
            ("name", "Role", "text", True),
            ("company", "Company", "text", False),
            ("status", "Status", "select", False),
            ("applied", "Applied", "date", False),
            ("notes", "Notes", "long_text", False),
        ],
        "categories": ["Applied", "Screening", "Interview", "Offer", "Rejected"],
        "description": "Track applications from applied to offer.",
    },
    "movie": {
        "entity": "Film",
        "fields": [
            ("name", "Title", "text", True),
            ("genre", "Genre", "select", False),
            ("rating", "Rating (1-10)", "number", False),
            ("watched", "Watched", "date", False),
        ],
        "categories": ["Drama", "Comedy", "Thriller", "Sci-fi", "Other"],
        "description": "A watchlist with genres, ratings and dates.",
    },
}

KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("habit", ("habit", "streak", "routine", "daily habit")),
    ("expense", ("expense", "spending", "budget", "cost tracker", "receipt", "money out")),
    ("task", ("task", "todo", "to-do", "checklist", "kanban", "backlog")),
    ("inventory", ("inventory", "stock", "warehouse", "supplies", "parts")),
    ("contact", ("contact", "crm", "lead", "client", "customer list", "sales pipeline")),
    ("recipe", ("recipe", "cooking", "meal", "kitchen", "food planner")),
    ("workout", ("workout", "gym", "exercise", "training log", "lifting")),
    ("book", ("book", "reading", "library", "novel")),
    ("booking", ("booking", "reservation", "appointment", "room", "slot", "schedule")),
    ("job", ("job application", "application", "job hunt", "interview", "recruit")),
    ("movie", ("movie", "film", "watchlist", "series", "tv show")),
]

CALCULATORS: dict[str, dict[str, Any]] = {
    "loan": {
        "name": "Loan payment calculator",
        "fields": [
            ("principal", "Loan amount", "number"),
            ("rate", "Annual interest rate (%)", "number"),
            ("years", "Term (years)", "number"),
        ],
        "formula": "monthly_payment(principal, rate, years)",
        "label": "Monthly payment",
        "blurb": "Monthly repayment from principal, rate and term.",
    },
    "bmi": {
        "name": "BMI calculator",
        "fields": [
            ("weight", "Weight (kg)", "number"),
            ("height", "Height (cm)", "number"),
        ],
        "formula": "weight / ((height / 100) ** 2)",
        "label": "BMI",
        "blurb": "Body mass index from weight and height.",
    },
    "savings": {
        "name": "Savings growth calculator",
        "fields": [
            ("initial", "Starting amount", "number"),
            ("monthly", "Monthly contribution", "number"),
            ("rate", "Annual return (%)", "number"),
            ("years", "Years", "number"),
        ],
        "formula": "future_value(initial, monthly, rate, years)",
        "label": "Projected balance",
        "blurb": "Compound growth from a starting amount plus monthly contributions.",
    },
    "margin": {
        "name": "Margin calculator",
        "fields": [
            ("cost", "Cost", "number"),
            ("price", "Selling price", "number"),
        ],
        "formula": "(price - cost) / price * 100 if price else 0",
        "label": "Gross margin (%)",
        "blurb": "Gross margin from cost and selling price.",
    },
    "unit": {
        "name": "Unit price comparison",
        "fields": [
            ("price", "Pack price", "number"),
            ("size", "Pack size", "number"),
        ],
        "formula": "price / size if size else 0",
        "label": "Price per unit",
        "blurb": "Price per unit for comparing packs.",
    },
}

CALC_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    ("loan", ("loan", "mortgage", "emi", "repayment", "car finance", "instalment")),
    ("bmi", ("bmi", "body mass")),
    ("savings", ("savings", "compound", "investment growth", "retirement")),
    ("margin", ("margin", "markup", "profit")),
    ("unit", ("unit price", "price per", "compare packs", "per kg", "per litre")),
]


def _has(text: str, words: tuple[str, ...]) -> bool:
    return any(word in text for word in words)


def _clean_name(idea: str, fallback: str) -> str:
    text = idea.strip().rstrip(".!")
    quoted = re.search(r"[\"“']([^\"”']{3,40})[\"”']", idea)
    if quoted:
        return quoted.group(1).strip().title()
    words = [w for w in re.split(r"\s+", text) if w]
    if 2 <= len(words) <= 6 and len(text) <= 48:
        return text[0].upper() + text[1:]
    return fallback


def _plural(word: str) -> str:
    if word.endswith(("s", "x", "ch", "sh")):
        return word + "es"
    if word.endswith("y") and word[-2:-1] not in "aeiou":
        return word[:-1] + "ies"
    return word + "s"


def parse_idea(idea: str) -> AppSpec:
    """Idea in, spec out. Falls back to a generic records app rather than failing."""
    text = f" {idea.lower().strip()} "
    if not text.strip():
        raise ValueError("describe the app you want in a line or two")

    # ---- calculator?
    for key, words in CALC_KEYWORDS:
        if _has(text, words):
            template = CALCULATORS[key]
            name = _clean_name(idea, template["name"])
            return AppSpec(
                name=name,
                slug=slugify(name),
                kind="calculator",
                entity="Calculation",
                entity_plural="Calculations",
                description=template["blurb"],
                fields=[Field(f[0], f[1], f[2], []) for f in template["fields"]],
                formula=template["formula"],
                formula_label=template["label"],
                idea=idea.strip(),
            )

    # ---- records
    domain = "generic"
    for key, words in KEYWORDS:
        if _has(text, words):
            domain = key
            break

    if domain == "generic":
        spec = AppSpec(
            name=_clean_name(idea, "My list"),
            slug="",
            kind="records",
            entity="Item",
            entity_plural="Items",
            description=idea.strip() or "A simple list with the fields you need.",
            fields=[
                Field("name", "Name", "text", [], True),
                Field("category", "Category", "select", ["General", "Work", "Personal"]),
                Field("amount", "Amount", "number", []),
                Field("date", "Date", "date", []),
                Field("notes", "Notes", "long_text", []),
            ],
            categories=["General", "Work", "Personal"],
            idea=idea.strip(),
        )
        spec.slug = slugify(spec.name)
        return spec

    template = DEFAULTS[domain]
    entity = template["entity"]
    fields: list[Field] = []
    for name, label, ftype, required in template["fields"]:
        options = template["categories"] if ftype == "select" else []
        fields.append(Field(name, label, ftype, list(options), required))

    # categories mentioned in the idea override the defaults
    mentioned = [c for c in template["categories"] if c.lower() in text]
    if len(mentioned) >= 2:
        for f in fields:
            if f.type == "select" and f.name not in {"status", "stage", "priority"}:
                f.options = mentioned
    if entity == "Task" and ("priority" in text or "urgent" in text):
        for f in fields:
            if f.name == "status":
                f.options = ["Todo", "In progress", "Done"]

    name = _clean_name(idea, f"{entity} tracker")
    if len(name) < 4:
        name = f"{entity} tracker"

    return AppSpec(
        name=name,
        slug=slugify(name),
        kind="records",
        entity=entity,
        entity_plural=_plural(entity),
        description=template["description"],
        fields=fields,
        categories=[o for f in fields if f.type == "select" for o in f.options],
        idea=idea.strip(),
    )


EXAMPLES = [
    "A habit tracker with categories, weekly targets and streaks",
    "Expense logger with categories and a monthly chart",
    "Inventory list with quantity, unit cost and supplier",
    "A simple CRM for leads and customers with notes",
    "Reading list with status and ratings",
    "Loan repayment calculator",
    "BMI calculator",
]
