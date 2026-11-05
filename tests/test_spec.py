"""Idea → spec: the engine must understand the obvious cases and degrade gracefully."""

from __future__ import annotations

from engine.spec import EXAMPLES, parse_idea


def test_habit_idea_becomes_a_records_spec():
    spec = parse_idea("A habit tracker with categories, weekly targets and streaks")
    assert spec.kind == "records"
    assert spec.entity == "Habit"
    assert [f.name for f in spec.fields] == ["name", "category", "target", "streak"]
    assert spec.fields[1].type == "select"
    assert "Health" in spec.fields[1].options
    assert spec.slug and "-" not in spec.slug[:1]


def test_expense_idea_gets_amount_and_date():
    spec = parse_idea("Expense logger with categories and a monthly chart")
    assert spec.entity == "Expense"
    assert spec.numeric_field == "amount"
    assert spec.date_field == "date"
    assert spec.select_field is not None


def test_loan_idea_becomes_a_calculator():
    spec = parse_idea("Loan repayment calculator")
    assert spec.kind == "calculator"
    assert [f.name for f in spec.fields] == ["principal", "rate", "years"]
    assert spec.formula.startswith("monthly_payment")


def test_bmi_and_margin_calculators():
    bmi = parse_idea("BMI calculator")
    assert bmi.kind == "calculator" and "weight" in [f.name for f in bmi.fields]

    margin = parse_idea("margin calculator for product pricing")
    assert margin.kind == "calculator" and "price" in [f.name for f in margin.fields]


def test_unknown_idea_falls_back_to_a_generic_list():
    spec = parse_idea("something for tracking my collection of fountain pen inks")
    assert spec.kind == "records"
    assert spec.entity == "Item"
    assert len(spec.fields) >= 3


def test_every_example_parses():
    for idea in EXAMPLES:
        spec = parse_idea(idea)
        assert spec.name
        assert spec.kind in {"records", "calculator"}
        assert spec.fields


def test_categories_mentioned_in_the_idea_win():
    spec = parse_idea("Expense tracker with categories Food, Travel and Bills")
    categories = spec.fields[3].options
    assert {"Food", "Travel", "Bills"} <= set(categories)


def test_empty_idea_is_rejected():
    import pytest

    with pytest.raises(ValueError):
        parse_idea("   ")
