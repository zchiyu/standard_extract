from __future__ import annotations

import os
import shutil
from typing import Tuple


def copy_file_to_dir(src_path: str, dst_dir: str, overwrite: bool = True) -> Tuple[bool, str, str]:
    """
    将 src_path 复制到 dst_dir 下，返回 (ok, msg, dst_path)。

    - overwrite=True: 目标存在则覆盖
    """
    if not os.path.isfile(src_path):
        return False, f"源文件不存在: {src_path}", ""

    os.makedirs(dst_dir, exist_ok=True)

    dst_path = os.path.join(dst_dir, os.path.basename(src_path))

    if os.path.exists(dst_path) and not overwrite:
        return True, f"目标已存在，跳过复制: {dst_path}", dst_path

    try:
        shutil.copy2(src_path, dst_path)
        return True, f"已复制: {src_path} -> {dst_path}", dst_path
    except Exception as e:
        return False, f"复制失败: {src_path} -> {dst_path}, err={e}", ""