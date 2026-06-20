import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import itertools
import io


st.set_page_config(page_title="数据分析看板", page_icon="📊", layout="wide")


COLORS = ["#636EFA", "#EF553B", "#00CC96", "#AB63FA", "#FFA15A", "#19D3F3"]


def detect_column_types(df):
    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    date_cols = []
    remaining_object_cols = []
    for col in df.select_dtypes(include=["object"]).columns:
        try:
            converted = pd.to_datetime(df[col], errors="coerce")
            if converted.notnull().sum() >= max(10, len(df) * 0.5):
                date_cols.append(col)
            else:
                remaining_object_cols.append(col)
        except Exception:
            remaining_object_cols.append(col)
    categorical_cols = remaining_object_cols + df.select_dtypes(include=["category", "bool"]).columns.tolist()
    for col in categorical_cols[:]:
        if df[col].nunique() > df.shape[0] * 0.5 and df[col].nunique() > 20:
            categorical_cols.remove(col)
    return numeric_cols, categorical_cols, date_cols


def build_filter_sidebar(df, numeric_cols, categorical_cols, date_cols, key_prefix=""):
    st.sidebar.subheader("🔍 数据筛选")
    filtered = df.copy()
    active_filters = 0

    if not numeric_cols and not categorical_cols and not date_cols:
        st.sidebar.caption("无可筛选的列")
        return filtered, active_filters

    with st.sidebar.expander("数值列筛选", expanded=False):
        for col in numeric_cols:
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
                key=f"{key_prefix}num_{col}",
            )
            if sel != (lo, hi):
                filtered = filtered[(filtered[col] >= sel[0]) & (filtered[col] <= sel[1])]
                active_filters += 1

    with st.sidebar.expander("分类列筛选", expanded=False):
        for col in categorical_cols:
            uniques = sorted(df[col].dropna().astype(str).unique().tolist())
            if len(uniques) == 0 or len(uniques) > 200:
                continue
            selected = st.multiselect(
                f"{col}（空=全选）",
                options=uniques,
                default=[],
                key=f"{key_prefix}cat_{col}",
            )
            if selected:
                filtered = filtered[filtered[col].astype(str).isin(selected)]
                active_filters += 1

    with st.sidebar.expander("日期列筛选", expanded=False):
        for col in date_cols:
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
                key=f"{key_prefix}date_{col}",
            )
            if isinstance(sel, (list, tuple)) and len(sel) == 2:
                start, end = sel
                start_ts = pd.Timestamp(start)
                end_ts = pd.Timestamp(end) + pd.Timedelta(days=1)
                before = len(filtered)
                mask = (converted >= start_ts) & (converted < end_ts)
                filtered = filtered[mask.values]
                if len(filtered) != before:
                    active_filters += 1

    reset = st.sidebar.button("重置筛选", key=f"{key_prefix}reset_filter")
    if reset:
        for col in numeric_cols:
            k = f"{key_prefix}num_{col}"
            if k in st.session_state:
                del st.session_state[k]
        for col in categorical_cols:
            k = f"{key_prefix}cat_{col}"
            if k in st.session_state:
                del st.session_state[k]
        for col in date_cols:
            k = f"{key_prefix}date_{col}"
            if k in st.session_state:
                del st.session_state[k]
        st.rerun()

    return filtered, active_filters


def build_export_sidebar(filtered_df, all_figs_dict, key_prefix=""):
    st.sidebar.markdown("---")
    st.sidebar.subheader("💾 导出")

    if filtered_df is not None and len(filtered_df) > 0:
        st.sidebar.caption(f"将导出 {len(filtered_df):,} 行数据")
        col_a, col_b = st.sidebar.columns(2)
        csv_buf = io.StringIO()
        filtered_df.to_csv(csv_buf, index=False, encoding="utf-8-sig")
        col_a.download_button(
            "导出 CSV",
            data=csv_buf.getvalue(),
            file_name="filtered_data.csv",
            mime="text/csv",
            key=f"{key_prefix}csv_export",
            use_container_width=True,
        )
        xlsx_buf = io.BytesIO()
        with pd.ExcelWriter(xlsx_buf, engine="openpyxl") as writer:
            filtered_df.to_excel(writer, index=False, sheet_name="Filtered")
        col_b.download_button(
            "导出 Excel",
            data=xlsx_buf.getvalue(),
            file_name="filtered_data.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key_prefix}xlsx_export",
            use_container_width=True,
        )

    if all_figs_dict:
        st.sidebar.caption("导出单个图表为 PNG")
        for name, fig in all_figs_dict.items():
            safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in name)[:80]
            try:
                png_bytes = fig.to_image(format="png", scale=2, width=900, height=500)
                st.sidebar.download_button(
                    f"PNG: {name[:28]}",
                    data=png_bytes,
                    file_name=f"{safe_name}.png",
                    mime="image/png",
                    key=f"{key_prefix}png_{safe_name}",
                    use_container_width=True,
                )
            except Exception:
                pass


