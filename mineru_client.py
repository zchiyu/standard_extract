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

    def _check_response(self, response, action_name):
        """通用响应检查"""
        if response.status_code != 200:
            raise Exception(f"[{action_name}] HTTP请求失败: {response.status_code} - {response.text}")

        res_json = response.json()
        if res_json.get("code") != 0:
            raise Exception(f"[{action_name}] API返回错误: {res_json.get('msg')} (Code: {res_json.get('code')})")

        return res_json["data"]

    def submit_url_task(self, file_url, model_version="vlm"):
        """
        场景1: 提交单个 URL 解析任务
        """
        url = f"{self.base_url}/extract/task"
        data = {
            "url": file_url,
            "model_version": model_version,
            "is_ocr": True,  # 仅对 pipeline 模型有效
            "enable_formula": True  # 仅对 pipeline 模型有效
        }

        print(f"1. 正在提交 URL 解析任务: {file_url} ...")
        res = requests.post(url, headers=self.headers, json=data)
        data = self._check_response(res, "提交URL任务")

        task_id = data["task_id"]
        print(f"   -> 任务提交成功，Task ID: {task_id}")
        return self.wait_for_task_result(task_id)

    def wait_for_task_result(self, task_id):
        """
        轮询单个任务结果
        """
        url = f"{self.base_url}/extract/task/{task_id}"

        print(f"2. 开始轮询任务状态 (Task ID: {task_id})...")
        while True:
            res = requests.get(url, headers=self.headers)
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
                # pending, converting, waiting-file 等状态
                print(f"\r   -> 当前状态: {state} ...", end="", flush=True)

            time.sleep(2)  # 避免请求过于频繁

    def submit_local_file(self, file_path, model_version="vlm"):
        """
        场景2: 上传本地文件并解析 (批量接口流程)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")

        file_name = os.path.basename(file_path)

        # 1. 获取上传链接
        print(f"1. 正在申请上传链接: {file_name} ...")
        url_batch = f"{self.base_url}/file-urls/batch"
        data = {
            "files": [{"name": file_name}],
            "model_version": model_version
        }

        res = requests.post(url_batch, headers=self.headers, json=data)
        res_data = self._check_response(res, "获取上传链接")

        batch_id = res_data["batch_id"]
        upload_urls = res_data["file_urls"]

        if not upload_urls:
            raise Exception("未获取到有效的上传 URL")

        # 2. 上传文件 (PUT 请求，注意不能带 Authorization header)
        print(f"2. 正在上传文件 (Batch ID: {batch_id}) ...")
        with open(file_path, 'rb') as f:
            upload_res = requests.put(upload_urls[0], data=f)
            if upload_res.status_code != 200:
                raise Exception(f"文件上传失败 HTTP: {upload_res.status_code}")
        print("   -> 上传成功，系统将自动开始解析。")

        # 3. 轮询批量任务结果
        return self.wait_for_batch_result(batch_id)

    def wait_for_batch_result(self, batch_id):
        """
        轮询批量任务结果
        """
        url = f"{self.base_url}/extract-results/batch/{batch_id}"

        print(f"3. 开始轮询批量任务状态...")
        while True:
            res = requests.get(url, headers=self.headers)
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
