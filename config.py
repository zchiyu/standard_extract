import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    """
    统一配置入口：
    - Token：优先读环境变量 MINERU_TOKEN；也可在本地用 .env/系统环境配置
    - 路径：输入PDF目录、输出ZIP/解压目录
    - 轮询与下载：超时、重试等
    """

    # ====== MinerU ======
    mineru_base_url: str = "https://mineru.net/api/v4"
    mineru_token_env: str = "MINERU_TOKEN"
    model_version: str = "vlm"

    # ====== 批处理输入/输出 ======
    input_pdf_dir: str = r"G:\研究生\pdf\DB1"
    output_root_dir: str = r"G:\temp\standard_zip"

    # ====== 轮询/超时 ======
    poll_interval_sec: int = 2

    # ====== 下载重试/超时 ======
    download_retries: int = 5
    # (connect_timeout, read_timeout)
    download_timeout: tuple = (10, 180)
    verify_ssl: bool = True

    # ====== 其它开关 ======
    recursive: bool = True
    keep_zip: bool = True


def get_token(cfg: Config) -> str:
    """
    从环境变量读取 Token（避免写进代码）。
    用法：
      set MINERU_TOKEN=xxxxx  (Windows)
      export MINERU_TOKEN=xxxxx (Linux/Mac)
    """
    token = os.environ.get(cfg.mineru_token_env,
    "eyJ0eXBlIjoiSldUIiwiYWxnIjoiSFM1MTIifQ.eyJqdGkiOiIyODYwMDU4OSIsInJvbCI6IlJPTEVfUkVHSVNURVIiLCJpc3MiOiJPcGVuWExhYiIsImlhdCI6MTc2NDU5MDc5NCwiY2xpZW50SWQiOiJsa3pkeDU3bnZ5MjJqa3BxOXgydyIsInBob25lIjoiMTU3MzAxNzMzMjAiLCJvcGVuSWQiOm51bGwsInV1aWQiOiI1NmUyNWI5Zi1mMzk2LTQzMGEtODJlYy0wNGE1MWEyMzJmYmMiLCJlbWFpbCI6IiIsImV4cCI6MTc2NTgwMDM5NH0.ENFLBxGQaJ-YN9NyskYSpFaaFZw0rgJHK96eajUiAvi84DAn9T94smBLUQCaAnw_1BVSZLTAxeThTeqf-_p1ZA").strip()
    if not token:
        raise RuntimeError(
            f"未设置 MinerU Token：请配置环境变量 {cfg.mineru_token_env}"
        )
    return token