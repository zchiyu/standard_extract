from __future__ import annotations

import os
from typing import Any, Dict, List, Tuple

import pandas as pd


def append_row(rows: List[Dict[str, Any]], row: Dict[str, Any]) -> None:
    """
    向 rows 追加一行（dict），用于最后导出 Excel。

    输入:
      - rows: List[Dict[str, Any]] 累积容器
      - row: Dict[str, Any] 一行数据
    输出:
      - None（原地修改 rows）
    """
    rows.append(row)


def save_rows_to_excel(
    rows: List[Dict[str, Any]],
    output_excel_path: str,
    columns: List[str] | None = None,
) -> Tuple[bool, str]:
    """
    将 rows 写入 Excel。

    输入:
      - rows: 每个元素是一行 dict
      - output_excel_path: 输出 xlsx 路径
      - columns: 可选，指定列顺序；不传则用 DataFrame 自动推断

    输出:
      - (ok, msg)
    """
    if not rows:
        return False, "rows 为空，未写入 Excel"

    out_dir = os.path.dirname(output_excel_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    df = pd.DataFrame(rows)
    if columns:
        # 若缺列会自动补 NaN；若多列会被忽略
        df = df.reindex(columns=columns)

    try:
        df.to_excel(output_excel_path, index=False)
        return True, f"已写入 Excel: {output_excel_path}（rows={len(rows)}）"
    except Exception as e:
        return False, f"写入 Excel 失败: {e}"