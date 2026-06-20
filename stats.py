import pandas as pd
import numpy as np


LOW_CARDINALITY_THRESHOLD = 15
LOW_CARDINALITY_RATIO = 0.2
HIGH_CARDINALITY_RATIO = 0.5
HIGH_CARDINALITY_MIN = 20
DATE_DETECT_THRESHOLD_COUNT = 10
DATE_DETECT_THRESHOLD_RATIO = 0.5


class ColumnTypes:
    def __init__(self, numeric, categorical, date):
        self.numeric = numeric
        self.categorical = categorical
        self.date = date

    def all_columns(self):
        return self.numeric + self.categorical + self.date


def detect_column_types(df: pd.DataFrame) -> ColumnTypes:
    total_rows = len(df)
    numeric_cols_raw = df.select_dtypes(include=[np.number]).columns.tolist()

    numeric_cols = []
    low_cardinality_numeric = []
    for col in numeric_cols_raw:
        non_null = df[col].dropna()
        nuniq = non_null.nunique()
        if nuniq < LOW_CARDINALITY_THRESHOLD or (
            total_rows > 0 and nuniq < total_rows * LOW_CARDINALITY_RATIO
        ):
            low_cardinality_numeric.append(col)
        else:
            numeric_cols.append(col)

    date_cols = []
    remaining_object_cols = []
    for col in df.select_dtypes(include=["object"]).columns:
        try:
            converted = pd.to_datetime(df[col], errors="coerce")
            threshold = max(DATE_DETECT_THRESHOLD_COUNT, len(df) * DATE_DETECT_THRESHOLD_RATIO)
            if converted.notnull().sum() >= threshold:
                date_cols.append(col)
            else:
                remaining_object_cols.append(col)
        except Exception:
            remaining_object_cols.append(col)

    categorical_cols = (
        remaining_object_cols
        + df.select_dtypes(include=["category", "bool"]).columns.tolist()
        + low_cardinality_numeric
    )

    for col in categorical_cols[:]:
        nunique = df[col].nunique(dropna=True)
        if (
            total_rows > 0
            and nunique > total_rows * HIGH_CARDINALITY_RATIO
            and nunique > HIGH_CARDINALITY_MIN
        ):
            categorical_cols.remove(col)

    categorical_cols = list(dict.fromkeys(categorical_cols))
    return ColumnTypes(numeric=numeric_cols, categorical=categorical_cols, date=date_cols)


def _safe_numeric_stats(series: pd.Series) -> dict:
    s = series.dropna()
    if len(s) == 0:
        return {"均值": None, "中位数": None, "标准差": None, "最小值": None, "最大值": None}
    try:
        return {
            "均值": round(float(s.mean()), 4),
            "中位数": round(float(s.median()), 4),
            "标准差": round(float(s.std()), 4),
            "最小值": round(float(s.min()), 4),
            "最大值": round(float(s.max()), 4),
        }
    except (ValueError, TypeError, ZeroDivisionError):
        return {"均值": None, "中位数": None, "标准差": None, "最小值": None, "最大值": None}


def _safe_categorical_stats(series: pd.Series) -> dict:
    try:
        vc = series.value_counts(dropna=True)
    except Exception:
        vc = pd.Series(dtype=int)
    return {
        "唯一值": int(series.nunique(dropna=True)),
        "最高频": vc.index[0] if len(vc) else None,
        "最高频次数": int(vc.iloc[0]) if len(vc) else 0,
    }


def build_statistics_table(df: pd.DataFrame, col_types: ColumnTypes) -> tuple[pd.DataFrame, pd.DataFrame]:
    num_stats = []
    for col in col_types.numeric:
        row = {"列名": col}
        row.update(_safe_numeric_stats(df[col]))
        row["缺失值"] = int(df[col].isnull().sum())
        num_stats.append(row)

    cat_stats = []
    for col in col_types.categorical:
        row = {"列名": col}
        row.update(_safe_categorical_stats(df[col]))
        row["缺失值"] = int(df[col].isnull().sum())
        cat_stats.append(row)

    return pd.DataFrame(num_stats), pd.DataFrame(cat_stats)


def build_compare_statistics(
    df1: pd.DataFrame,
    df2: pd.DataFrame,
    col_types1: ColumnTypes,
    col_types2: ColumnTypes,
    label1: str,
    label2: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    common_num = sorted(set(col_types1.numeric) & set(col_types2.numeric))
    num_rows = []
    for col in common_num:
        s1_stats = _safe_numeric_stats(df1[col])
        s2_stats = _safe_numeric_stats(df2[col])
        row = {"列名": col}
        for key in s1_stats:
            row[f"{key} [{label1}]"] = s1_stats[key]
            row[f"{key} [{label2}]"] = s2_stats[key]
        num_rows.append(row)

    common_cat = sorted(set(col_types1.categorical) & set(col_types2.categorical))
    cat_rows = []
    for col in common_cat:
        s1_stats = _safe_categorical_stats(df1[col])
        s2_stats = _safe_categorical_stats(df2[col])
        row = {"列名": col}
        for key in ("唯一值", "最高频"):
            row[f"{key} [{label1}]"] = s1_stats[key]
            row[f"{key} [{label2}]"] = s2_stats[key]
        cat_rows.append(row)

    return pd.DataFrame(num_rows), pd.DataFrame(cat_rows)


def missing_summary(df: pd.DataFrame) -> dict:
    total_missing = int(df.isnull().sum().sum())
    return {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "missing_total": total_missing,
    }
