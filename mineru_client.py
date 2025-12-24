import requests
import time
import os


class MinerUClient:
    def __init__(self, token):
        self.base_url = "https://mineru.net/api/v4"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}"
        }

        # 关键：不要信任环境变量代理（HTTP_PROXY/HTTPS_PROXY/ALL_PROXY）
        self.session = requests.Session()
        self.session.trust_env = False

        # （可选）你也可以显式清空代理，双保险
        self.session.proxies = {}

    def _check_response(self, response, action_name):
        if response.status_code != 200:
            raise Exception(f"[{action_name}] HTTP请求失败: {response.status_code} - {response.text}")
        res_json = response.json()
        if res_json.get("code") != 0:
            raise Exception(f"[{action_name}] API返回错误: {res_json.get('msg')} (Code: {res_json.get('code')})")
        return res_json["data"]

    def submit_url_task(self, file_url, model_version="vlm"):
        url = f"{self.base_url}/extract/task"
        data = {
            "url": file_url,
            "model_version": model_version,
            "is_ocr": True,
            "enable_formula": True
        }

        print(f"1. 正在提交 URL 解析任务: {file_url} ...")
        res = self.session.post(url, headers=self.headers, json=data)
        data = self._check_response(res, "提交URL任务")

        task_id = data["task_id"]
        print(f"   -> 任务提交成功，Task ID: {task_id}")
        return self.wait_for_task_result(task_id)

    def wait_for_task_result(self, task_id):
        url = f"{self.base_url}/extract/task/{task_id}"

        print(f"2. 开始轮询任务状态 (Task ID: {task_id})...")
        while True:
            res = self.session.get(url, headers=self.headers)
            data = self._check_response(res, "查询任务状态")

            state = data["state"]
            if state == "done":
                print(f"\n[完成] 解析成功!")
                return data
            elif state == "failed":
                print(f"\n[失败] 解析失败: {data.get('err_msg')}")
                return data
            elif state == "running":
                progress = data.get("extract_progress", {})
                current = progress.get("extracted_pages", 0)
                total = progress.get("total_pages", "?")
                print(f"\r   -> 正在解析: 已处理 {current}/{total} 页...", end="", flush=True)
            else:
                print(f"\r   -> 当前状态: {state} ...", end="", flush=True)

            time.sleep(2)

    def submit_local_file(self, file_path, model_version="vlm"):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        file_name = os.path.basename(file_path)

        print(f"1. 正在申请上传链接: {file_name} ...")
        url_batch = f"{self.base_url}/file-urls/batch"
        data = {"files": [{"name": file_name}], "model_version": model_version}

        res = self.session.post(url_batch, headers=self.headers, json=data)
        res_data = self._check_response(res, "获取上传链接")

        batch_id = res_data["batch_id"]
        upload_urls = res_data["file_urls"]
        if not upload_urls:
            raise Exception("未获取到有效的上传 URL")

        # 上传也用同一个 session，确保同样不走系统代理
        print(f"2. 正在上传文件 (Batch ID: {batch_id}) ...")
        with open(file_path, 'rb') as f:
            upload_res = self.session.put(upload_urls[0], data=f)  # 不带 Authorization header 是对的
            if upload_res.status_code != 200:
                raise Exception(f"文件上传失败 HTTP: {upload_res.status_code}")

        print("   -> 上传成功，系统将自动开始解析。")
        return self.wait_for_batch_result(batch_id)

    def wait_for_batch_result(self, batch_id):
        url = f"{self.base_url}/extract-results/batch/{batch_id}"

        print(f"3. 开始轮询批量任务状态...")
        while True:
            res = self.session.get(url, headers=self.headers)
            data = self._check_response(res, "查询批量状态")

            file_result = data["extract_result"][0]
            state = file_result["state"]

            if state == "done":
                print(f"\n[完成] {file_result['file_name']} 解析成功!")
                return file_result
            elif state == "failed":
                print(f"\n[失败] {file_result['file_name']} 解析失败: {file_result.get('err_msg')}")
                return file_result
            elif state == "running":
                progress = file_result.get("extract_progress", {})
                current = progress.get("extracted_pages", 0)
                total = progress.get("total_pages", "?")
                print(f"\r   -> 正在解析: 已处理 {current}/{total} 页...", end="", flush=True)
            else:
                print(f"\r   -> 当前状态: {state} ...", end="", flush=True)

            time.sleep(2)