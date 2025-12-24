import os
from pathlib import Path

from config import Config, get_token
from mineru_client import MinerUClient

from utils.io import iter_files, ensure_dir, find_jsons_in_dir, load_json
from utils.files import copy_file_to_dir

from pdf_rename.content_list_parser import extract_title_and_stdno_from_content_list
from pdf_rename.renamer import rename_pdf_in_dir, sanitize_filename

from downloader import download_zip, unzip

from toc_extract.model_parser import extract_titles_by_pattern, clean_toc_list, toc_items_to_rows
from toc_extract.export_excel import export_rows_to_excel, DEFAULT_COLUMNS
from toc_extract.content_list_images import (
    rename_images_by_caption_from_content_list,
    collect_images_from_content_list,
)


def log(step: str, msg: str):
    print(f"[{step}] {msg}")


def find_any_model_json(unzip_dir: str) -> str:
    for dirpath, _, _ in os.walk(unzip_dir):
        for fn in os.listdir(dirpath):
            low = fn.lower()
            if low.endswith(".json") and ("model" in low) and ("model_list" not in low):
                return os.path.join(dirpath, fn)
    return ""


def process_one_pdf(client: MinerUClient, cfg: Config, pdf_path: str):
    pdf_path = str(pdf_path)
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

    log("STEP", "4/4 解析 content_list 并重命名 pdf（标准号_标题），并复制到输出目录")

    detected_title = None
    detected_std_no = None
    found_any = False

    for dirpath, _, _ in os.walk(unzip_dir):
        content_list_jsons = find_jsons_in_dir(dirpath, name_contains="content_list", endswith=".json")
        for p in content_list_jsons:
            found_any = True
            log("JSON", p)

            data = load_json(p, default=None)
            if not data:
                log("SKIP", "content_list json 读取失败或为空")
                continue

            title, std_no = extract_title_and_stdno_from_content_list(data)
            log("INFO", f"title={title}")
            log("INFO", f"std_no={std_no}")

            if detected_title is None and detected_std_no is None and title and std_no:
                detected_title = title
                detected_std_no = std_no

            if title and std_no:
                ok, msg = rename_pdf_in_dir(os.path.dirname(pdf_path), std_no, title)
                log("RENAME", msg)

                new_name = sanitize_filename(f"{std_no}_{title}") + ".pdf"
                candidate = os.path.join(os.path.dirname(pdf_path), new_name)
                if os.path.isfile(candidate):
                    ok2, msg2, dst_pdf = copy_file_to_dir(candidate, out_dir, overwrite=True)
                    log("COPY_PDF", msg2)
                else:
                    log("COPY_PDF", f"未找到改名后的 PDF：{candidate}")
            else:
                log("SKIP", "未识别到 title/std_no，跳过重命名")

    if not found_any:
        log("WARN", f"解压目录未找到 content_list json：{unzip_dir}")

    # 输出文件夹重命名（同 pdf 规则）
    if detected_std_no and detected_title:
        new_folder_name = sanitize_filename(f"{detected_std_no}_{detected_title}")
        new_out_dir = os.path.join(cfg.output_root_dir, new_folder_name)
        if os.path.abspath(new_out_dir) != os.path.abspath(out_dir):
            base = new_out_dir
            k = 1
            while os.path.exists(new_out_dir):
                k += 1
                new_out_dir = f"{base}_{k}"
            try:
                os.rename(out_dir, new_out_dir)
                log("OUT_DIR", f"输出文件夹已重命名：{out_dir} -> {new_out_dir}")
                out_dir = new_out_dir
                unzip_dir = os.path.join(out_dir, "unzipped")
            except Exception as e:
                log("OUT_DIR_WARN", f"输出文件夹重命名失败：{out_dir} -> {new_out_dir}, err={e}")

    # std_no（同 toc 表）= 标准号_标题（不清洗更可读；若要与文件夹一致可改成 sanitize_filename）
    if detected_std_no and detected_title:
        std_no_out = f"{detected_std_no}_{detected_title}"
        std_title_out = detected_title
    else:
        std_no_out = stem
        std_title_out = ""

    # 1) 图片/表格图片重命名
    log("IMG", "开始按 caption 重命名 images 下图片（支持 image/table）")
    img_mapping, img_errors = rename_images_by_caption_from_content_list(unzip_dir)
    log("IMG", f"图片重命名完成，mapping={len(img_mapping)}")
    if img_errors:
        for e in img_errors[:30]:
            log("IMG_WARN", e)
        if len(img_errors) > 30:
            log("IMG_WARN", f"图片重命名错误较多，仅展示前30条，共 {len(img_errors)} 条")

    # 2) 输出 image.xlsx
    img_items = collect_images_from_content_list(unzip_dir)
    image_rows = []
    for i, it in enumerate(img_items, 1):
        old_rel = it["img_path"]
        # 若已改名，用改名后的相对路径
        new_rel = img_mapping.get(old_rel, old_rel)

        # image 列：写绝对路径（Excel 里可点击打开）
        image_abs = os.path.join(unzip_dir, new_rel)

        caption = (it.get("caption") or "").strip()
        if not caption:
            # 与重命名函数的兜底保持一致
            prefix = "图" if it.get("kind") == "image" else "表"
            caption = f"{prefix}_{it.get('hash')}"

        image_rows.append(
            {
                "order_index": i,
                "std_no": std_no_out,
                "image_title": caption,
                "clause_id": "",     # 暂不自动挂靠条款
                "clause_text": "",   # 暂不自动挂靠条款
                "image": image_abs,  # “图片附件”用路径表示
            }
        )

    from toc_extract.image_excel import export_image_rows_with_embedded_images

    image_excel_path = os.path.join(out_dir, "image.xlsx")
    if image_rows:
        export_image_rows_with_embedded_images(
            image_rows,
            image_excel_path,
            sheet_name="images",
            image_display_px=(320, 200),
        )
        log("IMG_XLSX", f"已导出(含图片嵌入): {image_excel_path} (rows={len(image_rows)})")
    else:
        log("IMG_XLSX", f"未发现图片/表格图片，跳过导出: {image_excel_path}")


    # 3) 导出 toc_results.xlsx（保持你原逻辑）
    model_json_path = find_any_model_json(unzip_dir)
    if not model_json_path:
        log("TOC", f"未找到 model*.json（排除 model_list）：{unzip_dir}")
        return

    model_data = load_json(model_json_path, default=None)
    if not model_data:
        log("TOC", f"model.json 读取失败或为空：{model_json_path}")
        return

    raw_items = extract_titles_by_pattern(model_data)
    clean_items = clean_toc_list(raw_items)
    rows = toc_items_to_rows(clean_items, std_no_out, std_title_out)

    images_dir = os.path.join(unzip_dir, "images")
    image_files = []
    if os.path.isdir(images_dir):
        for fn in os.listdir(images_dir):
            if fn.lower().endswith((".jpg", ".jpeg", ".png", ".bmp", ".gif", ".webp")):
                image_files.append(fn)
    image_files.sort()
    image_cell = ";".join(image_files)

    for r in rows:
        r["model_json_path"] = model_json_path
        r["image"] = image_cell

    excel_path = os.path.join(out_dir, "toc_results.xlsx")
    export_rows_to_excel(rows, excel_path, columns_order=DEFAULT_COLUMNS)
    log("TOC", f"已导出: {excel_path}")


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