import os
from pathlib import Path

from config import Config, get_token
from mineru_client import MinerUClient

from utils.io import iter_files, ensure_dir, find_jsons_in_dir, load_json

from pdf_rename.content_list_parser import extract_title_and_stdno_from_content_list
from pdf_rename.renamer import rename_pdf_in_dir

# 你需要有 downloader.py，至少包含 download_zip(url, path, retries, timeout, verify_ssl) 和 unzip(zip_path, out_dir)
from downloader import download_zip, unzip


def log(step: str, msg: str):
    print(f"[{step}] {msg}")


def process_one_pdf(client: MinerUClient, cfg: Config, pdf_path: str):
    pdf_path = str(pdf_path)
    pdf_name = os.path.basename(pdf_path)
    stem = Path(pdf_path).stem

    log("FILE", pdf_path)
    log("STEP", "1/4 上传并解析（MinerU）")
    result = client.submit_local_file(pdf_path, model_version=cfg.model_version)

    if result.get("state") != "done":
        log("FAIL", f"解析失败/未完成: state={result.get('state')} err={result.get('err_msg')}")
        return

    full_zip_url = result.get("full_zip_url")
    if not full_zip_url:
        log("FAIL", "返回结果缺少 full_zip_url，无法下载")
        return

    # 输出目录：G:\temp\standard_zip\<pdf_stem>\
    out_dir = os.path.join(cfg.output_root_dir, stem)
    ensure_dir(out_dir)

    zip_path = os.path.join(out_dir, "result.zip")
    unzip_dir = os.path.join(out_dir, "unzipped")

    log("STEP", "2/4 下载 zip")
    log("URL", full_zip_url)
    download_zip(
        full_zip_url,
        zip_path,
        retries=cfg.download_retries,
        timeout=cfg.download_timeout,
        verify_ssl=cfg.verify_ssl,
    )

    log("STEP", "3/4 解压 zip")
    unzip(zip_path, unzip_dir)

    # 在解压目录中找 content_list json（注意：解压结构可能嵌套，使用递归搜索更稳）
    log("STEP", "4/4 解析 content_list 并重命名 pdf（标准号_标题）")

    # 4.1 找 content_list json（递归）
    # 这里不再 iter_dirs，而直接在 unzip_dir 内做遍历
    found_any = False
    for dirpath, _, _ in os.walk(unzip_dir):
        content_list_jsons = find_jsons_in_dir(dirpath, name_contains="content_list", endswith=".json")
        for p in content_list_jsons:
            found_any = True
            log("DIR", dirpath)
            log("JSON", p)

            data = load_json(p, default=None)
            if not data:
                log("SKIP", "content_list json 读取失败或为空")
                continue

            title, std_no = extract_title_and_stdno_from_content_list(data)
            log("INFO", f"title={title}")
            log("INFO", f"std_no={std_no}")

            if title and std_no:
                ok, msg = rename_pdf_in_dir(os.path.dirname(pdf_path), std_no, title)
                log("RENAME", msg)
            else:
                log("SKIP", "未识别到 title/std_no，跳过重命名")

    if not found_any:
        log("WARN", f"解压目录未找到 content_list json：{unzip_dir}")


def main():
    cfg = Config()
    ensure_dir(cfg.output_root_dir)

    token = get_token(cfg)
    client = MinerUClient(token)

    log("START", f"输入PDF目录: {cfg.input_pdf_dir}")
    log("START", f"输出目录: {cfg.output_root_dir}")

    pdfs = list(iter_files(cfg.input_pdf_dir, suffixes=[".pdf"], recursive=cfg.recursive))
    log("START", f"发现PDF数量: {len(pdfs)}")

    for i, pdf_path in enumerate(pdfs, 1):
        log("PROGRESS", f"{i}/{len(pdfs)}")
        try:
            process_one_pdf(client, cfg, pdf_path)
        except Exception as e:
            log("ERROR", f"{pdf_path} 处理异常: {e}")


if __name__ == "__main__":
    main()