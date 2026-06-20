from typing import List

import pandas as pd
import plotly.express as px
import streamlit as st

from .base import ChartStrategy


class BarChartStrategy(ChartStrategy):
    name = "bar"

    def section_title(self) -> str:
        return "📊 分类列柱状图"

    def can_apply(self, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> bool:
        return len(categorical_cols) > 0

    def generate(self, df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> List:
        figs = []
        n_cols = min(2, len(categorical_cols))
        cols = st.columns(n_cols)
        for idx, col_name in enumerate(categorical_cols):
            with cols[idx % n_cols]:
                vc = df[col_name].value_counts().head(self.config.bar_top_n)
                fig = px.bar(
                    x=vc.index, y=vc.values,
                    title=f"{col_name} 频次统计 (Top {self.config.bar_top_n})",
                    labels={"x": col_name, "y": "频次"},
                )
                fig.update_layout(
                    height=self.config.height,
                    margin=self.config.margin_dict(large_bottom=True),
                    xaxis_tickangle=self.config.xaxis_tickangle,
                )
                st.plotly_chart(fig, use_container_width=True)
                figs.append(fig)
        return figs
