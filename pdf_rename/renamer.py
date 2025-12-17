import os
import re
from typing import Tuple


def sanitize_filename(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r'[\\/:*?"<>|]', '_', s)
    s = re.sub(r'\s+', '_', s)
    s = re.sub(r'_+', '_', s)
    return s.strip('_')


def rename_pdf_in_dir(dirpath: str, std_no: str, title: str) -> Tuple[bool, str]:
    """
    将 dirpath 下的 pdf 重命名为：标准号_标题.pdf
    返回: (ok, msg)
    """
    if not std_no or not title:
        return False, "std_no/title 为空"

    std_no_clean = sanitize_filename(std_no)
    title_clean = sanitize_filename(title)
    new_name = sanitize_filename(f"{std_no_clean}_{title_clean}") + ".pdf"
    new_pdf_path = os.path.join(dirpath, new_name)

    pdfs = [fn for fn in os.listdir(dirpath) if fn.lower().endswith(".pdf")]
    if not pdfs:
        return False, f"未找到 pdf：{dirpath}"

    # 如果目录里多个 pdf：选文件名最长的那个（你可按需要改策略）
    old_pdf = pdfs[0] if len(pdfs) == 1 else max(pdfs, key=len)
    old_pdf_path = os.path.join(dirpath, old_pdf)

    if os.path.abspath(old_pdf_path) == os.path.abspath(new_pdf_path):
        return True, "pdf 名称已符合目标命名，无需重命名"

    if os.path.exists(new_pdf_path):
        return False, f"目标文件已存在，跳过：{new_pdf_path}"

    try:
        os.rename(old_pdf_path, new_pdf_path)
        return True, f"已重命名：{old_pdf} -> {new_name}"
    except Exception as e:
        return False, f"重命名失败：{old_pdf_path} -> {new_pdf_path}，原因：{e}"