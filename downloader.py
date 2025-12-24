import requests
import time
import os
import zipfile

def download_zip(
    full_zip_url: str,
    zip_path: str,
    retries: int = 5,
    timeout=(10, 120),
    verify_ssl: bool = True,
    bypass_proxy: bool = True,   # 新增：是否绕开系统代理（Clash）
):
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)

    last_err = None
    for attempt in range(1, retries + 1):
        try:
            with requests.Session() as s:
                # 关键：绕开系统代理（HTTP(S)_PROXY / ALL_PROXY）
                if bypass_proxy:
                    s.trust_env = False
                    s.proxies = {}  # 双保险

                headers = {"Connection": "close"}

                # 如果你想更明确，也可以每次 resolve 走直连 DNS（通常不需要）
                with s.get(
                    full_zip_url,
                    stream=True,
                    timeout=timeout,
                    verify=verify_ssl,
                    headers=headers,
                    allow_redirects=True,
                ) as r:
                    r.raise_for_status()
                    with open(zip_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=1024 * 256):
                            if chunk:
                                f.write(chunk)
            return

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