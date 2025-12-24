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
    "model_json_path",
    "image",
)


def export_rows_to_excel(
    rows: List[Dict],
    output_excel_path: str,
    columns_order: Sequence[str] = DEFAULT_COLUMNS,
) -> str:
    if not rows:
        raise ValueError("rows 为空，未导出任何内容")

    df = pd.DataFrame(rows)

    for col in columns_order:
        if col not in df.columns:
            df[col] = ""

    df = df[list(columns_order)]
    df.to_excel(output_excel_path, index=False)
    return output_excel_path