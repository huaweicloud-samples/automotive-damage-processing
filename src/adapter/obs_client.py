"""
OBS 对象存储客户端
依赖：pip install esdk-obs-python
凭据：环境变量 HW_ACCESS_KEY / HW_SECRET_KEY（不硬编码）
"""
import os
from obs import ObsClient


def _server():
    region = os.environ.get("REGION", "cn-north-4")
    return f"https://obs.{region}.myhuaweicloud.com"


def get_client():
    return ObsClient(
        access_key_id=os.environ["HW_ACCESS_KEY"],
        secret_access_key=os.environ["HW_SECRET_KEY"],
        server=_server(),
    )


def list_image_keys(bucket, prefix=""):
    cli = get_client()
    keys, marker = [], None
    while True:
        resp = cli.listObjects(bucketName=bucket, prefix=prefix, marker=marker or "")
        if resp.status >= 300 or resp.body is None:
            break
        for it in resp.body.contents:
            keys.append(it.key)
        if getattr(resp.body, "isTruncated", False):
            marker = resp.body.nextMarker
        else:
            break
    return keys


def get_object_bytes(bucket, key):
    cli = get_client()
    # 新版 esdk-obs-python：loadStreamInMemory=True 时内容在 resp.body.buffer（字节）
    resp = cli.getObject(bucketName=bucket, objectKey=key, loadStreamInMemory=True)
    if resp.status >= 300 or resp.body is None:
        return None
    return resp.body.buffer


def put_object(bucket, key, data):
    cli = get_client()
    resp = cli.putObject(bucketName=bucket, objectKey=key, content=data)
    return resp.status < 300