def display_data_preview(df, title_prefix=""):
    if title_prefix:
        st.markdown(f"#### {title_prefix} 📋 数据预览")
    else:
        st.header("📋 数据预览")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("数据行数", f"{df.shape[0]:,}")
    with col2:
        st.metric("数据列数", df.shape[1])
    with col3:
        st.metric("缺失值总数", f"{df.isnull().sum().sum():,}")
    st.dataframe(df.head(20), use_container_width=True, hide_index=True)


def build_statistics_table(df, numeric_cols, categorical_cols):
    num_stats = []
    for col in numeric_cols:
        s = df[col]
        num_stats.append({
            "列名": col,
            "均值": round(s.mean(), 4) if s.notnull().any() else None,
            "中位数": round(s.median(), 4) if s.notnull().any() else None,
            "标准差": round(s.std(), 4) if s.notnull().any() else None,
            "最小值": round(s.min(), 4) if s.notnull().any() else None,
            "最大值": round(s.max(), 4) if s.notnull().any() else None,
            "缺失值": int(s.isnull().sum()),
        })
    cat_stats = []
    for col in categorical_cols:
        s = df[col]
        vc = s.value_counts()
        cat_stats.append({
            "列名": col,
            "唯一值": int(s.nunique()),
            "最高频": vc.index[0] if len(vc) else None,
            "最高频次数": int(vc.iloc[0]) if len(vc) else 0,
            "缺失值": int(s.isnull().sum()),
        })
    return pd.DataFrame(num_stats), pd.DataFrame(cat_stats)


def display_statistics(df, numeric_cols, categorical_cols, title_prefix=""):
    if title_prefix:
        st.markdown(f"#### {title_prefix} 📈 统计摘要")
    else:
        st.header("📈 统计摘要")
    num_df, cat_df = build_statistics_table(df, numeric_cols, categorical_cols)
    if numeric_cols:
        if title_prefix:
            st.caption("数值列统计")
        else:
            st.subheader("数值列统计")
        st.dataframe(num_df, use_container_width=True, hide_index=True)
    if categorical_cols:
        if title_prefix:
            st.caption("分类列统计")
        else:
            st.subheader("分类列统计")
        st.dataframe(cat_df, use_container_width=True, hide_index=True)
    return num_df, cat_df


def build_histograms(df, numeric_cols, figs_dict, figs_key_prefix=""):
    result = []
    if not numeric_cols:
        return result
    n_cols = min(2, len(numeric_cols))
    cols = st.columns(n_cols)
    for idx, col_name in enumerate(numeric_cols):
        with cols[idx % n_cols]:
            series = df[col_name].dropna()
            fig = px.histogram(
                series, x=col_name, title=f"{col_name} 分布",
                nbins=30, opacity=0.75,
            )
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20), showlegend=False)
            fig.update_traces(marker_line_width=1, marker_line_color="white")
            st.plotly_chart(fig, use_container_width=True)
            result.append(fig)
            if figs_dict is not None:
                figs_dict[f"{figs_key_prefix}hist_{col_name}"] = fig
    return result


def build_bar_charts(df, categorical_cols, figs_dict, figs_key_prefix=""):
    result = []
    if not categorical_cols:
        return result
    n_cols = min(2, len(categorical_cols))
    cols = st.columns(n_cols)
    for idx, col_name in enumerate(categorical_cols):
        with cols[idx % n_cols]:
            vc = df[col_name].value_counts().head(15)
            fig = px.bar(
                x=vc.index, y=vc.values,
                title=f"{col_name} 频次统计 (Top 15)",
                labels={"x": col_name, "y": "频次"},
            )
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=80), xaxis_tickangle=-45)
            st.plotly_chart(fig, use_container_width=True)
            result.append(fig)
            if figs_dict is not None:
                figs_dict[f"{figs_key_prefix}bar_{col_name}"] = fig
    return result


