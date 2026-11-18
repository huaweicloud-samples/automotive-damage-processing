"""
Ingestion 灌库任务（华为云适配版）
================================
流程：OBS 源桶取图 -> 多模态模型抽取标准化元数据 -> 向量嵌入 -> 写入 CSS 向量库；原图落 OBS 展示桶。
实现要点：
  - 配置全部从环境变量读取（由 ConfigMap / Secret 注入）
  - 对象存储用 OBS（src/adapter/obs_client.py）
  - 向量库用 CSS OpenSearch（basic auth，src/adapter/opensearch_client.py）
  - 模型调用统一走 model_adapter（MaaS 盘古），嵌入默认仅文本向量（可切多模态）
运行方式：CCE Job（一次性），或本地 `python image_ingestion.py`
"""

import os
import json
import base64
from datetime import datetime

from adapter.model_adapter import create_model_client
from adapter.obs_client import list_image_keys, get_object_bytes, put_object
from adapter.opensearch_client import get_client, ensure_index

# ----------------------------------------------------------------------------
# 配置（统一从环境变量读取）
# ----------------------------------------------------------------------------
OS_HOST = os.environ["OS_HOST"]                       # CSS 公网域名（不含 https://）
OS_INDEX = os.environ.get("OS_INDEX", "repair-cost-data")
OS_DIM = int(os.environ.get("EMBEDDING_DIM", "1024"))  # 须与嵌入模型输出维度一致
OBS_BUCKET = os.environ["OBS_BUCKET"]                 # 前端展示桶
OBS_BUCKET_SOURCE = os.environ["OBS_BUCKET_SOURCE"]   # 灌库源桶
OBS_FOLDER = os.environ.get("OBS_FOLDER", "repair-data/")
CHAT_MODEL = os.environ.get("CHAT_MODEL", "pangu-nlp-2024-12")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "pangu-embedding-v1")
MULTIMODAL = os.environ.get("MULTIMODAL_EMBEDDING", "false").lower() == "true"

adapter = create_model_client(provider="huaweicloud")

# 三种虚构车型指令（用于演示元数据标准化）
INSTRUCTION_MODEL_1 = ('Instruction: You are a damage repair cost estimator and you need to create a json output as close as possible to the <model>, '
    'you need to estimate the repair cost to populate within the output and you need to provide the damage_severity according to the <criteria>, '
    'you also need to provide a damage_description which is short and less than 10 words. Just provide the json output in the response, do not explain the reasoning. '
    'For testing purposes assume the vehicle is from a fictitious car brand "Make_1" and a ficticious model "Model_1" in the state of Florida.')

INSTRUCTION_MODEL_2 = INSTRUCTION_MODEL_1.replace('Make_1', 'Make_2').replace('Model_1', 'Model_2')
INSTRUCTION_MODEL_3 = INSTRUCTION_MODEL_1.replace('Make_1', 'Make_3').replace('Model_1', 'Model_3')

JSON_MODEL = ('<model>\
    {\
        "make": "XXXX",\
        "model": "XXXX",\
        "year": XXXX,\
        "state": "XX",\
        "damage": "Right Front",\
        "repair_cost": XXXXX,\
        "damage_severity": "moderate",\
        "damage_description": "Dent and scratches on the right fender",\
        "parts_for_repair": "add a list of parts that need to be replaced/repaired",\
        "labor_hours": XX,\
        "parts_cost": XXXX,\
        "labor_cost"\
      }\
    </model>')

CRITERIA_COST = ('<criteria> \
    repair_cost < 500 = light \
    repair_cost > 500 AND < 1000 = moderate \
    repair_cost > 1000 AND < 2000 = severe \
    repair_cost > 2000 = major \
    </criteria>')


def _media_type(file_key):
    ext = file_key.lower().split('.')[-1]
    if ext in ('jpg', 'jpeg'):
        return "image/jpeg"
    if ext == 'png':
        return "image/png"
    return "image/jpeg"


# 对话模型为纯文本（如 DeepSeek 系列），不接收图片：
# 按序号轮询构造损伤场景，由模型基于场景文本生成标准化 JSON 元数据（无图像信息，演示用）。
DAMAGE_TYPES = ['Scratch', 'Dent', 'Fender Bender', 'Broken']
SEVERITIES = ['light', 'moderate', 'severe', 'major']


def create_metadata(idx, instruction):
    """调用对话模型，基于场景文本生成标准化 JSON 元数据（纯文本，不含图片）。"""
    print('[ingest] 请求大模型生成元数据（文本驱动）')
    dmg = DAMAGE_TYPES[idx % len(DAMAGE_TYPES)]
    sev = SEVERITIES[(idx // len(DAMAGE_TYPES)) % len(SEVERITIES)]
    scenario = (f'\nScenario: the vehicle has a "{dmg}" damage with "{sev}" severity. '
                'Populate the json output accordingly and provide damage_description (<= 10 words).')
    prompt = CRITERIA_COST + JSON_MODEL + instruction + scenario
    messages = [{"role": "user", "content": [{"type": "text", "text": prompt}]}]
    resp = adapter.converse(
        messages=messages,
        model_id=CHAT_MODEL,
        inference_config={"maxTokens": 2000, "temperature": 1, "topP": 1, "topK": 250},
    )
    text = resp.output["message"]["content"][0]["text"]
    print('[ingest] 元数据生成完成')
    return text


def index_data(client, image_vector, metadata):
    print('[ingest] 写入向量文档')
    client.index(index=OS_INDEX, body={"damage_vector": image_vector, "metadata": metadata})


def ingest_image(client, items, instruction):
    """items: list of (file_key, file_binary)"""
    for idx, (file_key, file_binary) in enumerate(items):
        encoded_image = base64.b64encode(file_binary).decode('utf-8')
        json_text = create_metadata(idx, instruction)
        data = json.loads(json_text)

        # 原图存入 OBS 前端展示桶
        key = OBS_FOLDER + file_key
        put_object(OBS_BUCKET, key, file_binary)

        # 嵌入：默认仅文本向量；可选多模态
        if MULTIMODAL:
            print('[ingest] 多模态嵌入（图+文）')
            image_vector = adapter.embed_multimodal(image_b64=encoded_image, text=json_text, model_id=EMBEDDING_MODEL)
        else:
            print('[ingest] 文本嵌入（仅元数据）')
            image_vector = adapter.embed(content=json_text, model_id=EMBEDDING_MODEL, content_type="text")

        data["obs_location"] = key
        index_data(client, image_vector, data)


def batch(items, start, end):
    return list(items.items())[start:end]


def main():
    client = get_client()
    ensure_index(client, OS_INDEX, OS_DIM)

    print(f"[ingest] 列出源桶 {OBS_BUCKET_SOURCE} 图片")
    keys = list_image_keys(OBS_BUCKET_SOURCE)
    contents = {k: get_object_bytes(OBS_BUCKET_SOURCE, k) for k in keys if k.lower().endswith(('.jpg', '.jpeg', '.png'))}
    print(f"[ingest] 共 {len(contents)} 张图片")

    n = len(contents)
    cut1, cut2 = max(1, n // 3), max(2, 2 * n // 3)
    ingest_image(client, batch(contents, 0, cut1), INSTRUCTION_MODEL_1)
    ingest_image(client, batch(contents, cut1, cut2), INSTRUCTION_MODEL_2)
    ingest_image(client, batch(contents, cut2, n), INSTRUCTION_MODEL_3)
    print('[ingest] 灌库完成')


if __name__ == "__main__":
    start = datetime.now()
    print("Start:", start)
    main()
    end = datetime.now()
    print(f"Start {start} - End {end}")
