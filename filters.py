import pandas as pd
import streamlit as st

from stats import ColumnTypes


CATEGORICAL_MAX_UNIQUE = 200


class FilterResult:
    def __init__(self, df: pd.DataFrame, active_count: int):
        self.df = df
        self.active_count = active_count


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