def build_scatter_plots(df, numeric_cols, figs_dict, figs_key_prefix=""):
    result = []
    if len(numeric_cols) < 2:
        return result
    pairs = list(itertools.combinations(numeric_cols, 2))
    max_pairs = min(len(pairs), 6)
    pairs = pairs[:max_pairs]
    n_cols = min(2, len(pairs))
    cols = st.columns(n_cols)
    for idx, (x_col, y_col) in enumerate(pairs):
        with cols[idx % n_cols]:
            clean = df[[x_col, y_col]].dropna()
            fig = px.scatter(
                clean, x=x_col, y=y_col,
                title=f"{x_col} vs {y_col}", opacity=0.6,
            )
            fig.update_layout(height=400, margin=dict(l=20, r=20, t=40, b=20))
            st.plotly_chart(fig, use_container_width=True)
            result.append(fig)
            if figs_dict is not None:
                figs_dict[f"{figs_key_prefix}scatter_{x_col}_{y_col}"] = fig
    return result


def display_charts(df, numeric_cols, categorical_cols, figs_dict=None, figs_key_prefix="", title_prefix=""):
    if title_prefix:
        st.markdown(f"#### {title_prefix} 📊 自动生成图表")
    else:
        st.header("📊 自动生成图表")
    if title_prefix:
        st.caption("数值列直方图")
    else:
        st.subheader("📊 数值列直方图")
    build_histograms(df, numeric_cols, figs_dict, figs_key_prefix)
    if title_prefix:
        st.caption("分类列柱状图")
    else:
        st.subheader("📊 分类列柱状图")
    build_bar_charts(df, categorical_cols, figs_dict, figs_key_prefix)
    if title_prefix:
        st.caption("数值列散点图")
    else:
        st.subheader("📊 数值列散点图")
    build_scatter_plots(df, numeric_cols, figs_dict, figs_key_prefix)


def build_compare_statistics(df1, df2, num_cols_1, cat_cols_1, num_cols_2, cat_cols_2, label1, label2):
    common_num = sorted(set(num_cols_1) & set(num_cols_2))
    if common_num:
        st.subheader("数值列对比（同名列）")
        rows = []
        for col in common_num:
            s1, s2 = df1[col], df2[col]
            rows.append({
                "列名": col,
                f"均值 [{label1}]": round(s1.mean(), 4) if s1.notnull().any() else None,
                f"均值 [{label2}]": round(s2.mean(), 4) if s2.notnull().any() else None,
                f"中位数 [{label1}]": round(s1.median(), 4) if s1.notnull().any() else None,
                f"中位数 [{label2}]": round(s2.median(), 4) if s2.notnull().any() else None,
                f"标准差 [{label1}]": round(s1.std(), 4) if s1.notnull().any() else None,
                f"标准差 [{label2}]": round(s2.std(), 4) if s2.notnull().any() else None,
                f"最小 [{label1}]": round(s1.min(), 4) if s1.notnull().any() else None,
                f"最小 [{label2}]": round(s2.min(), 4) if s2.notnull().any() else None,
                f"最大 [{label1}]": round(s1.max(), 4) if s1.notnull().any() else None,
                f"最大 [{label2}]": round(s2.max(), 4) if s2.notnull().any() else None,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    common_cat = sorted(set(cat_cols_1) & set(cat_cols_2))
    if common_cat:
        st.subheader("分类列对比（同名列）")
        rows = []
        for col in common_cat:
            s1, s2 = df1[col], df2[col]
            vc1, vc2 = s1.value_counts(), s2.value_counts()
            rows.append({
                "列名": col,
                f"唯一值 [{label1}]": int(s1.nunique()),
                f"唯一值 [{label2}]": int(s2.nunique()),
                f"最高频 [{label1}]": vc1.index[0] if len(vc1) else None,
                f"最高频 [{label2}]": vc2.index[0] if len(vc2) else None,
            })
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)


def build_compare_histograms(df1, df2, numeric_cols_1, numeric_cols_2, label1, label2, figs_dict):
    common = sorted(set(numeric_cols_1) & set(numeric_cols_2))
    if not common:
        return
    st.subheader("叠加直方图（同名列）")
    n_cols = min(2, len(common))
    cols = st.columns(n_cols)
    for idx, col in enumerate(common):
        with cols[idx % n_cols]:
            fig = go.Figure()
            fig.add_trace(go.Histogram(
                x=df1[col].dropna(), name=label1, nbinsx=30,
                marker_color=COLORS[0], opacity=0.65,
            ))
            fig.add_trace(go.Histogram(
                x=df2[col].dropna(), name=label2, nbinsx=30,
                marker_color=COLORS[1], opacity=0.65,
            ))
            fig.update_layout(
                barmode="overlay", title=f"{col} 分布对比",
                height=400, margin=dict(l=20, r=20, t=40, b=20),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)
            figs_dict[f"cmp_hist_{col}"] = fig


def build_compare_bars(df1, df2, cat_cols_1, cat_cols_2, label1, label2, figs_dict):
    common = sorted(set(cat_cols_1) & set(cat_cols_2))
    if not common:
        return
    st.subheader("叠加柱状图（同名列，Top 10）")
    n_cols = min(2, len(common))
    cols = st.columns(n_cols)
    for idx, col in enumerate(common):
        with cols[idx % n_cols]:
            vc1 = df1[col].value_counts().head(10)
            vc2 = df2[col].value_counts().head(10)
            union = sorted(set(vc1.index) | set(vc2.index), key=lambda x: -(vc1.get(x, 0) + vc2.get(x, 0)))
            union = union[:10]
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[str(u) for u in union],
                y=[vc1.get(u, 0) for u in union],
                name=label1, marker_color=COLORS[0],
            ))
            fig.add_trace(go.Bar(
                x=[str(u) for u in union],
                y=[vc2.get(u, 0) for u in union],
                name=label2, marker_color=COLORS[1],
            ))
            fig.update_layout(
                barmode="group", title=f"{col} 频次对比",
                height=400, margin=dict(l=20, r=20, t=40, b=80),
                xaxis_tickangle=-45,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)
            figs_dict[f"cmp_bar_{col}"] = fig


