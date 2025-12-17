import json
import os
from pathlib import Path
from typing import Iterable, List, Optional, Any


def load_json(path: str, default: Any = None) -> Any:
    """
    【输入】
      - path (str): JSON 文件的路径（可以是绝对路径或相对路径）
      - default (Any): 当读取/解析失败时返回的默认值（例如 None、[]、{}）

    【输出】
      - Any: 解析成功则返回 json.load(...) 的结果（可能是 dict/list/str/int 等）
             解析失败则返回 default
    """
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def ensure_dir(path: str) -> str:
    """
    【输入】
      - path (str): 需要确保存在的目录路径

    【输出】
      - str: 返回传入的 path（目录会被创建/确保存在）
    """
    os.makedirs(path, exist_ok=True)
    return path


def iter_files(root: str, suffixes: Optional[List[str]] = None, recursive: bool = True) -> Iterable[str]:
    """
    【功能】
      遍历 root 目录下的文件路径，可按后缀过滤，可递归子目录。

    【输入】
      - root (str): 根目录路径
      - suffixes (Optional[List[str]]):
          * None：不按后缀过滤，返回所有文件
          * [".pdf", ".json"]：只返回指定后缀的文件（不区分大小写）
      - recursive (bool):
          * True：递归遍历 root 的所有子目录
          * False：只遍历 root 当前目录（不进入子目录）

    【输出】
      - Iterable[str]:
          一个可迭代对象（生成器）。for 迭代时，每次 yield 一个文件的完整路径字符串。
          若 root 不存在，则不 yield 任何内容（等价于空迭代）。
    """
    root_path = Path(root)
    if not root_path.exists():
        return  # root 不存在：直接结束生成器（不产出任何路径）

    if suffixes:
        suffixes = [s.lower() for s in suffixes]

    paths = root_path.rglob("*") if recursive else root_path.glob("*")
    for p in paths:
        if not p.is_file():
            continue
        if suffixes and p.suffix.lower() not in suffixes:
            continue
        yield str(p)


def find_jsons_in_dir(dirpath: str, name_contains: str = "", endswith: str = ".json") -> List[str]:
    """
    【功能】
      在“单个目录（不递归）”中查找符合条件的 JSON 文件路径列表。

    【输入】
      - dirpath (str): 要搜索的目录路径（仅当前层，不进入子目录）
      - name_contains (str):
          文件名需要包含的子串（不区分大小写）。空字符串表示不限制。
          例：name_contains="content_list" 用于筛选 *content_list*.json
      - endswith (str):
          文件名后缀要求（默认 ".json"）。不区分大小写。

    【输出】
      - List[str]:
          返回符合条件的文件完整路径列表。
          如果目录不存在/无权限/其它异常，则返回空列表 []。
    """
    res: List[str] = []
    try:
        for fn in os.listdir(dirpath):
            low = fn.lower()
            if not low.endswith(endswith.lower()):
                continue
            if name_contains and (name_contains.lower() not in low):
                continue
            res.append(os.path.join(dirpath, fn))
    except Exception:
        return []
    return res


def iter_dirs(root: str) -> Iterable[str]:
    """
    【功能】
      遍历 root 下所有目录，储存目录信息。

    【输入】
      - root (str): 根目录路径

    【输出】
      - Iterable[str]:
          一个可迭代对象（生成器）。for 迭代时，每次 yield 一个目录路径字符串（dirpath）。
          若 root 不存在，os.walk 会自然不产出任何内容（空迭代）。
    """
    for dirpath, dirnames, filenames in os.walk(root):
        yield dirpath