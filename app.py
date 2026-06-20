import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import itertools


st.set_page_config(page_title="数据分析看板", page_icon="📊", layout="wide")


def detect_column_types(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    categorical_cols = df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
    for col in categorical_cols[:]:
        if df[col].nunique() > df.shape[0] * 0.5 and df[col].nunique() > 20:
            categorical_cols.remove(col)
    return numeric_cols, categorical_cols


def display_data_preview(df):
    st.header("📋 数据预览")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("数据行数", f"{df.shape[0]:,}")
    with col2:
        st.metric("数据列数", df.shape[1])
    with col3:
        st.metric("缺失值总数", f"{df.isnull().sum().sum():,}")
    st.dataframe(df.head(20), use_container_width=True, hide_index=True)


def display_statistics(df, numeric_cols, categorical_cols):
    st.header("📈 统计摘要")
    if numeric_cols:
        st.subheader("数值列统计")
        stats_data = []
        for col in numeric_cols:
            series = df[col]
            stats_data.append({
                "列名": col,
                "均值": round(series.mean(), 4) if series.notnull().any() else None,
                "中位数": round(series.median(), 4) if series.notnull().any() else None,
                "标准差": round(series.std(), 4) if series.notnull().any() else None,
                "最小值": round(series.min(), 4) if series.notnull().any() else None,
                "最大值": round(series.max(), 4) if series.notnull().any() else None,
                "缺失值数量": int(series.isnull().sum()),
            })
        stats_df = pd.DataFrame(stats_data)
        st.dataframe(stats_df, use_container_width=True, hide_index=True)

    if categorical_cols:
        st.subheader("分类列统计")
        cat_stats_data = []
        for col in categorical_cols:
            series = df[col]
            value_counts = series.value_counts()
            most_freq = value_counts.index[0] if len(value_counts) > 0 else None
            most_freq_count = value_counts.iloc[0] if len(value_counts) > 0 else 0
            cat_stats_data.append({
                "列名": col,
                "唯一值个数": int(series.nunique()),
                "最高频类别": most_freq,
                "最高频次数": int(most_freq_count),
                "缺失值数量": int(series.isnull().sum()),
            })
        cat_stats_df = pd.DataFrame(cat_stats_data)
        st.dataframe(cat_stats_df, use_container_width=True, hide_index=True)


def display_histograms(df, numeric_cols):
    if not numeric_cols:
        return
    st.subheader("📊 数值列直方图")
    n_cols = min(2, len(numeric_cols))
    n_rows = (len(numeric_cols) + n_cols - 1) // n_cols
    cols = st.columns(n_cols)
    for idx, col_name in enumerate(numeric_cols):
        with cols[idx % n_cols]:
            series = df[col_name].dropna()
            fig = px.histogram(
                series,
                x=col_name,
                title=f"{col_name} 分布",
                nbins=30,
                opacity=0.75,
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
                showlegend=False,
            )
            fig.update_traces(marker_line_width=1, marker_line_color="white")
            st.plotly_chart(fig, use_container_width=True)


def display_bar_charts(df, categorical_cols):
    if not categorical_cols:
        return
    st.subheader("📊 分类列柱状图")
    n_cols = min(2, len(categorical_cols))
    cols = st.columns(n_cols)
    for idx, col_name in enumerate(categorical_cols):
        with cols[idx % n_cols]:
            value_counts = df[col_name].value_counts().head(15)
            fig = px.bar(
                x=value_counts.index,
                y=value_counts.values,
                title=f"{col_name} 频次统计 (Top 15)",
                labels={"x": col_name, "y": "频次"},
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=80),
                xaxis_tickangle=-45,
            )
            st.plotly_chart(fig, use_container_width=True)


def display_scatter_plots(df, numeric_cols):
    if len(numeric_cols) < 2:
        return
    st.subheader("📊 数值列散点图")
    pairs = list(itertools.combinations(numeric_cols, 2))
    max_pairs = min(len(pairs), 6)
    pairs = pairs[:max_pairs]
    n_cols = min(2, len(pairs))
    cols = st.columns(n_cols)
    for idx, (x_col, y_col) in enumerate(pairs):
        with cols[idx % n_cols]:
            clean_df = df[[x_col, y_col]].dropna()
            fig = px.scatter(
                clean_df,
                x=x_col,
                y=y_col,
                title=f"{x_col} vs {y_col}",
                opacity=0.6,
            )
            fig.update_layout(
                height=400,
                margin=dict(l=20, r=20, t=40, b=20),
            )
            st.plotly_chart(fig, use_container_width=True)


def display_charts(df, numeric_cols, categorical_cols):
    st.header("📊 自动生成图表")
    display_histograms(df, numeric_cols)
    display_bar_charts(df, categorical_cols)
    display_scatter_plots(df, numeric_cols)


def main():
    st.title("📊 数据分析看板")
    st.markdown("上传 CSV 文件，自动生成数据预览、统计摘要和可视化图表。")

    uploaded_file = st.file_uploader("请上传 CSV 文件", type=["csv"])

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
        except Exception as e:
            st.error(f"读取 CSV 文件失败: {e}")
            return

        numeric_cols, categorical_cols = detect_column_types(df)
        display_data_preview(df)
        display_statistics(df, numeric_cols, categorical_cols)
        display_charts(df, numeric_cols, categorical_cols)
    else:
        st.info("👆 请在上方上传一个 CSV 文件开始分析")
        with st.expander("查看示例"):
            st.markdown("""
            **支持的分析内容：**
            - 数据预览（前 20 行）
            - 数值列统计：均值、中位数、标准差、最大最小值、缺失值
            - 分类列统计：唯一值个数、最高频类别
            - 数值列直方图
            - 分类列柱状图
            - 数值列两两散点图
            """)


if __name__ == "__main__":
    main()
