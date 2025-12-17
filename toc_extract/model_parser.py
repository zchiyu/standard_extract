import re
from typing import Any, Dict, List


def extract_titles_by_pattern(model_data: Any) -> List[Dict[str, str]]:
    """
    从 model.json 数据中提取形如：
      1 范围
      6.3.1 一般要求
    这类标题行。

    假设 model.json 结构为：
      - 顶层 list
      - 每个 page 是 list
      - block dict 中用 key 'content' 存文本
    """
    candidates: List[Dict[str, str]] = []
    title_pattern = re.compile(r'^(\d+(?:\.\d+)*)\s+(.*?)(?:\s+\d+)?$')
    exclude_keywords = ["GB/T", "ICS", "Term", "Definitions", "目次", "前言", "引言"]

    if not isinstance(model_data, list):
        return []

    for page in model_data:
        if not isinstance(page, list):
            continue
        for block in page:
            if not isinstance(block, dict):
                continue

            raw_content = block.get("content")
            text = str(raw_content).strip() if raw_content is not None else ""
            if not text:
                continue

            if any(k in text for k in exclude_keywords):
                continue

            m = title_pattern.match(text)
            if not m:
                continue

            label = m.group(1)
            title = m.group(2).strip()

            # 过滤异常
            if len(label.split(".")) > 5:
                continue
            if title.isdigit():
                continue

            candidates.append({"label": label, "title": title})

    return candidates


def clean_toc_list(candidates: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    清洗目录列表：
    - 从最后一次出现 label=1 的位置开始（避免把目录页重复抓进来）
    - label 去重
    """
    if not candidates:
        return []

    start_indices = [i for i, item in enumerate(candidates) if item.get("label") == "1"]
    if start_indices:
        candidates = candidates[start_indices[-1]:]

    seen = set()
    unique: List[Dict[str, str]] = []
    for item in candidates:
        label = item.get("label")
        if not label:
            continue
        if label in seen:
            continue
        seen.add(label)
        unique.append(item)
    return unique


def calculate_parent_id(label: str) -> str:
    """根据当前标号计算父标号"""
    if not label or "." not in label:
        return "/"
    return label.rsplit(".", 1)[0]


def toc_items_to_rows(clean_items: List[Dict[str, str]], std_no: str, std_title: str) -> List[Dict[str, object]]:
    """
    把 clean_items 转成可直接导出 Excel 的行结构。
    """
    rows: List[Dict[str, object]] = []
    for index, item in enumerate(clean_items):
        clause_id = item["label"]
        clause_text = item["title"]
        level = clause_id.count(".") + 1
        parent_id = calculate_parent_id(clause_id)

        rows.append(
            {
                "order_index": index + 1,
                "std_no": std_no,
                "std_title": std_title,
                "clause_id": clause_id,
                "clause_text": clause_text,
                "level": level,
                "parent_id": parent_id,
            }
        )
    return rows