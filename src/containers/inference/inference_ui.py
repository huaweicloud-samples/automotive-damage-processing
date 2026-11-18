"""
Inference UI（华为云适配版 · Streamlit）
========================================
流程：用户上传损伤图 + 填写基本信息 -> 多模态模型生成标准化元数据 -> 向量嵌入
      -> CSS 向量库 kNN 取 Top-K 相似历史案例 -> 按 Top-K 明文元数据算均价 -> 展示匹配图与估价。
实现要点：
  - 配置全部从环境变量读取（由 ConfigMap / Secret 注入）
  - 向量检索走 CSS（OpenSearch 引擎），HTTP basic auth
  - 模型调用统一走 model_adapter（MaaS 盘古）
  - 匹配图片从 OBS 公读地址加载
运行：CCE Deployment + Service（常驻），容器入口 `streamlit run inference_ui.py --server.port=8501`
"""

import os
import json
import base64
import requests
from requests.auth import HTTPBasicAuth
from io import BytesIO

import streamlit as st
from PIL import Image

from adapter.model_adapter import create_model_client

# ----------------------------------------------------------------------------
# 配置（运行期环境变量）
# ----------------------------------------------------------------------------
OS_HOST = os.environ["OS_HOST"]
OS_INDEX = os.environ.get("OS_INDEX", "repair-cost-data")
OS_USER = os.environ["OS_USER"]
OS_PASSWORD = os.environ["OS_PASSWORD"]
APP_BASE_URL = os.environ["APP_BASE_URL"]        # OBS 公读基址，如 https://<bucket>.obs.<region>.myhuaweicloud.com
CHAT_MODEL = os.environ.get("CHAT_MODEL", "pangu-nlp-2024-12")
EMBEDDING_MODEL = os.environ.get("EMBEDDING_MODEL", "pangu-embedding-v1")
MULTIMODAL = os.environ.get("MULTIMODAL_EMBEDDING", "false").lower() == "true"

adapter = create_model_client(provider="huaweicloud")

st.set_page_config(page_title="Damage Repair Cost Estimator")
st.title("Damage Repair Cost Estimator")

# ----------------------------------------------------------------------------
# UI 选项（车辆损伤维度枚举）
# ----------------------------------------------------------------------------
damage_area_options = ['Hood', 'Rear Left', 'Rear Right', 'Front Left', 'Front Right', 'Wheel', " Driver Side", 'Passenger Side', " Driver side Door", 'Passenger Side Door', "Windshield"]
damage_type_options = ['Scratch', 'Dent', 'Fender Bender', "Broken"]
damage_sev_option = ['light', 'moderate', 'severe', 'major']
options = ['Make_1', 'Make_2', 'Make_3']
selected = st.sidebar.selectbox('Select Car Make', options)
if "messages" not in st.session_state:
    st.session_state.messages = []
if selected == 'Make_1':
    second_options = ['Model_1']
elif selected == 'Make_2':
    second_options = ['Model_2']
else:
    second_options = ['Model_3']
selected_make = st.sidebar.selectbox('Second Make', second_options)
selected_damage_area = st.sidebar.multiselect('Damage Area:', damage_area_options)
selected_damage_type = st.sidebar.multiselect('Damage Type:', damage_type_options)
selected_damage_sev = st.sidebar.selectbox('Damage Severity', damage_sev_option)
matches = ['1', '2', '3']
number_of_matches = st.sidebar.selectbox('Number of matches (max 3)', matches)
if "uploader_key" not in st.session_state:
    st.session_state.uploader_key = 0
upload_file = st.sidebar.file_uploader("Upload your damage image", key=f"uploader_{st.session_state.uploader_key}")


def stream_cost_calc(invoke_body):
    """流式调用盘古生成估价说明（替代 invoke_model_with_response_stream）。"""
    st.write('**Streaming the Final Calculation**')
    for chunk in adapter.converse_stream(
        messages=invoke_body["messages"],
        model_id=CHAT_MODEL,
        inference_config={"maxTokens": 1000},
    ):
        if chunk.event_type == "contentBlockDelta" and chunk.delta and "text" in chunk.delta:
            yield chunk.delta["text"].replace("$", "\\$")


