from typing import List

import pandas as pd
import plotly.express as px
import streamlit as st

from .base import ChartStrategy


class LineChartStrategy(ChartStrategy):
    name = "line"

    def section_title(self) -> str:
        return "📈 日期列趋势图"

    def can_apply(self, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> bool:
        return len(date_cols) > 0 and len(numeric_cols) > 0

    def generate(self, df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> List:
        figs = []
        date_col = date_cols[0]
        value_cols = numeric_cols[: min(3, len(numeric_cols))]
        n_cols = min(2, len(value_cols))
        cols = st.columns(n_cols)

        temp_df = df.copy()
        temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors="coerce")
        temp_df = temp_df.dropna(subset=[date_col])

        for idx, val_col in enumerate(value_cols):
            with cols[idx % n_cols]:
                agg = temp_df.groupby(date_col)[val_col].mean().reset_index()
                fig = px.line(
                    agg, x=date_col, y=val_col,
                    title=f"{val_col} 随 {date_col} 变化趋势",
                    markers=True,
                )
                fig.update_layout(
                    height=self.config.height,
                    margin=self.config.margin_dict(large_bottom=True),
                )
                st.plotly_chart(fig, use_container_width=True)
                figs.append(fig)
        return figs
