from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

from stats import ColumnTypes


CATEGORICAL_MAX_UNIQUE = 200


@dataclass
class FilterConditions:
    numeric_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    categorical_selected: Dict[str, List[str]] = field(default_factory=dict)
    date_ranges: Dict[str, Tuple[pd.Timestamp, pd.Timestamp]] = field(default_factory=dict)

    def is_active(self) -> int:
        return (
            len(self.numeric_ranges)
            + len(self.categorical_selected)
            + len(self.date_ranges)
        )


@dataclass
class FilterResult:
    df: pd.DataFrame
    active_count: int


def _make_key(prefix: str, kind: str, col: str) -> str:
    return f"{prefix}{kind}_{col}"


def _clear_filter_keys(numeric_cols, categorical_cols, date_cols, key_prefix):
    for col in numeric_cols:
        k = _make_key(key_prefix, "num", col)
        if k in st.session_state:
            del st.session_state[k]
    for col in categorical_cols:
        k = _make_key(key_prefix, "cat", col)
        if k in st.session_state:
            del st.session_state[k]
    for col in date_cols:
        k = _make_key(key_prefix, "date", col)
        if k in st.session_state:
            del st.session_state[k]


def apply_numeric_filter(series: pd.Series, col: str, bounds: Optional[Tuple[float, float]]) -> pd.Series:
    if bounds is None:
        return pd.Series(True, index=series.index)
    lo, hi = bounds
    return (series >= lo) & (series <= hi)


def apply_categorical_filter(series: pd.Series, col: str, selected: Optional[List[str]]) -> pd.Series:
    if not selected:
        return pd.Series(True, index=series.index)
    return series.astype(str).isin(selected)


def apply_date_filter(series: pd.Series, col: str, bounds: Optional[Tuple[pd.Timestamp, pd.Timestamp]]) -> pd.Series:
    if bounds is None:
        return pd.Series(True, index=series.index)
    converted = pd.to_datetime(series, errors="coerce")
    start, end = bounds
    return (converted >= start) & (converted < end)


def apply_filter_conditions(df: pd.DataFrame, col_types: ColumnTypes, conditions: FilterConditions) -> FilterResult:
    filtered = df.copy()
    for col, bounds in conditions.numeric_ranges.items():
        if col not in df.columns:
            continue
        lo, hi = bounds
        series = df[col]
        original = series.dropna()
        if len(original) == 0:
            continue
        default_lo = float(original.min())
        default_hi = float(original.max())
        if (lo, hi) == (default_lo, default_hi):
            continue
        filtered = filtered[(filtered[col] >= lo) & (filtered[col] <= hi)]

    for col, selected in conditions.categorical_selected.items():
        if col not in df.columns or not selected:
            continue
        filtered = filtered[filtered[col].astype(str).isin(selected)]

    for col, bounds in conditions.date_ranges.items():
        if col not in df.columns:
            continue
        start, end = bounds
        converted = pd.to_datetime(df[col], errors="coerce")
        mask = (converted >= start) & (converted < end)
        filtered = filtered[mask]

    active = conditions.is_active()
    return FilterResult(df=filtered, active_count=active)


def apply_filters(
    df: pd.DataFrame,
    col_types: ColumnTypes,
    key_prefix: str = "",
) -> FilterResult:
    st.sidebar.subheader("🔍 数据筛选")
    filtered = df.copy()
    active = 0

    if not col_types.numeric and not col_types.categorical and not col_types.date:
        st.sidebar.caption("无可筛选的列")
        return FilterResult(filtered, active)

    with st.sidebar.expander("数值列筛选", expanded=False):
        for col in col_types.numeric:
            series = df[col].dropna()
            if len(series) == 0:
                continue
            lo = float(series.min())
            hi = float(series.max())
            if lo == hi:
                continue
            step = (hi - lo) / 100 if (hi - lo) > 100 else None
            sel = st.slider(
                f"{col}",
                min_value=lo,
                max_value=hi,
                value=(lo, hi),
                step=step,
                key=_make_key(key_prefix, "num", col),
            )
            if sel != (lo, hi):
                filtered = filtered[(filtered[col] >= sel[0]) & (filtered[col] <= sel[1])]
                active += 1

    with st.sidebar.expander("分类列筛选", expanded=False):
        for col in col_types.categorical:
            uniques = sorted(df[col].dropna().astype(str).unique().tolist())
            if len(uniques) == 0 or len(uniques) > CATEGORICAL_MAX_UNIQUE:
                continue
            selected = st.multiselect(
                f"{col}（空=全选）",
                options=uniques,
                default=[],
                key=_make_key(key_prefix, "cat", col),
            )
            if selected:
                filtered = filtered[filtered[col].astype(str).isin(selected)]
                active += 1

    with st.sidebar.expander("日期列筛选", expanded=False):
        for col in col_types.date:
            converted = pd.to_datetime(df[col], errors="coerce")
            min_dt = converted.min().date() if converted.notnull().any() else None
            max_dt = converted.max().date() if converted.notnull().any() else None
            if min_dt is None or max_dt is None:
                continue
            sel = st.date_input(
                f"{col}",
                value=(min_dt, max_dt),
                min_value=min_dt,
                max_value=max_dt,
                key=_make_key(key_prefix, "date", col),
            )
            if isinstance(sel, (list, tuple)) and len(sel) == 2:
                start, end = sel
                start_ts = pd.Timestamp(start)
                end_ts = pd.Timestamp(end) + pd.Timedelta(days=1)
                before = len(filtered)
                mask = (converted >= start_ts) & (converted < end_ts)
                filtered = filtered[mask.values]
                if len(filtered) != before:
                    active += 1

    reset_key = f"{key_prefix}reset_filter"
    if st.sidebar.button("重置筛选", key=reset_key):
        _clear_filter_keys(
            col_types.numeric, col_types.categorical, col_types.date, key_prefix
        )
        st.rerun()

    return FilterResult(filtered, active)