if upload_file is not None:
    st.session_state.uploader_key += 1
    file_bytes = upload_file.read()
    encoded_image = base64.b64encode(file_bytes).decode()
    file_extension = upload_file.name.lower().split('.')[-1]
    media_type = "image/png" if file_extension == "png" else "image/jpeg"

    json_text = {
        "make": selected, "model": selected_make, "state": "FL",
        "damage": selected_damage_area, "damage_severity": selected_damage_sev,
        "damage_type": selected_damage_type,
    }
    json_string = json.dumps(json_text)
    base64_string = base64.b64encode(json_string.encode('utf-8')).decode('utf-8')

    # 1) 对话模型生成损伤描述元数据（纯文本驱动：基于用户选择的参数，不传图片）
    json_model = ('<model>\
    {"make": "XXXXX", "model": "XXXXX", "state": "FL", "damage": "Front and Rear",\
    "damage_severity": "moderate", "damage_description": "Front and rear bumper cover repairs"}</model>')
    real_data_json = '<real_data>' + str(json_text) + '</real_data>'
    prompt_description = (json_model + real_data_json +
        'Instruction: You are a car damage assessor. Based on the real_data, populate the json output adding an extra field called damage_description, '
        'this description has to be short and less than 10 words, provide ONLY the json as a response and no other data, the xml tags also must not be in the response.')
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": prompt_description},
        ],
    }]
    resp = adapter.converse(messages=messages, model_id=CHAT_MODEL, inference_config={"maxTokens": 2000, "temperature": 1, "topP": 1, "topK": 250})
    text = resp.output["message"]["content"][0]["text"]
    json_bytes = json.dumps(text).encode('utf-8')
    encoded_json = base64.b64encode(json_bytes).decode('utf-8')

    # 2) 嵌入（默认仅文本；可选多模态）
    if MULTIMODAL:
        image_vector = adapter.embed_multimodal(image_b64=encoded_image, text=json_text, model_id=EMBEDDING_MODEL)
    else:
        image_vector = adapter.embed(content=json_text, model_id=EMBEDDING_MODEL, content_type="text")

    # 3) kNN 检索（CSS OpenSearch，basic auth）
    body = {"query": {"knn": {"damage_vector": {"vector": image_vector, "k": int(number_of_matches)}}}}
    url = f"https://{OS_HOST}/_search"
    r = requests.get(url, auth=HTTPBasicAuth(OS_USER, OS_PASSWORD),
                     params={"size": number_of_matches},
                     data=json.dumps(body),
                     headers={"Content-Type": "application/json; charset=utf-8"},
                     verify=False)  # CSS HTTPS 自签证书；opensearch-py 已关 verify，这里同步关
    results = r.json()
    num_results = len(results.get('hits', {}).get('hits', []))
    columns = st.columns(num_results + 1)
    metadata_strings = []
    with columns[0]:
        st.write('This is the Image that has been provided: ')
        st.image(file_bytes)
    for i, hit in enumerate(results.get('hits', {}).get('hits', [])):
        metadata = hit['_source']['metadata']
        obs_location = metadata['obs_location']
        score = hit['_score']
        metadata_strings.append(json.dumps(metadata, indent=2))
        with columns[i + 1]:
            img_url = f"{APP_BASE_URL.rstrip('/')}/{obs_location}"
            img_resp = requests.get(img_url)
            img = Image.open(BytesIO(img_resp.content))
            st.write(f'This is the Match Accuracy for Image {i + 1}: {score}')
            st.sidebar.write(f'Metadata for the closest match {i + 1}')
            st.sidebar.code(json.dumps(metadata, indent=2))
            st.image(img)

    # 4) 盘古基于 Top-K 元数据生成估价说明
    combined_metadata_string = '\n'.join(metadata_strings)
    prompt_full = ('<current>' + json_string + '</current>' + '<dataset>' + combined_metadata_string + '</dataset> '
        'Instruction; You are calculating the estimated repair cost based on previous data of similar car damages. '
        'Take the repair cost of the data set provide within <dataset> and calculate the average cost among all example data sets. '
        'Explain the math, but you must be brief, the answer cannot have more than 3 sentences.')
    invoke_body = {
        "messages": [{"role": "user", "content": [{"type": "text", "text": prompt_full}]}],
    }
    answer = st.write_stream(stream_cost_calc(invoke_body))
    st.session_state.messages.append({"role": "assistant", "content": answer})
