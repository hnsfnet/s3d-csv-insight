import math
import os

import numpy as np
import pandas as pd
import pytest

from stats import (
    ColumnTypes,
    build_compare_statistics,
    build_statistics_table,
    detect_column_types,
    missing_summary,
)


def _read(name, fixtures_dir):
    return pd.read_csv(os.path.join(fixtures_dir, name))


def test_detect_column_types_pure_numeric(fixtures_dir):
    df = pd.DataFrame({
        "a": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0,
              11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0, 20.0],
        "b": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0,
              110.0, 120.0, 130.0, 140.0, 150.0, 160.0, 170.0, 180.0, 190.0, 200.0],
    })
    ct = detect_column_types(df)
    assert "a" in ct.numeric
    assert "b" in ct.numeric
    assert ct.categorical == []
    assert ct.date == []


def test_detect_column_types_low_cardinality_numeric_becomes_categorical():
    df = pd.DataFrame({
        "id": [1, 2, 3, 1, 2, 3, 1, 2, 3, 1],
        "score": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100,
                  110, 120, 130, 140, 150, 160, 170, 180, 190, 200],
    })
    ct = detect_column_types(df)
    assert "id" in ct.categorical
    assert "score" in ct.numeric


def test_detect_column_types_categorical(fixtures_dir):
    df = _read("utf8_normal.csv", fixtures_dir)
    ct = detect_column_types(df)
    assert "name" in ct.categorical
    assert "city" in ct.categorical


def test_detect_column_types_date(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    assert "visit_date" in ct.date


def test_detect_column_types_empty():
    df = pd.DataFrame()
    ct = detect_column_types(df)
    assert ct.numeric == []
    assert ct.categorical == []
    assert ct.date == []


def test_safe_numeric_stats_with_nulls(fixtures_dir):
    df = _read("numeric_with_nulls.csv", fixtures_dir)
    ct = detect_column_types(df)
    num_stats, cat_stats = build_statistics_table(df, ct)

    value_row = num_stats[num_stats["列名"] == "value"].iloc[0]
    non_null_values = [10.0, 20.0, 40.0, 60.0, 70.0, 90.0, 100.0]
    expected_mean = round(float(np.mean(non_null_values)), 4)
    expected_median = round(float(np.median(non_null_values)), 4)
    expected_std = round(float(np.std(non_null_values, ddof=1)), 4)

    assert math.isclose(value_row["均值"], expected_mean, rel_tol=1e-4)
    assert math.isclose(value_row["中位数"], expected_median, rel_tol=1e-4)
    assert math.isclose(value_row["标准差"], expected_std, rel_tol=1e-4)
    assert value_row["最小值"] == 10.0
    assert value_row["最大值"] == 100.0
    assert value_row["缺失值"] == 3


def test_safe_numeric_stats_all_null():
    s = pd.Series([np.nan, np.nan, np.nan])
    ct = ColumnTypes(numeric=["x"], categorical=[], date=[])
    df = pd.DataFrame({"x": s})
    num_stats, _ = build_statistics_table(df, ct)
    row = num_stats.iloc[0]
    assert row["均值"] is None
    assert row["中位数"] is None
    assert row["标准差"] is None
    assert row["最小值"] is None
    assert row["最大值"] is None
    assert row["缺失值"] == 3


def test_categorical_stats(fixtures_dir):
    df = _read("numeric_with_nulls.csv", fixtures_dir)
    ct = detect_column_types(df)
    _, cat_stats = build_statistics_table(df, ct)
    cat_row = cat_stats[cat_stats["列名"] == "category"].iloc[0]
    assert cat_row["唯一值"] == 3
    assert cat_row["最高频"] in ("A", "B")
    assert cat_row["最高频次数"] == 4


def test_mixed_types_statistics(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    num_stats, cat_stats = build_statistics_table(df, ct)

    height_row = num_stats[num_stats["列名"] == "height"].iloc[0]
    assert height_row["均值"] is not None
    assert height_row["缺失值"] == 0

    gender_row = cat_stats[cat_stats["列名"] == "gender"].iloc[0]
    assert gender_row["唯一值"] == 2


def test_missing_summary(fixtures_dir):
    df = _read("numeric_with_nulls.csv", fixtures_dir)
    s = missing_summary(df)
    assert s["rows"] == 10
    assert s["columns"] == 4
    assert s["missing_total"] == 3


def test_build_compare_statistics(fixtures_dir):
    df1 = pd.DataFrame({"x": [1, 2, 3, 4, 5], "g": ["a", "a", "b", "b", "c"]})
    df2 = pd.DataFrame({"x": [10, 20, 30, 40, 50], "g": ["a", "a", "a", "b", "b"]})
    ct1 = detect_column_types(df1)
    ct2 = detect_column_types(df2)
    num_cmp, cat_cmp = build_compare_statistics(df1, df2, ct1, ct2, "D1", "D2")

    x_row = num_cmp[num_cmp["列名"] == "x"].iloc[0]
    assert x_row["均值 [D1]"] == 3.0
    assert x_row["均值 [D2]"] == 30.0

    g_row = cat_cmp[cat_cmp["列名"] == "g"].iloc[0]
    assert g_row["唯一值 [D1]"] == 3
    assert g_row["唯一值 [D2]"] == 2
