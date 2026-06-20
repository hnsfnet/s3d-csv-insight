import io
import pandas as pd


ENCODING_CANDIDATES = ["utf-8", "utf-8-sig", "gbk", "gb2312", "latin-1"]


class CSVLoadError(Exception):
    pass


def read_csv_auto_encoding(file_obj) -> tuple[pd.DataFrame, str]:
    raw_bytes = file_obj.read()
    errors = []
    for enc in ENCODING_CANDIDATES:
        try:
            buf = io.BytesIO(raw_bytes)
            df = pd.read_csv(buf, encoding=enc)
            return df, enc
        except Exception as e:
            errors.append(f"{enc}: {type(e).__name__} — {e}")

    msg = (
        "所有候选编码均解析失败。\n已尝试的编码及错误：\n"
        + "\n".join(f"  - {msg}" for msg in errors)
        + "\n\n建议：请用 Excel 或文本编辑器将文件另存为 UTF-8 编码后再上传。"
    )
    raise CSVLoadError(msg)


def load_csv_file(file_obj) -> tuple[pd.DataFrame, str]:
    return read_csv_auto_encoding(file_obj)
