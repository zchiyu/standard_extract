from typing import Dict, List, Sequence

import pandas as pd

DEFAULT_COLUMNS: Sequence[str] = (
    "order_index",
    "std_no",
    "std_title",
    "clause_id",
    "clause_text",
    "level",
    "parent_id",
)


def export_rows_to_excel(
    rows: List[Dict],
    output_excel_path: str,
    columns_order: Sequence[str] = DEFAULT_COLUMNS,
) -> str:
    """
    将 rows 导出为 Excel。

    Parameters
    ----------
    rows:
        List[Dict]，每个 dict 是一行数据。
    output_excel_path:
        输出 xlsx 路径。
    columns_order:
        列顺序；若 rows 缺少某些列会自动补空列。

    Returns
    -------
    str:
        实际写入的 output_excel_path
    """
    if not rows:
        raise ValueError("rows 为空，未导出任何内容")

    df = pd.DataFrame(rows)

    # 若缺列，补空值，确保顺序稳定
    for col in columns_order:
        if col not in df.columns:
            df[col] = ""

    df = df[list(columns_order)]
    df.to_excel(output_excel_path, index=False)
    return output_excel_path