def build_compare_scatters(df1, df2, num_cols_1, num_cols_2, label1, label2, figs_dict):
    common = sorted(set(num_cols_1) & set(num_cols_2))
    if len(common) < 2:
        return
    pairs = list(itertools.combinations(common, 2))[:6]
    if not pairs:
        return
    st.subheader("叠加散点图（同名列）")
    n_cols = min(2, len(pairs))
    cols = st.columns(n_cols)
    for idx, (x_col, y_col) in enumerate(pairs):
        with cols[idx % n_cols]:
            fig = go.Figure()
            clean1 = df1[[x_col, y_col]].dropna()
            clean2 = df2[[x_col, y_col]].dropna()
            fig.add_trace(go.Scatter(
                x=clean1[x_col], y=clean1[y_col], mode="markers",
                name=label1, marker=dict(color=COLORS[0], opacity=0.5),
            ))
            fig.add_trace(go.Scatter(
                x=clean2[x_col], y=clean2[y_col], mode="markers",
                name=label2, marker=dict(color=COLORS[1], opacity=0.5),
            ))
            fig.update_layout(
                title=f"{x_col} vs {y_col}",
                height=400, margin=dict(l=20, r=20, t=40, b=20),
                xaxis_title=x_col, yaxis_title=y_col,
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
            )
            st.plotly_chart(fig, use_container_width=True)
            figs_dict[f"cmp_scatter_{x_col}_{y_col}"] = fig


def display_compare_charts(df1, df2, num1, cat1, num2, cat2, label1, label2, figs_dict):
    st.header("🆚 对比图表")
    build_compare_histograms(df1, df2, num1, num2, label1, label2, figs_dict)
    build_compare_bars(df1, df2, cat1, cat2, label1, label2, figs_dict)
    build_compare_scatters(df1, df2, num1, num2, label1, label2, figs_dict)


def single_file_mode():
    st.title("📊 数据分析看板")
    uploaded_file = st.file_uploader("请上传 CSV 文件", type=["csv"])
    if uploaded_file is None:
        st.info("👆 请上传 CSV 文件开始分析")
        with st.expander("功能说明"):
            st.markdown("""
            - **筛选**: 左侧边栏按数值范围、分类多选、日期范围筛选
            - **导出**: 侧边栏可导出 CSV / Excel，及各图表 PNG
            - **统计**: 自动显示数值列和分类列统计摘要
            - **图表**: 数值直方图、分类柱状图、散点图（相关性）
            """)
        return

    try:
        df = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"读取 CSV 失败: {e}")
        return

    numeric_cols, categorical_cols, date_cols = detect_column_types(df)
    filtered, active = build_filter_sidebar(df, numeric_cols, categorical_cols, date_cols, key_prefix="sf_")

    if active > 0:
        st.info(f"🔍 已应用 {active} 个筛选条件: {len(df):,} → {len(filtered):,} 行")
    if len(filtered) == 0:
        st.warning("筛选后无数据，请调整筛选条件")
        return

    figs_dict = {}
    display_data_preview(filtered)
    display_statistics(filtered, numeric_cols, categorical_cols)
    display_charts(filtered, numeric_cols, categorical_cols, figs_dict=figs_dict, figs_key_prefix="sf_")
    build_export_sidebar(filtered, figs_dict, key_prefix="sf_")


