from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Tuple

from utils.io import load_json, find_jsons_in_dir


def sanitize_filename(s: str) -> str:
    """Windows 文件名清洗"""
    s = (s or "").strip()
    s = re.sub(r'[\\/:*?"<>|]', "_", s)
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def iter_content_list_jsons(unzip_dir: str) -> Iterable[str]:
    """在 unzip_dir 内递归找 content_list*.json"""
    for dirpath, _, _ in os.walk(unzip_dir):
        for p in find_jsons_in_dir(dirpath, name_contains="content_list", endswith=".json"):
            yield p


def _first_str(x: Any) -> str:
    if isinstance(x, list) and x:
        return str(x[0]).strip()
    if isinstance(x, str):
        return x.strip()
    return ""


def parse_media_blocks_from_content_list(content_list_data: Any) -> List[Dict[str, Any]]:
    if not isinstance(content_list_data, list):
        return []

    res: List[Dict[str, Any]] = []
    for blk in content_list_data:
        if not isinstance(blk, dict):
            continue

        typ = blk.get("type")
        if typ not in ("image", "table"):
            continue

        img_path = blk.get("img_path") or ""
        if not isinstance(img_path, str) or not img_path.strip():
            continue

        if typ == "image":
            caption = _first_str(blk.get("image_caption") or [])
        else:
            caption = _first_str(blk.get("table_caption") or [])

        res.append(
            {
                "kind": typ,
                "img_path": img_path.replace("\\", "/"),
                "caption": caption,
                "page_idx": blk.get("page_idx"),
            }
        )

    return res


def _hash_from_img_path(img_path: str) -> str:
    base = os.path.basename(img_path.replace("\\", "/"))
    return os.path.splitext(base)[0]


def collect_images_from_content_list(unzip_dir: str) -> List[Dict[str, Any]]:
    """
    收集 content_list 里所有 image/table 图片块，用于生成 image.xlsx。
    返回按出现顺序的列表，每个元素包含：
      kind, img_path, caption, page_idx, hash
    """
    items: List[Dict[str, Any]] = []
    for json_path in iter_content_list_jsons(unzip_dir):
        data = load_json(json_path, default=None)
        if not data:
            continue
        blocks = parse_media_blocks_from_content_list(data)
        for b in blocks:
            img_path = b["img_path"]
            items.append(
                {
                    "kind": b["kind"],
                    "img_path": img_path,
                    "caption": (b.get("caption") or "").strip(),
                    "page_idx": b.get("page_idx"),
                    "hash": _hash_from_img_path(img_path),
                    "content_list_json": json_path,
                }
            )
    return items


def rename_images_by_caption_from_content_list(unzip_dir: str) -> Tuple[Dict[str, str], List[str]]:
    mapping: Dict[str, str] = {}
    errors: List[str] = []

    used: Dict[str, int] = {}

    for json_path in iter_content_list_jsons(unzip_dir):
        data = load_json(json_path, default=None)
        if not data:
            continue

        blocks = parse_media_blocks_from_content_list(data)
        for b in blocks:
            old_rel = b["img_path"]
            kind = b["kind"]
            caption = (b.get("caption") or "").strip()

            src_abs = os.path.join(unzip_dir, old_rel)
            if not os.path.isfile(src_abs):
                errors.append(f"图片不存在: {src_abs} (from {json_path})")
                continue

            ext = os.path.splitext(src_abs)[1]
            h = _hash_from_img_path(old_rel)

            if caption:
                base = sanitize_filename(caption)
            else:
                prefix = "图" if kind == "image" else "表"
                base = f"{prefix}_{h}"

            if not base:
                continue

            n = used.get(base, 0) + 1
            used[base] = n
            new_base = base if n == 1 else f"{base}_{n}"
            new_rel = f"images/{new_base}{ext}"
            dst_abs = os.path.join(unzip_dir, new_rel)

            while os.path.exists(dst_abs) and os.path.abspath(dst_abs) != os.path.abspath(src_abs):
                used[base] += 1
                new_base = f"{base}_{used[base]}"
                new_rel = f"images/{new_base}{ext}"
                dst_abs = os.path.join(unzip_dir, new_rel)

            try:
                os.rename(src_abs, dst_abs)
                mapping[old_rel] = new_rel
            except Exception as e:
                errors.append(f"重命名失败: {src_abs} -> {dst_abs}, err={e}")

    return mapping, errors