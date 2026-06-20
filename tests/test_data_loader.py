import io

import pytest

from data_loader import CSVLoadError, load_csv_file, read_csv_auto_encoding


def test_read_utf8_csv(open_fixture):
    with open_fixture("utf8_normal.csv") as f:
        df, enc = read_csv_auto_encoding(f)
    assert enc.lower().startswith("utf")
    assert list(df.columns) == ["name", "age", "score", "city"]
    assert len(df) == 6
    assert df.loc[0, "name"] == "Alice"
    assert df.loc[0, "age"] == 25


def test_read_gbk_csv(open_fixture):
    with open_fixture("gbk_chinese.csv") as f:
        df, enc = read_csv_auto_encoding(f)
    assert enc.lower() in ("gbk", "gb2312")
    assert list(df.columns) == ["姓名", "年龄", "分数", "城市"]
    assert len(df) == 4
    assert df.loc[0, "姓名"] == "张三"


def test_header_only_csv(open_fixture):
    with open_fixture("header_only.csv") as f:
        df, enc = read_csv_auto_encoding(f)
    assert list(df.columns) == ["name", "age", "score", "city"]
    assert len(df) == 0


def test_empty_csv(open_fixture):
    with open_fixture("empty.csv") as f:
        with pytest.raises(CSVLoadError) as exc_info:
            read_csv_auto_encoding(f)
    msg = str(exc_info.value)
    assert "所有候选编码均解析失败" in msg
    assert "utf-8" in msg


def test_missing_column_names(open_fixture):
    with open_fixture("missing_column_names.csv") as f:
        df, enc = read_csv_auto_encoding(f)
    assert enc.lower().startswith("utf")
    assert len(df.columns) == 4
    assert len(df) == 2
    assert df.columns[0] != "Alice"


def test_broken_encoding(open_fixture):
    with open_fixture("broken_encoding.bin") as f:
        with pytest.raises(CSVLoadError) as exc_info:
            read_csv_auto_encoding(f)
    msg = str(exc_info.value)
    assert "已尝试的编码及错误" in msg
    for enc in ["utf-8", "gbk", "latin-1"]:
        assert enc in msg


def test_load_csv_file_alias(open_fixture):
    with open_fixture("utf8_normal.csv") as f:
        df, enc = load_csv_file(f)
    assert len(df) == 6
    assert enc.lower().startswith("utf")


def test_bytesio_round_trip():
    data = "a,b,c\n1,2,3\n4,5,6\n"
    buf = io.BytesIO(data.encode("utf-8"))
    df, enc = read_csv_auto_encoding(buf)
    assert enc.lower().startswith("utf")
    assert list(df.columns) == ["a", "b", "c"]
    assert len(df) == 2
