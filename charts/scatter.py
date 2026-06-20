import itertools
from typing import List

import pandas as pd
import plotly.express as px
import streamlit as st

from .base import ChartStrategy


class ScatterStrategy(ChartStrategy):
    name = "scatter"

    def section_title(self) -> str:
        return "📊 数值列散点图"

    def can_apply(self, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> bool:
        return len(numeric_cols) >= 2

    def generate(self, df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> List:
        figs = []
        pairs = list(itertools.combinations(numeric_cols, 2))
        max_pairs = min(len(pairs), self.config.scatter_max_pairs)
        pairs = pairs[:max_pairs]

        n_cols = min(2, len(pairs))
        cols = st.columns(n_cols)
        for idx, (x_col, y_col) in enumerate(pairs):
            with cols[idx % n_cols]:
                clean = df[[x_col, y_col]].dropna()
                fig = px.scatter(
                    clean, x=x_col, y=y_col,
                    title=f"{x_col} vs {y_col}",
                    opacity=self.config.scatter_opacity,
                )
                fig.update_layout(
                    height=self.config.height,
                    margin=self.config.margin_dict(),
                )
                st.plotly_chart(fig, use_container_width=True)
                figs.append(fig)
        return figs
