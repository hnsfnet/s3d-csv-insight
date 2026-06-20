from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChartConfig:
    colors: List[str] = field(
        default_factory=lambda: [
            "#636EFA",
            "#EF553B",
            "#00CC96",
            "#AB63FA",
            "#FFA15A",
            "#19D3F3",
        ]
    )
    height: int = 400
    margin_l: int = 20
    margin_r: int = 20
    margin_t: int = 40
    margin_b: int = 20
    margin_b_large: int = 80
    opacity: float = 0.75
    scatter_opacity: float = 0.6
    hist_bins: int = 30
    bar_top_n: int = 15
    bar_compare_top_n: int = 10
    scatter_max_pairs: int = 6
    png_width: int = 900
    png_height: int = 500
    png_scale: float = 2.0
    legend_orientation: str = "h"
    xaxis_tickangle: int = -45

    def margin_dict(self, large_bottom: bool = False) -> dict:
        return {
            "l": self.margin_l,
            "r": self.margin_r,
            "t": self.margin_t,
            "b": self.margin_b_large if large_bottom else self.margin_b,
        }

    def legend_dict(self) -> dict:
        return {
            "orientation": self.legend_orientation,
            "yanchor": "bottom",
            "y": 1.02,
        }


_default_instance: Optional[ChartConfig] = None


def default_config() -> ChartConfig:
    global _default_instance
    if _default_instance is None:
        _default_instance = ChartConfig()
    return _default_instance
