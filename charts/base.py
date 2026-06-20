from abc import ABC, abstractmethod
from typing import List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from .config import ChartConfig, default_config


class ChartStrategy(ABC):
    name: str = "base"

    def __init__(self, config: Optional[ChartConfig] = None):
        self.config = config or default_config()

    @abstractmethod
    def can_apply(self, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> bool:
        ...

    @abstractmethod
    def generate(self, df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str]) -> List[go.Figure]:
        ...

    @abstractmethod
    def section_title(self) -> str:
        ...

    def render(self, df: pd.DataFrame, numeric_cols: List[str], categorical_cols: List[str], date_cols: List[str], figs_dict: Optional[dict] = None, key_prefix: str = "", title_prefix: str = "") -> List[go.Figure]:
        if not self.can_apply(numeric_cols, categorical_cols, date_cols):
            return []
        if title_prefix:
            st.caption(self.section_title())
        else:
            st.subheader(self.section_title())
        figs = self.generate(df, numeric_cols, categorical_cols, date_cols)
        if figs_dict is not None:
            for i, fig in enumerate(figs):
                figs_dict[f"{key_prefix}{self.name}_{i}"] = fig
        return figs


class ChartGenerator:
    def __init__(self, strategies: Optional[List[ChartStrategy]] = None, config: Optional[ChartConfig] = None):
        self.config = config or default_config()
        self.strategies: List[ChartStrategy] = strategies or []

    def add_strategy(self, strategy: ChartStrategy):
        self.strategies.append(strategy)

    def render_all(
        self,
        df: pd.DataFrame,
        numeric_cols: List[str],
        categorical_cols: List[str],
        date_cols: List[str],
        figs_dict: Optional[dict] = None,
        key_prefix: str = "",
        title_prefix: str = "",
    ) -> List[go.Figure]:
        all_figs = []
        for strategy in self.strategies:
            figs = strategy.render(
                df, numeric_cols, categorical_cols, date_cols,
                figs_dict=figs_dict, key_prefix=key_prefix, title_prefix=title_prefix,
            )
            all_figs.extend(figs)
        return all_figs
