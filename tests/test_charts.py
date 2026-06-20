import os

import pandas as pd
import pytest
import plotly.graph_objects as go

from charts import (
    BarChartStrategy,
    ChartGenerator,
    HistogramStrategy,
    LineChartStrategy,
    ScatterStrategy,
    CompareChartGenerator,
    CompareHistogramStrategy,
    CompareBarStrategy,
    CompareScatterStrategy,
    default_config,
)
from stats import ColumnTypes, detect_column_types


def _read(name, fixtures_dir):
    return pd.read_csv(os.path.join(fixtures_dir, name))


def _collect_figures(strategy_cls, df, col_types):
    strategy = strategy_cls(config=default_config())
    assert strategy.can_apply(col_types.numeric, col_types.categorical, col_types.date) is True

    generated = strategy.generate(
        df, col_types.numeric, col_types.categorical, col_types.date
    )
    return strategy, generated


def test_default_config_returns_same_instance():
    c1 = default_config()
    c2 = default_config()
    assert c1 is c2
    assert len(c1.colors) >= 2


def test_histogram_strategy_can_apply(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    s = HistogramStrategy()
    assert s.can_apply(ct.numeric, ct.categorical, ct.date) is True

    empty_ct = ColumnTypes(numeric=[], categorical=["a"], date=[])
    assert s.can_apply(empty_ct.numeric, empty_ct.categorical, empty_ct.date) is False


def test_histogram_strategy_generates_figures(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    strategy, figs = _collect_figures(HistogramStrategy, df, ct)
    assert len(figs) >= 1
    for fig in figs:
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.layout.title is not None


def test_histogram_data_matches(fixtures_dir):
    df = pd.DataFrame({"x": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10,
                             11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
                             21, 22, 23, 24, 25, 26, 27, 28, 29, 30]})
    ct = ColumnTypes(numeric=["x"], categorical=[], date=[])
    strategy, figs = _collect_figures(HistogramStrategy, df, ct)
    assert len(figs) == 1
    traces = figs[0].data
    assert traces[0].type == "histogram"
    total_count = sum(traces[0].y) if traces[0].y is not None else len(traces[0].x)
    assert total_count == 30


def test_bar_strategy_can_apply(fixtures_dir):
    df = _read("utf8_normal.csv", fixtures_dir)
    ct = detect_column_types(df)
    s = BarChartStrategy()
    assert s.can_apply(ct.numeric, ct.categorical, ct.date) is True


def test_bar_strategy_generates_figures(fixtures_dir):
    df = _read("utf8_normal.csv", fixtures_dir)
    ct = detect_column_types(df)
    strategy, figs = _collect_figures(BarChartStrategy, df, ct)
    assert len(figs) >= 1
    for fig in figs:
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        assert fig.data[0].type == "bar"


def test_bar_data_matches_category_counts():
    df = pd.DataFrame({"cat": ["A", "A", "B", "C", "C", "C"]})
    ct = ColumnTypes(numeric=[], categorical=["cat"], date=[])
    strategy, figs = _collect_figures(BarChartStrategy, df, ct)
    assert len(figs) == 1
    trace = figs[0].data[0]
    values = dict(zip([str(x) for x in trace.x], list(trace.y)))
    assert values.get("A") == 2
    assert values.get("B") == 1
    assert values.get("C") == 3


def test_scatter_strategy_can_apply():
    ct = ColumnTypes(numeric=["a", "b", "c"], categorical=[], date=[])
    s = ScatterStrategy()
    assert s.can_apply(ct.numeric, ct.categorical, ct.date) is True

    ct_one = ColumnTypes(numeric=["a"], categorical=[], date=[])
    assert s.can_apply(ct_one.numeric, ct_one.categorical, ct_one.date) is False


def test_scatter_generates_figures(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    strategy, figs = _collect_figures(ScatterStrategy, df, ct)
    assert len(figs) >= 1
    for fig in figs:
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1
        trace = fig.data[0]
        assert trace.type == "scatter"
        assert trace.mode == "markers"
        assert len(trace.x) >= 1
        assert len(trace.y) == len(trace.x)


def test_line_chart_strategy_can_apply(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    s = LineChartStrategy()
    assert s.can_apply(ct.numeric, ct.categorical, ct.date) is True

    ct_no_date = ColumnTypes(numeric=["a", "b"], categorical=[], date=[])
    assert s.can_apply(ct_no_date.numeric, ct_no_date.categorical, ct_no_date.date) is False


def test_chart_generator_integration(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    gen = ChartGenerator(config=default_config())
    gen.add_strategy(HistogramStrategy(config=default_config()))
    gen.add_strategy(BarChartStrategy(config=default_config()))
    gen.add_strategy(ScatterStrategy(config=default_config()))

    collected = {}
    all_figs = gen.render_all(
        df, ct.numeric, ct.categorical, ct.date,
        figs_dict=collected, key_prefix="t_",
    )
    assert len(all_figs) >= 1
    for fig in all_figs:
        assert isinstance(fig, go.Figure)
    assert len(collected) == len(all_figs)


def test_compare_histogram_strategy_can_apply():
    ct1 = ColumnTypes(numeric=["a", "b"], categorical=[], date=[])
    ct2 = ColumnTypes(numeric=["a", "c"], categorical=[], date=[])
    s = CompareHistogramStrategy(label1="X", label2="Y")
    assert s.can_apply_compare(ct1, ct2) is True

    ct3 = ColumnTypes(numeric=["z"], categorical=[], date=[])
    assert s.can_apply_compare(ct1, ct3) is False


def test_compare_bar_strategy_generates_overlay_figure():
    df1 = pd.DataFrame({"g": ["A", "A", "B"]})
    df2 = pd.DataFrame({"g": ["A", "B", "B", "B"]})
    ct1 = ColumnTypes(numeric=[], categorical=["g"], date=[])
    ct2 = ColumnTypes(numeric=[], categorical=["g"], date=[])

    s = CompareBarStrategy(label1="X", label2="Y")
    assert s.can_apply_compare(ct1, ct2) is True

    figs = s.generate_compare(df1, df2, ct1, ct2)
    assert len(figs) == 1
    fig = figs[0]
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 2
    assert fig.data[0].type == "bar"
    assert fig.data[1].type == "bar"
    assert fig.layout.barmode == "group"


def test_compare_scatter_strategy():
    df1 = pd.DataFrame({"x": [1, 2, 3], "y": [4, 5, 6]})
    df2 = pd.DataFrame({"x": [10, 20, 30], "y": [40, 50, 60]})
    ct1 = ColumnTypes(numeric=["x", "y"], categorical=[], date=[])
    ct2 = ColumnTypes(numeric=["x", "y"], categorical=[], date=[])
    s = CompareScatterStrategy(label1="A", label2="B")
    assert s.can_apply_compare(ct1, ct2) is True
    figs = s.generate_compare(df1, df2, ct1, ct2)
    assert len(figs) == 1
    assert len(figs[0].data) == 2


def test_compare_chart_generator(fixtures_dir):
    df = _read("mixed_types.csv", fixtures_dir)
    ct = detect_column_types(df)
    gen = CompareChartGenerator(config=default_config())
    gen.add_strategy(CompareHistogramStrategy(config=default_config(), label1="A", label2="B"))
    gen.add_strategy(CompareBarStrategy(config=default_config(), label1="A", label2="B"))
    gen.add_strategy(CompareScatterStrategy(config=default_config(), label1="A", label2="B"))

    collected = {}
    figs = gen.render_all(df, df, ct, ct, figs_dict=collected, key_prefix="c_")
    assert len(figs) >= 1
    for fig in figs:
        assert isinstance(fig, go.Figure)
