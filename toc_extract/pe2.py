import json
import os
import re
from typing import Dict, List, Tuple, Any, Set

import pandas as pd


def load_data(filepath: str) -> Any:
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取文件失败 {filepath}: {e}")
        return []


def extract_std_info_from_path(folder_path: str) -> Tuple[str, str]:
    folder_name = os.path.basename(folder_path)

    match = re.search(r'[\u4e00-\u9fa5]', folder_name)
    if match:
        split_index = match.start()
        std_no = folder_name[:split_index].strip('_').strip()
        std_title = folder_name[split_index:].strip()
    else:
        std_no = folder_name
        std_title = "/"

    if std_title == "/":
        return std_no, std_title

    if ".pdf" in std_title:
        std_title = std_title.removesuffix(".pdf")

    placeholder = "##KEEP_DOT##"
    std_title = re.sub(r'(?<=\d)\.(?=\d)', placeholder, std_title)
    std_title = re.sub(r'[^\w\u4e00-\u9fa5]', '_', std_title)
    std_title = std_title.replace(placeholder, '.')

    return std_no, std_title


def extract_titles_by_pattern(data: Any) -> List[Dict[str, str]]:
    candidates: List[Dict[str, str]] = []
    title_pattern = re.compile(r'^(\d+(?:\.\d+)*)\s+(.*?)(?:\s+\d+)?$')
    exclude_keywords = ["GB/T", "ICS", "Term", "Definitions", "目次", "前言", "引言"]

    if not isinstance(data, list):
        return []

    for page in data:
        if not isinstance(page, list):
            continue
        for block in page:
            raw_content = block.get('content')
            text = str(raw_content).strip() if raw_content is not None else ""

            if not text:
                continue
            if any(k in text for k in exclude_keywords):
                continue

            match = title_pattern.match(text)
            if not match:
                continue

            label = match.group(1)
            title = match.group(2).strip()

            if len(label.split('.')) > 5:
                continue
            if title.isdigit():
                continue

            candidates.append({"label": label, "title": title})

    return candidates


def clean_toc_list(candidates: List[Dict[str, str]]) -> List[Dict[str, str]]:
    if not candidates:
        return []

    start_indices = [i for i, item in enumerate(candidates) if item.get('label') == '1']
    if start_indices:
        candidates = candidates[start_indices[-1]:]

    seen_labels = set()
    unique_candidates: List[Dict[str, str]] = []
    for item in candidates:
        lab = item.get("label")
        if not lab:
            continue
        if lab in seen_labels:
            continue
        seen_labels.add(lab)
        unique_candidates.append(item)

    return unique_candidates


def calculate_parent_id(label: str) -> str:
    return "/" if '.' not in label else label.rsplit('.', 1)[0]


def process_folder_to_excel(root_folder: str, output_excel_path: str) -> None:
    """
    需求适配：
      1) Excel 的 std_no 输出为 “标题号 + 标题”（例如: "1.2 范围"）
      2) 去重：同一个 root_folder 内避免重复输出
    """
    print(f"正在遍历文件夹: {root_folder}")

    rows: List[Dict[str, Any]] = []
    seen: Set[Tuple[str, str]] = set()  # (clause_id, clause_text) 去重

    for dirpath, dirnames, filenames in os.walk(root_folder):
        for filename in filenames:
            low = filename.lower()
            if "model" in low and low.endswith(".json"):
                full_path = os.path.join(dirpath, filename)
                print(f"处理中: {full_path}")

                # 原有：从文件夹名提取（保留列 std_title 以便溯源）
                _std_no_from_folder, std_title = extract_std_info_from_path(dirpath)

                data = load_data(full_path)
                if not data:
                    continue

                raw_items = extract_titles_by_pattern(data)
                clean_items = clean_toc_list(raw_items)

                if not clean_items:
                    print("  - 警告: 未识别到有效目录")
                    continue

                for index, item in enumerate(clean_items):
                    clause_id = item["label"]
                    clause_text = item["title"]

                    # 2) 去重：避免重复输出
                    key = (clause_id, clause_text)
                    if key in seen:
                        continue
                    seen.add(key)

                    level = clause_id.count(".") + 1
                    parent_id = calculate_parent_id(clause_id)

                    # 1) std_no 输出为 “标题号+标题”
                    std_no_out = f"{clause_id} {clause_text}".strip()

                    rows.append(
                        {
                            "order_index": index + 1,
                            "std_no": std_no_out,
                            "std_title": std_title,
                            "clause_id": clause_id,
                            "clause_text": clause_text,
                            "level": level,
                            "parent_id": parent_id,
                            "model_json_path": full_path,
                        }
                    )

                print(f"  - 已提取 {len(clean_items)} 条记录（去重后累计 {len(rows)}）")

    if not rows:
        print("未提取到任何数据。")
        return

    print(f"\n正在保存结果到: {output_excel_path} ...")
    os.makedirs(os.path.dirname(output_excel_path) or ".", exist_ok=True)

    df = pd.DataFrame(rows)
    columns_order = [
        "order_index",
        "std_no",
        "std_title",
        "clause_id",
        "clause_text",
        "level",
        "parent_id",
        "model_json_path",
    ]
    df = df[columns_order]

    try:
        df.to_excel(output_excel_path, index=False)
        print("全部完成！")
    except Exception as e:
        print(f"保存 Excel 失败: {e} (请检查文件是否被占用)")