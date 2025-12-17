import requests
import time
import os
import zipfile

def download_zip(full_zip_url: str, zip_path: str, retries: int = 5, timeout=(10, 120), verify_ssl: bool = True):
    """
    更稳的下载：
    - retries: 重试次数
    - timeout: (连接超时, 读取超时)
    - verify_ssl: 是否校验证书（建议 True；若你网络环境导致 TLS EOF，可临时 False 验证）
    """
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            # 每次尝试都新建会话，避免复用连接造成 EOF
            with requests.Session() as s:
                # 明确关闭 keep-alive，降低 EOF 概率
                headers = {"Connection": "close"}
                with s.get(full_zip_url, stream=True, timeout=timeout, verify=verify_ssl, headers=headers) as r:
                    r.raise_for_status()
                    with open(zip_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                f.write(chunk)
            return  # 成功直接返回

        except requests.exceptions.SSLError as e:
            last_err = e
            print(f"[下载重试] SSL错误，第 {attempt}/{retries} 次失败：{e}")
            time.sleep(2 * attempt)

        except requests.exceptions.RequestException as e:
            last_err = e
            print(f"[下载重试] 网络错误，第 {attempt}/{retries} 次失败：{e}")
            time.sleep(2 * attempt)

    raise Exception(f"zip 下载失败，已重试 {retries} 次：{full_zip_url}\n最后错误：{last_err}")


def unzip(zip_path: str, out_dir: str):
    os.makedirs(out_dir, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(out_dir)