def compare_mode():
    st.title("🆚 双文件对比模式")
    cola, colb = st.columns(2)
    with cola:
        file1 = st.file_uploader("上传文件 1 (CSV)", type=["csv"], key="cmp_f1")
    with colb:
        file2 = st.file_uploader("上传文件 2 (CSV)", type=["csv"], key="cmp_f2")

    label1 = st.sidebar.text_input("文件 1 标签", value="文件A")
    label2 = st.sidebar.text_input("文件 2 标签", value="文件B")

    if not file1 or not file2:
        st.info("请上传两个 CSV 文件开始对比")
        return

    try:
        df1_raw = pd.read_csv(file1)
        df2_raw = pd.read_csv(file2)
    except Exception as e:
        st.error(f"读取失败: {e}")
        return

    tab_mode = st.sidebar.radio("展示方式", ["并排", "仅对比"], index=0)

    n1, c1, d1 = detect_column_types(df1_raw)
    n2, c2, d2 = detect_column_types(df2_raw)

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"🎯 {label1} 筛选")
    df1, a1 = build_filter_sidebar(df1_raw, n1, c1, d1, key_prefix="cmp1_")
    if a1 > 0:
        st.sidebar.caption(f"{label1}: {len(df1_raw):,} → {len(df1):,} 行")

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"🎯 {label2} 筛选")
    df2, a2 = build_filter_sidebar(df2_raw, n2, c2, d2, key_prefix="cmp2_")
    if a2 > 0:
        st.sidebar.caption(f"{label2}: {len(df2_raw):,} → {len(df2):,} 行")

    if len(df1) == 0 or len(df2) == 0:
        st.warning("筛选后至少一个文件为空，请调整条件")
        return

    figs_dict = {}
    n1, c1, d1 = detect_column_types(df1)
    n2, c2, d2 = detect_column_types(df2)

    if tab_mode == "并排":
        st.header(f"📋 数据预览对比")
        p1, p2 = st.columns(2)
        with p1:
            st.markdown(f"**{label1}** ({len(df1):,} 行 × {len(df1.columns)} 列)")
            st.dataframe(df1.head(15), use_container_width=True, hide_index=True)
        with p2:
            st.markdown(f"**{label2}** ({len(df2):,} 行 × {len(df2.columns)} 列)")
            st.dataframe(df2.head(15), use_container_width=True, hide_index=True)

        st.header(f"📈 统计摘要对比")
        s1, s2 = st.columns(2)
        with s1:
            display_statistics(df1, n1, c1, title_prefix=label1)
        with s2:
            display_statistics(df2, n2, c2, title_prefix=label2)

        st.header(f"📊 各自图表")
        g1, g2 = st.columns(2)
        with g1:
            display_charts(df1, n1, c1, figs_dict=figs_dict, figs_key_prefix="c1_", title_prefix=label1)
        with g2:
            display_charts(df2, n2, c2, figs_dict=figs_dict, figs_key_prefix="c2_", title_prefix=label2)

    st.header("📊 同名列统计对比")
    build_compare_statistics(df1, df2, n1, c1, n2, c2, label1, label2)
    display_compare_charts(df1, df2, n1, c1, n2, c2, label1, label2, figs_dict)

    st.sidebar.markdown("---")
    build_export_sidebar(df1, figs_dict, key_prefix="c1_exp_")
    st.sidebar.caption("—— 以下为文件 2 数据导出 ——")
    build_export_sidebar(df2, {}, key_prefix="c2_exp_")


def main():
    mode = st.sidebar.radio("工作模式", ["单文件分析", "双文件对比"], index=0)
    if mode == "单文件分析":
        single_file_mode()
    else:
        compare_mode()


if __name__ == "__main__":
    main()
