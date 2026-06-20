import io
import pandas as pd
import streamlit as st

from data_loader import load_csv_file, CSVLoadError
from stats import detect_column_types, build_statistics_table, build_compare_statistics, missing_summary
from filters import apply_filters
from charts import (
    ChartGenerator,
    HistogramStrategy,
    BarChartStrategy,
    ScatterStrategy,
    LineChartStrategy,
    CompareChartGenerator,
    CompareHistogramStrategy,
    CompareBarStrategy,
    CompareScatterStrategy,
    default_config,
)


st.set_page_config(page_title="数据分析看板", page_icon="📊", layout="wide")


CFG = default_config()


def _build_chart_generator() -> ChartGenerator:
    gen = ChartGenerator(config=CFG)
    gen.add_strategy(HistogramStrategy(config=CFG))
    gen.add_strategy(BarChartStrategy(config=CFG))
    gen.add_strategy(ScatterStrategy(config=CFG))
    gen.add_strategy(LineChartStrategy(config=CFG))
    return gen


def _build_compare_generator(label1: str, label2: str) -> CompareChartGenerator:
    gen = CompareChartGenerator(config=CFG)
    gen.add_strategy(CompareHistogramStrategy(config=CFG, label1=label1, label2=label2))
    gen.add_strategy(CompareBarStrategy(config=CFG, label1=label1, label2=label2))
    gen.add_strategy(CompareScatterStrategy(config=CFG, label1=label1, label2=label2))
    return gen


def display_data_preview(df, title_prefix=""):
    if title_prefix:
        st.markdown(f"#### {title_prefix} 📋 数据预览")
    else:
        st.header("📋 数据预览")
    info = missing_summary(df)
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("数据行数", f"{info['rows']:,}")
    with c2:
        st.metric("数据列数", info["columns"])
    with c3:
        st.metric("缺失值总数", f"{info['missing_total']:,}")
    st.dataframe(df.head(20), use_container_width=True, hide_index=True)


def display_statistics(df, col_types, title_prefix=""):
    if title_prefix:
        st.markdown(f"#### {title_prefix} 📈 统计摘要")
    else:
        st.header("📈 统计摘要")
    num_df, cat_df = build_statistics_table(df, col_types)
    if len(num_df) > 0:
        if title_prefix:
            st.caption("数值列统计")
        else:
            st.subheader("数值列统计")
        st.dataframe(num_df, use_container_width=True, hide_index=True)
    if len(cat_df) > 0:
        if title_prefix:
            st.caption("分类列统计")
        else:
            st.subheader("分类列统计")
        st.dataframe(cat_df, use_container_width=True, hide_index=True)


def display_charts_section(df, col_types, figs_dict=None, key_prefix="", title_prefix=""):
    if title_prefix:
        st.markdown(f"#### {title_prefix} 📊 自动生成图表")
    else:
        st.header("📊 自动生成图表")
    gen = _build_chart_generator()
    gen.render_all(
        df, col_types.numeric, col_types.categorical, col_types.date,
        figs_dict=figs_dict, key_prefix=key_prefix, title_prefix=title_prefix,
    )


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
                png_bytes = fig.to_image(
                    format="png", scale=CFG.png_scale,
                    width=CFG.png_width, height=CFG.png_height,
                )
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
            - **图表**: 数值直方图、分类柱状图、散点图、日期趋势图
            """)
        return

    try:
        df, used_enc = load_csv_file(uploaded_file)
    except CSVLoadError as e:
        st.error(f"读取 CSV 失败:\n{e}")
        return
    except Exception as e:
        st.error(f"读取 CSV 失败: {e}")
        return

    st.success(f"✅ 解析成功，使用编码: {used_enc.upper()}")
    col_types = detect_column_types(df)
    filter_result = apply_filters(df, col_types, key_prefix="sf_")
    filtered = filter_result.df
    active = filter_result.active_count

    if active > 0:
        st.info(f"🔍 已应用 {active} 个筛选条件: {len(df):,} → {len(filtered):,} 行")
    if len(filtered) == 0:
        st.warning("筛选后无数据，请调整筛选条件")
        return

    figs_dict = {}
    display_data_preview(filtered)
    display_statistics(filtered, col_types)
    display_charts_section(filtered, col_types, figs_dict=figs_dict, key_prefix="sf_")
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
        df1_raw, enc1 = load_csv_file(file1)
        df2_raw, enc2 = load_csv_file(file2)
    except CSVLoadError as e:
        st.error(f"读取失败:\n{e}")
        return
    except Exception as e:
        st.error(f"读取失败: {e}")
        return

    st.success(f"✅ {label1} 使用编码: {enc1.upper()}　|　{label2} 使用编码: {enc2.upper()}")

    tab_mode = st.sidebar.radio("展示方式", ["并排", "仅对比"], index=0)

    col_types1_raw = detect_column_types(df1_raw)
    col_types2_raw = detect_column_types(df2_raw)

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"🎯 {label1} 筛选")
    fr1 = apply_filters(df1_raw, col_types1_raw, key_prefix="cmp1_")
    df1 = fr1.df
    if fr1.active_count > 0:
        st.sidebar.caption(f"{label1}: {len(df1_raw):,} → {len(df1):,} 行")

    st.sidebar.markdown("---")
    st.sidebar.subheader(f"🎯 {label2} 筛选")
    fr2 = apply_filters(df2_raw, col_types2_raw, key_prefix="cmp2_")
    df2 = fr2.df
    if fr2.active_count > 0:
        st.sidebar.caption(f"{label2}: {len(df2_raw):,} → {len(df2):,} 行")

    if len(df1) == 0 or len(df2) == 0:
        st.warning("筛选后至少一个文件为空，请调整条件")
        return

    col_types1 = detect_column_types(df1)
    col_types2 = detect_column_types(df2)

    figs_dict = {}

    if tab_mode == "并排":
        st.header("📋 数据预览对比")
        p1, p2 = st.columns(2)
        with p1:
            st.markdown(f"**{label1}** ({len(df1):,} 行 × {len(df1.columns)} 列)")
            st.dataframe(df1.head(15), use_container_width=True, hide_index=True)
        with p2:
            st.markdown(f"**{label2}** ({len(df2):,} 行 × {len(df2.columns)} 列)")
            st.dataframe(df2.head(15), use_container_width=True, hide_index=True)

        st.header("📈 统计摘要对比")
        s1, s2 = st.columns(2)
        with s1:
            display_statistics(df1, col_types1, title_prefix=label1)
        with s2:
            display_statistics(df2, col_types2, title_prefix=label2)

        st.header("📊 各自图表")
        g1, g2 = st.columns(2)
        with g1:
            display_charts_section(df1, col_types1, figs_dict=figs_dict, key_prefix="c1_", title_prefix=label1)
        with g2:
            display_charts_section(df2, col_types2, figs_dict=figs_dict, key_prefix="c2_", title_prefix=label2)

    st.header("📊 同名列统计对比")
    num_cmp_df, cat_cmp_df = build_compare_statistics(
        df1, df2, col_types1, col_types2, label1, label2,
    )
    if len(num_cmp_df) > 0:
        st.subheader("数值列对比（同名列）")
        st.dataframe(num_cmp_df, use_container_width=True, hide_index=True)
    if len(cat_cmp_df) > 0:
        st.subheader("分类列对比（同名列）")
        st.dataframe(cat_cmp_df, use_container_width=True, hide_index=True)

    st.header("🆚 对比图表")
    cmp_gen = _build_compare_generator(label1, label2)
    cmp_gen.render_all(df1, df2, col_types1, col_types2, figs_dict=figs_dict, key_prefix="cmp_")

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
