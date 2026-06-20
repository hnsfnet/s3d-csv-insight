import itertools
from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .base import ChartStrategy
from .config import ChartConfig, default_config


class CompareChartStrategy(ChartStrategy):
    name = "compare_base"

    def __init__(self, config: Optional[ChartConfig] = None, label1: str = "A", label2: str = "B"):
        super().__init__(config)
        self.label1 = label1
        self.label2 = label2

    def can_apply(self, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> bool:
        return False

    def generate(self, df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> List:
        return []

    def can_apply_compare(self, col_types1, col_types2) -> bool:
        raise NotImplementedError

    def generate_compare(self, df1, df2, col_types1, col_types2) -> List[go.Figure]:
        raise NotImplementedError

    def render_compare(self, df1, df2, col_types1, col_types2, figs_dict: Optional[dict] = None, key_prefix: str = "") -> List[go.Figure]:
        if not self.can_apply_compare(col_types1, col_types2):
            return []
        st.subheader(self.section_title())
        figs = self.generate_compare(df1, df2, col_types1, col_types2)
        if figs_dict is not None:
            for i, fig in enumerate(figs):
                figs_dict[f"{key_prefix}{self.name}_{i}"] = fig
        return figs


class CompareHistogramStrategy(CompareChartStrategy):
    name = "cmp_hist"

    def section_title(self) -> str:
        return "叠加直方图（同名列）"

    def can_apply_compare(self, col_types1, col_types2) -> bool:
        common = set(col_types1.numeric) & set(col_types2.numeric)
        return len(common) > 0

    def generate_compare(self, df1, df2, col_types1, col_types2) -> List[go.Figure]:
        common = sorted(set(col_types1.numeric) & set(col_types2.numeric))
        figs = []
        n_cols = min(2, len(common))
        cols = st.columns(n_cols)
        for idx, col in enumerate(common):
            with cols[idx % n_cols]:
                fig = go.Figure()
                fig.add_trace(go.Histogram(
                    x=df1[col].dropna(), name=self.label1, nbinsx=self.config.hist_bins,
                    marker_color=self.config.colors[0], opacity=0.65,
                ))
                fig.add_trace(go.Histogram(
                    x=df2[col].dropna(), name=self.label2, nbinsx=self.config.hist_bins,
                    marker_color=self.config.colors[1], opacity=0.65,
                ))
                fig.update_layout(
                    barmode="overlay", title=f"{col} 分布对比",
                    height=self.config.height,
                    margin=self.config.margin_dict(),
                    legend=self.config.legend_dict(),
                )
                st.plotly_chart(fig, use_container_width=True)
                figs.append(fig)
        return figs


class CompareBarStrategy(CompareChartStrategy):
    name = "cmp_bar"

    def section_title(self) -> str:
        return f"叠加柱状图（同名列，Top {self.config.bar_compare_top_n}）"

    def can_apply_compare(self, col_types1, col_types2) -> bool:
        common = set(col_types1.categorical) & set(col_types2.categorical)
        return len(common) > 0

    def generate_compare(self, df1, df2, col_types1, col_types2) -> List[go.Figure]:
        common = sorted(set(col_types1.categorical) & set(col_types2.categorical))
        figs = []
        n_cols = min(2, len(common))
        cols = st.columns(n_cols)
        top_n = self.config.bar_compare_top_n
        for idx, col in enumerate(common):
            with cols[idx % n_cols]:
                vc1 = df1[col].value_counts().head(top_n)
                vc2 = df2[col].value_counts().head(top_n)
                union = sorted(
                    set(vc1.index) | set(vc2.index),
                    key=lambda x: -(vc1.get(x, 0) + vc2.get(x, 0)),
                )[:top_n]
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=[str(u) for u in union],
                    y=[vc1.get(u, 0) for u in union],
                    name=self.label1, marker_color=self.config.colors[0],
                ))
                fig.add_trace(go.Bar(
                    x=[str(u) for u in union],
                    y=[vc2.get(u, 0) for u in union],
                    name=self.label2, marker_color=self.config.colors[1],
                ))
                fig.update_layout(
                    barmode="group", title=f"{col} 频次对比",
                    height=self.config.height,
                    margin=self.config.margin_dict(large_bottom=True),
                    xaxis_tickangle=self.config.xaxis_tickangle,
                    legend=self.config.legend_dict(),
                )
                st.plotly_chart(fig, use_container_width=True)
                figs.append(fig)
        return figs


class CompareScatterStrategy(CompareChartStrategy):
    name = "cmp_scatter"

    def section_title(self) -> str:
        return "叠加散点图（同名列）"

    def can_apply_compare(self, col_types1, col_types2) -> bool:
        common = set(col_types1.numeric) & set(col_types2.numeric)
        return len(common) >= 2

    def generate_compare(self, df1, df2, col_types1, col_types2) -> List[go.Figure]:
        common = sorted(set(col_types1.numeric) & set(col_types2.numeric))
        pairs = list(itertools.combinations(common, 2))[: self.config.scatter_max_pairs]
        if not pairs:
            return []
        figs = []
        n_cols = min(2, len(pairs))
        cols = st.columns(n_cols)
        for idx, (x_col, y_col) in enumerate(pairs):
            with cols[idx % n_cols]:
                fig = go.Figure()
                clean1 = df1[[x_col, y_col]].dropna()
                clean2 = df2[[x_col, y_col]].dropna()
                fig.add_trace(go.Scatter(
                    x=clean1[x_col], y=clean1[y_col], mode="markers",
                    name=self.label1,
                    marker=dict(color=self.config.colors[0], opacity=self.config.scatter_opacity),
                ))
                fig.add_trace(go.Scatter(
                    x=clean2[x_col], y=clean2[y_col], mode="markers",
                    name=self.label2,
                    marker=dict(color=self.config.colors[1], opacity=self.config.scatter_opacity),
                ))
                fig.update_layout(
                    title=f"{x_col} vs {y_col}",
                    height=self.config.height,
                    margin=self.config.margin_dict(),
                    xaxis_title=x_col, yaxis_title=y_col,
                    legend=self.config.legend_dict(),
                )
                st.plotly_chart(fig, use_container_width=True)
                figs.append(fig)
        return figs


class CompareChartGenerator:
    def __init__(self, strategies: Optional[List[CompareChartStrategy]] = None, config: Optional[ChartConfig] = None):
        self.config = config or default_config()
        self.strategies: List[CompareChartStrategy] = strategies or []

    def add_strategy(self, strategy: CompareChartStrategy):
        self.strategies.append(strategy)

    def render_all(self, df1, df2, col_types1, col_types2, figs_dict=None, key_prefix="") -> List[go.Figure]:
        all_figs = []
        for strategy in self.strategies:
            figs = strategy.render_compare(
                df1, df2, col_types1, col_types2,
                figs_dict=figs_dict, key_prefix=key_prefix,
            )
            all_figs.extend(figs)
        return all_figs
