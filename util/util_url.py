"""
⚠️ 一旦我被更新，务必更新我的开头注释，以及所属的文件夹的md
Input: 测试数据或模块
Output: 测试结果
Pos: 测试文件：util_url.py
"""

import logging
import os
import requests
from pathlib import Path
from datetime import datetime, timedelta
import base64
import hashlib
from urllib.parse import urlparse
from typing import Optional
from dotenv import load_dotenv
from config import config as cfg
from config.logging_config import get_logger
import oss2
import time

# 项目启动时初始化日志
logger = get_logger(__name__)


def get_upload_policy(api_key, model_name):
    """获取文件上传凭证"""
    url = "https://dashscope.aliyuncs.com/api/v1/uploads"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    params = {
        "action": "getPolicy",
        "model": model_name
    }

    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        raise Exception(f"Failed to get upload policy: {response.text}")

    return response.json()['data']


def upload_file_and_get_url(_api_key, _model_name, file_path):
    """上传文件并获取URL"""
    # 获取上传凭证，上传凭证接口有限流，超出限流将导致请求失败
    policy_data = get_upload_policy(_api_key, _model_name)
    # 上传文件到OSS
    oss_url = upload_file_to_oss(policy_data, file_path)
    # 打印结果
    _expire_time = datetime.now() + timedelta(hours=48)
    logger.info(f"✅ 文件上传成功，有效期48小时，过期时间: {_expire_time:%Y-%m-%d %H:%M:%S}")
    logger.info(f"临时URL: {oss_url}")

    return oss_url


def upload_file_to_my_gitee(file_path: str) -> str:
    """
    将文件上传到Gitee仓库并返回URL

    Args:
        file_path (str): 本地文件路径

    Returns:
        str: 文件的URL路径
    """

    logger.info("📋 初始化配置参数")
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../env/default.env"))

    gitee_token = os.getenv("GITEE_TOKEN")
    gitee_repo_owner = os.getenv("GITEE_REPO_OWNER")
    gitee_repo_name = os.getenv("GITEE_REPO_NAME")
    gitee_branch = os.getenv("GITEE_BRANCH")

    if not all([gitee_token, gitee_repo_owner, gitee_repo_name]):
        raise ValueError("缺少Gitee配置信息，请检查环境变量")

    # 获取文件名
    filename = os.path.basename(file_path)
    # 生成唯一文件名避免冲突
    import time
    unique_filename = f"{int(time.time())}_{filename}"

    # 读取文件内容并进行base64编码
    with open(file_path, "rb") as f:
        file_content = f.read()
    content = base64.b64encode(file_content).decode('utf-8')

    # Gitee API上传文件
    url = f"https://gitee.com/api/v5/repos/{gitee_repo_owner}/{gitee_repo_name}/contents/my_uploads/{unique_filename}"

    data = {
        "access_token": gitee_token,
        "content": content,
        "message": f"Upload file {filename}",
        "branch": gitee_branch
    }

    try:
        response = requests.post(url, json=data)
        response.raise_for_status()
        result = response.json()

        # 返回文件的可访问URL
        file_url = result.get("content", {}).get("download_url")
        if file_url:
            return file_url
        else:
            raise Exception("无法获取文件下载URL")

    except Exception as e:
        print(f"上传文件到Gitee失败: {e}")
        # 上传失败时返回本地文件路径作为备选方案
        return f"file://{file_path}"


def upload_file_to_oss(local_file_path: str, expire_time: int) -> str:
    """
    将本地文件上传到阿里云OSS，并返回带有效期的访问链接

    参数:
        local_file_path (str): 本地文件路径
        expire_time (int): 链接有效期（秒）
    返回:
        str: 带签名的可访问URL

    说明:
        - 你的生图流程可能需要开启系统/环境代理，但 OSS（国内）上传走代理时可能出现 ProxyError/Timeout。
        - 这里采用最小侵入方案：仅在本函数上传阶段临时设置 NO_PROXY/no_proxy，强制 OSS 直连。
    """


