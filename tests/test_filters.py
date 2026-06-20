import os

import pandas as pd
import pytest

from filters import (
    FilterConditions,
    apply_categorical_filter,
    apply_date_filter,
    apply_filter_conditions,
    apply_numeric_filter,
)
from stats import ColumnTypes, detect_column_types


def _read(name, fixtures_dir):
    return pd.read_csv(os.path.join(fixtures_dir, name))


def test_apply_numeric_filter_within_bounds():
    s = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
    mask = apply_numeric_filter(s, "x", (2.0, 4.0))
    assert list(s[mask]) == [2.0, 3.0, 4.0]


def test_apply_numeric_filter_none_returns_all_true():
    s = pd.Series([1.0, 2.0, 3.0])
    mask = apply_numeric_filter(s, "x", None)
    assert mask.all()


def test_apply_numeric_filter_edge_included():
    s = pd.Series([10.0, 20.0, 30.0])
    mask = apply_numeric_filter(s, "x", (10.0, 30.0))
    assert mask.sum() == 3


def test_apply_categorical_filter_selected():
    s = pd.Series(["A", "B", "C", "A", "B"])
    mask = apply_categorical_filter(s, "cat", ["A", "C"])
    assert list(s[mask]) == ["A", "C", "A"]


def test_apply_categorical_filter_empty_selected_returns_all():
    s = pd.Series(["A", "B", "C"])
    mask = apply_categorical_filter(s, "cat", [])
    assert mask.all()


def test_apply_categorical_filter_numeric_casted_to_string():
    s = pd.Series([1, 2, 3, 1, 2])
    mask = apply_categorical_filter(s, "id", ["1", "3"])
    assert list(s[mask]) == [1, 3, 1]


def test_apply_date_filter_between_range():
    s = pd.Series(["2024-01-01", "2024-01-05", "2024-01-10", "2024-01-15"])
    start = pd.Timestamp("2024-01-04")
    end = pd.Timestamp("2024-01-11")
    mask = apply_date_filter(s, "d", (start, end))
    assert list(s[mask]) == ["2024-01-05", "2024-01-10"]


def test_apply_date_filter_none_returns_all():
    s = pd.Series(["2024-01-01", "2024-01-02"])
    mask = apply_date_filter(s, "d", None)
    assert mask.all()


def test_apply_filter_conditions_numeric_only(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    cond = FilterConditions()
    cond.numeric_ranges["height"] = (170.0, 175.0)
    result = apply_filter_conditions(df, ct, cond)
    assert len(result.df) >= 1
    assert result.active_count >= 1
    assert result.df["height"].min() >= 170.0
    assert result.df["height"].max() <= 175.0


def test_apply_filter_conditions_categorical_only(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    cond = FilterConditions()
    cond.categorical_selected["gender"] = ["F"]
    result = apply_filter_conditions(df, ct, cond)
    assert (result.df["gender"] == "F").all()
    assert len(result.df) < len(df)


def test_apply_filter_conditions_date_only(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    cond = FilterConditions()
    start = pd.Timestamp("2024-01-05")
    end = pd.Timestamp("2024-01-11")
    cond.date_ranges["visit_date"] = (start, end)
    result = apply_filter_conditions(df, ct, cond)
    for d in result.df["visit_date"]:
        ts = pd.Timestamp(d)
        assert start <= ts < end


def test_apply_filter_conditions_combined(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    cond = FilterConditions()
    cond.categorical_selected["gender"] = ["M"]
    cond.numeric_ranges["weight"] = (70.0, 80.0)
    result = apply_filter_conditions(df, ct, cond)
    assert (result.df["gender"] == "M").all()
    assert result.df["weight"].min() >= 70.0
    assert result.df["weight"].max() <= 80.0


def test_apply_filter_conditions_empty_result(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    cond = FilterConditions()
    cond.numeric_ranges["height"] = (1.0, 2.0)
    result = apply_filter_conditions(df, ct, cond)
    assert len(result.df) == 0


def test_apply_filter_conditions_empty_condition(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    cond = FilterConditions()
    result = apply_filter_conditions(df, ct, cond)
    assert len(result.df) == len(df)
    assert result.active_count == 0


def test_filter_conditions_is_active_counts():
    cond = FilterConditions()
    assert cond.is_active() == 0
    cond.numeric_ranges["a"] = (1.0, 2.0)
    assert cond.is_active() == 1
    cond.categorical_selected["b"] = ["x"]
    assert cond.is_active() == 2
    cond.date_ranges["c"] = (pd.Timestamp("2024-01-01"), pd.Timestamp("2024-01-02"))
    assert cond.is_active() == 3
