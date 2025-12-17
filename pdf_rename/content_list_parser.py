import re
from typing import Any, Dict, List, Optional, Tuple


def count_chinese(s: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff]', s or ""))


def build_stdno_pattern() -> re.Pattern:
    """
    相对通用的“标准号”匹配正则（可继续扩展前缀）：
      GB/T 30269.901—2016
      DB37/T 4866-2025
      DB11 2251-2024
      DB21/T 3728.4-2024
      DB37/T 4658.3-2023
    """
    prefixes = r"(?:GB|DB\d{0,3}|YY|JJF|JGJ|HG|SN|SB|NY|LY|SL|QB|TB|NB|SJ|WH|WS|JR)"
    return re.compile(
        r'^' +
        prefixes +
        r'(?:\s*\/\s*[A-Z])?' +        # 可选 /T /Z ...
        r'\s*' +
        r'\d+(?:\.\d+)*' +             # 数字段，允许 3728.4 / 4658.3
        r'(?:\s*[-—]\s*\d{2,4})?' +    # -2025 或 —2016
        r'$'
    )


def clean_std_no_keep_dot(std_no: str) -> str:
    """
    标准号清洗：除 '.' 外的符号替换为 '_'
    - 不使用占位符，避免 KEEP_DOT 泄漏
    - 保留：字母数字下划线/中文/点号'.'
    """
    s = (std_no or "").strip()
    s = s.replace('—', '-').replace('－', '-').replace('–', '-')  # 统一破折号
    s = re.sub(r'[^\w\u4e00-\u9fff\.]', '_', s)
    s = re.sub(r'_+', '_', s).strip('_')
    return s


def extract_title_from_page0_blocks(content_list: List[Dict[str, Any]]) -> Optional[str]:
    """
    标题识别规则（与你之前约定一致）：
    - page_idx == 0
    - type == text
    - bbox[1] > 300 且 bbox[3] < 600
    - 多候选取中文字符最多
    - 兜底：第一页所有 text 中中文最多的一行（排除纯英文）
    """
    title_candidates: List[Tuple[int, int, str]] = []

    for blk in content_list:
        if not isinstance(blk, dict):
            continue
        if blk.get("page_idx") != 0:
            continue
        if blk.get("type") != "text":
            continue

        text = (blk.get("text") or "").strip()
        bbox = blk.get("bbox") or []
        if not text or len(bbox) != 4:
            continue

        if bbox[1] > 300 and bbox[3] < 600:
            title_candidates.append((count_chinese(text), len(text), text))

    if title_candidates:
        title_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return title_candidates[0][2]

    # fallback
    fallback: List[Tuple[int, int, str]] = []
    for blk in content_list:
        if not isinstance(blk, dict):
            continue
        if blk.get("page_idx") != 0:
            continue
        if blk.get("type") != "text":
            continue

        text = (blk.get("text") or "").strip()
        bbox = blk.get("bbox") or []
        if not text or len(bbox) != 4:
            continue
        cn = count_chinese(text)
        if cn == 0:
            continue
        fallback.append((cn, len(text), text))

    if fallback:
        fallback.sort(key=lambda x: (x[0], x[1]), reverse=True)
        return fallback[0][2]

    return None


def extract_stdno_from_page0_blocks(content_list: List[Dict[str, Any]], y_threshold: int = 350) -> Optional[str]:
    """
    标准号识别规则：
    - page_idx == 0
    - type in (header, text)
    - bbox[1] < y_threshold（第一页上半区）
    - text 匹配 build_stdno_pattern()
    - 多候选优先：更长的文本，其次 bbox[0] 更大（更靠右）
    """
    std_pattern = build_stdno_pattern()
    std_candidates: List[Tuple[int, int, str]] = []

    for blk in content_list:
        if not isinstance(blk, dict):
            continue
        if blk.get("page_idx") != 0:
            continue
        if blk.get("type") not in ("header", "text"):
            continue

        text = (blk.get("text") or "").strip()
        bbox = blk.get("bbox") or []
        if not text or len(bbox) != 4:
            continue

        if bbox[1] < y_threshold:
            t2 = re.sub(r'\s+', ' ', text).strip()
            if std_pattern.match(t2):
                std_candidates.append((len(t2), int(bbox[0]), t2))

    if not std_candidates:
        return None

    std_candidates.sort(key=lambda x: (x[0], x[1]), reverse=True)
    return clean_std_no_keep_dot(std_candidates[0][2])


def extract_title_and_stdno_from_content_list(content_list: Any) -> Tuple[Optional[str], Optional[str]]:
    """
    从 content_list.json（顶层 list）提取 (title, std_no)。
    """
    if not isinstance(content_list, list):
        return None, None

    title = extract_title_from_page0_blocks(content_list)
    std_no = extract_stdno_from_page0_blocks(content_list)
    return title, std_no