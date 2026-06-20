from typing import List

import pandas as pd
import plotly.express as px
import streamlit as st

from .base import ChartStrategy


class HistogramStrategy(ChartStrategy):
    name = "histogram"

    def section_title(self) -> str:
        return "📊 数值列直方图"

    def can_apply(self, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> bool:
        return len(numeric_cols) > 0

    def generate(self, df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> List:
        figs = []
        n_cols = min(2, len(numeric_cols))
        cols = st.columns(n_cols)
        for idx, col_name in enumerate(numeric_cols):
            with cols[idx % n_cols]:
                series = df[col_name].dropna()
                fig = px.histogram(
                    series, x=col_name, title=f"{col_name} 分布",
                    nbins=self.config.hist_bins, opacity=self.config.opacity,
                )
                fig.update_layout(
                    height=self.config.height,
                    margin=self.config.margin_dict(),
                    showlegend=False,
                )
                fig.update_traces(marker_line_width=1, marker_line_color="white")
                st.plotly_chart(fig, use_container_width=True)
                figs.append(fig)
        return figs