def upload_file_to_oss_dedup_with_meta(
    local_file_path: str,
    expire_time: int,
    object_prefix: str = "auto_uploads/by_hash",
) -> tuple[str, dict]:
    """上传文件到 OSS（按内容去重），并返回 (signed_url, meta)。

    meta 里包含：
    - sha256: 文件内容 hash
    - object_name: OSS 对象 key
    - action: "upload" | "reuse"

    注意：返回的 signed_url 每次都会变（Expires/Signature 不同），但 object_name 是稳定的。
    """

    def _merge_no_proxy(old_value: Optional[str], add_value: str) -> str:
        parts = [p.strip() for p in (old_value or "").split(",") if p.strip()]
        adds = [p.strip() for p in add_value.split(",") if p.strip()]
        merged = parts[:]
        for a in adds:
            if a and a not in merged:
                merged.append(a)
        return ",".join(merged)

    if not os.path.exists(local_file_path):
        logger.error(f"❌ 文件不存在: {local_file_path}")
        raise FileNotFoundError(f"文件不存在: {local_file_path}")

    # 计算文件内容 hash（流式，避免一次性读入内存）
    h = hashlib.sha256()
    with open(local_file_path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    digest = h.hexdigest()

    file_name = os.path.basename(local_file_path)
    object_name = f"{object_prefix}/{digest}_{file_name}"

    # ======== 1. OSS配置（需改成你自己的）========
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../env/default.env"))

    access_key_id = os.getenv("ALIYUN_ACCESS_KEY")
    access_key_secret = os.getenv("ALIYUN_ACCESS_SECRET")
    bucket_name = os.getenv("ALIYUN_BUCKET_NAME")
    endpoint = os.getenv("ALIYUN_BUCKET_ENDPORT")

    # ======== 2. 初始化bucket对象 ========
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # 仅对 OSS 上传阶段生效：强制直连（避免被 HTTP(S)_PROXY/ALL_PROXY 接管）
    old_np = os.environ.get("NO_PROXY")
    old_np_lower = os.environ.get("no_proxy")
    endpoint_host = urlparse(endpoint).hostname or ""
    add_np = ",".join([h for h in ["aliyuncs.com", endpoint_host] if h])
    if add_np:
        merged = _merge_no_proxy(old_np, add_np)
        os.environ["NO_PROXY"] = merged
        os.environ["no_proxy"] = merged

    action = "reuse"
    try:
        # 已存在则不重复上传
        if not bucket.object_exists(object_name):
            action = "upload"
            with open(local_file_path, "rb") as file_obj:
                bucket.put_object(object_name, file_obj)
            logger.info(f"✅ 文件上传oss成功(去重): {object_name}")
        else:
            logger.info(f"♻️ 复用已存在OSS对象(去重): {object_name}")
    finally:
        # 恢复环境变量，避免影响后续需要走代理的请求
        if old_np is None:
            os.environ.pop("NO_PROXY", None)
        else:
            os.environ["NO_PROXY"] = old_np
        if old_np_lower is None:
            os.environ.pop("no_proxy", None)
        else:
            os.environ["no_proxy"] = old_np_lower

    signed_url = bucket.sign_url("GET", object_name, expire_time)
    logger.info(f"🔗 访问链接: {signed_url}")

    meta = {
        "sha256": digest,
        "object_name": object_name,
        "action": action,
        "local_file_path": local_file_path,
    }

    return signed_url, meta


def upload_file_to_oss_dedup(local_file_path: str, expire_time: int, object_prefix: str = "auto_uploads/by_hash") -> str:
    """兼容旧接口：只返回 signed_url。"""
    signed_url, _meta = upload_file_to_oss_dedup_with_meta(local_file_path, expire_time, object_prefix)
    return signed_url

    def _merge_no_proxy(old_value: Optional[str], add_value: str) -> str:
        parts = [p.strip() for p in (old_value or "").split(",") if p.strip()]
        adds = [p.strip() for p in add_value.split(",") if p.strip()]
        merged = parts[:]
        for a in adds:
            if a and a not in merged:
                merged.append(a)
        return ",".join(merged)

    # ======== 1. OSS配置（需改成你自己的）========
    load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../env/default.env"))
    api_key = os.getenv("DASHSCOPE_API_KEY")

    access_key_id = os.getenv("ALIYUN_ACCESS_KEY")
    access_key_secret = os.getenv("ALIYUN_ACCESS_SECRET")
    bucket_name = os.getenv("ALIYUN_BUCKET_NAME")
    endpoint = os.getenv("ALIYUN_BUCKET_ENDPORT")

    # ======== 2. 初始化bucket对象 ========
    auth = oss2.Auth(access_key_id, access_key_secret)
    bucket = oss2.Bucket(auth, endpoint, bucket_name)

    # ======== 3. 自动生成唯一文件名 ========
    timestamp = int(time.time())
    file_name = os.path.basename(local_file_path)
    object_name = f"auto_uploads/{timestamp}_{file_name}"  # 存储到OSS的路径

    # ======== 4. 上传文件 ========
    if not os.path.exists(local_file_path):
        logger.error(f"❌ 文件不存在: {local_file_path}")
        raise FileNotFoundError(f"文件不存在: {local_file_path}")

    # 仅对 OSS 上传阶段生效：强制直连（避免被 HTTP(S)_PROXY/ALL_PROXY 接管）
    old_np = os.environ.get("NO_PROXY")
    old_np_lower = os.environ.get("no_proxy")
    endpoint_host = urlparse(endpoint).hostname or ""
    # aliyuncs.com 覆盖常见 OSS 域名；endpoint_host 覆盖你配置的具体节点/自定义域
    add_np = ",".join([h for h in ["aliyuncs.com", endpoint_host] if h])
    if add_np:
        merged = _merge_no_proxy(old_np, add_np)
        os.environ["NO_PROXY"] = merged
        os.environ["no_proxy"] = merged

    try:
        with open(local_file_path, "rb") as file_obj:
            bucket.put_object(object_name, file_obj)
    finally:
        # 恢复环境变量，避免影响后续需要走代理的请求
        if old_np is None:
            os.environ.pop("NO_PROXY", None)
        else:
            os.environ["NO_PROXY"] = old_np
        if old_np_lower is None:
            os.environ.pop("no_proxy", None)
        else:
            os.environ["no_proxy"] = old_np_lower

    # ======== 5. 生成带时效的访问链接 ========
    signed_url = bucket.sign_url('GET', object_name, expire_time)

    logger.info(f"✅ 文件上传oss成功: {object_name}")
    logger.info(f"🔗 访问链接: {signed_url}")

    return signed_url


# 使用示例
if __name__ == "__main__":
    # from config.logging_config import get_logger, setup_logging
    #
    # # 项目启动时初始化日志
    # setup_logging()
    # logger = get_logger(__name__)
    #
    # # 指定加载 env/default.env
    # load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../env/default.env"))
    # api_key = os.getenv("DASHSCOPE_API_KEY")  # 从环境变量读取
    #
    # # 设置model名称
    # model_name = "videoretalk"
    #
    # # 待上传的文件路径
    # file_path = "/Users/thomaschan/Code/Python/AI_vedio_demo/pythonProject/data/Data_results/video_results/my_video_7d390dfa-75cb-43aa-9d96-588fde858116.mp4"
    #
    # try:
    #     public_url = upload_file_and_get_url(api_key, model_name, file_path)
    #     expire_time = datetime.now() + timedelta(hours=48)
    #     logger.info(f"文件上传成功，有效期为48小时，过期时间: {expire_time.strftime('%Y-%m-%d %H:%M:%S')}")
    #     logger.info(f"临时URL: {public_url}")
    #
    # except Exception as e:
    #     logger.error(f"Error: {str(e)}")

    folder_path = "/Users/thomaschan/Code/Python/AI_vedio_demo/pythonProject/data/upload"  # 📁 需要上传的文件夹路径
    expire_time = 600  # ⏳ 链接有效期（秒）

    url_list = []

    # 遍历文件夹上传所有文件
    for file_name in os.listdir(folder_path):
        file_path = os.path.join(folder_path, file_name)
        if os.path.isfile(file_path):
            try:
                url = upload_file_to_oss(file_path, expire_time)
                url_list.append(url)

            except Exception as e:
                print(f"❌ 上传失败: {file_name} - {e}")

    for url in url_list:
        print(f"📡 {url}")

