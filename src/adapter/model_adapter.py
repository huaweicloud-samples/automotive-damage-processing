"""
automotive-damage-processing · 华为云模型抽象层
================================================

把多模态对话与向量嵌入两类模型能力收敛到统一抽象接口，
底层走华为云 MaaS（ModelArts Studio）OpenAI 兼容端点。

对外接口：
    ModelProvider.converse()                     多模态对话（图 + 文 -> 结构化元数据）
    ModelProvider.embed() / embed_multimodal()   文本 / 多模态向量嵌入

依赖：pip install openai
凭据：从环境变量读取（不硬编码），见 response-constraints / deployment-guide。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Iterator
import json
import base64
import os


# ============================================================================
# 数据结构（统一的多轮对话消息模型，供上层业务代码直接使用）
# ============================================================================

class StopReason(str, Enum):
    END_TURN = "end_turn"
    TOOL_USE = "tool_use"
    MAX_TOKENS = "max_tokens"
    STOP_SEQUENCE = "stop_sequence"
    GUARDRAIL_INTERVENED = "guardrail_intervened"


@dataclass
class ConverseResponse:
    output: dict
    stop_reason: str
    usage: dict
    metrics: dict = None


@dataclass
class ConverseStreamChunk:
    event_type: str
    delta: dict = None
    stop_reason: str = None
    usage: dict = None


# ============================================================================
# 抽象接口
# ============================================================================

class ModelProvider(ABC):

    @abstractmethod
    def converse(self, messages, model_id, system=None, inference_config=None, **kw) -> ConverseResponse: ...

    @abstractmethod
    def converse_stream(self, messages, model_id, system=None, inference_config=None, **kw) -> Iterator[ConverseStreamChunk]: ...

    @abstractmethod
    def embed(self, content, model_id, content_type="text") -> list[float]: ...

    @abstractmethod
    def embed_multimodal(self, image_b64, text, model_id) -> list[float]: ...


# ============================================================================
# 华为云适配器（MaaS / ModelArts Studio，OpenAI 兼容）
# ============================================================================

class HuaweiCloudAdapter(ModelProvider):
    """
    将统一对话请求翻译为 OpenAI 兼容格式，调用华为云 MaaS 大模型服务。

    - 对话（chat）：base_url 取 MAAS_CHAT_BASE_URL（如 https://api.modelarts-maas.com/v2）
    - 嵌入（embedding）：base_url 取 MAAS_EMBED_BASE_URL（如 https://api.modelarts-maas.com/v1）
      （两个端点的 API 版本可能不同，因此各持一个 client，不能共用）

    视觉支持：
    - 默认 VISION_ENABLED=false（纯文本对话模型，如 DeepSeek 系列），消息中的
      image block 会被忽略，仅保留 text；上层业务据此改用元数据文本驱动。
    - VISION_ENABLED=true（多模态模型）时正常携带 image_url。
    """

    def __init__(self, region=None, api_key=None, base_url=None,
                 chat_base_url=None, embed_base_url=None, multimodal_model=None):
        self.region = region or os.environ.get("REGION", "cn-north-4")
        self.api_key = api_key or os.environ.get("MAAS_API_KEY", "")
        self.chat_base_url = (chat_base_url or base_url
                              or os.environ.get("MAAS_CHAT_BASE_URL",
                                                f"https://maas.{self.region}.myhuaweicloud.com/v1"))
        self.embed_base_url = (embed_base_url or base_url
                               or os.environ.get("MAAS_EMBED_BASE_URL", self.chat_base_url))
        self.multimodal_model = multimodal_model or os.environ.get("MULTIMODAL_MODEL", "pangu-multimodal-v1")
        self.vision_enabled = os.environ.get("VISION_ENABLED", "false").lower() == "true"
        from openai import OpenAI
        self._chat_client = OpenAI(base_url=self.chat_base_url, api_key=self.api_key)
        self._embed_client = OpenAI(base_url=self.embed_base_url, api_key=self.api_key)

    # ------------------------------------------------------------------ #
    # 同步对话
    # ------------------------------------------------------------------ #
    def converse(self, messages, model_id, system=None, inference_config=None, **kw) -> ConverseResponse:
        openai_messages = self._to_openai_messages(messages, system)
        req = {"model": model_id, "messages": openai_messages}
        if inference_config:
            if "maxTokens" in inference_config:
                req["max_tokens"] = inference_config["maxTokens"]
            if "temperature" in inference_config:
                req["temperature"] = inference_config["temperature"]
            if "topP" in inference_config:
                req["top_p"] = inference_config["topP"]
            # 注意：MaaS OpenAI 兼容端点不支持 top_k（OpenAI 标准无此参数），忽略
        resp = self._chat_client.chat.completions.create(**req)
        choice = resp.choices[0]
        blocks = []
        if choice.message.content:
            blocks.append({"text": choice.message.content})
        return ConverseResponse(
            output={"message": {"role": "assistant", "content": blocks}},
            stop_reason="end_turn",
            usage={"input_tokens": getattr(resp.usage, "prompt_tokens", 0) or 0,
                   "output_tokens": getattr(resp.usage, "completion_tokens", 0) or 0},
        )

    # ------------------------------------------------------------------ #
    # 流式对话
    # ------------------------------------------------------------------ #
    def converse_stream(self, messages, model_id, system=None, inference_config=None, **kw) -> Iterator[ConverseStreamChunk]:
        openai_messages = self._to_openai_messages(messages, system)
        req = {"model": model_id, "messages": openai_messages, "stream": True,
               "stream_options": {"include_usage": True}}
        if inference_config and "maxTokens" in inference_config:
            req["max_tokens"] = inference_config["maxTokens"]
        stream = self._chat_client.chat.completions.create(**req)
        for chunk in stream:
            if not chunk.choices:
                if chunk.usage:
                    yield ConverseStreamChunk(event_type="metadata",
                                             usage={"input_tokens": chunk.usage.prompt_tokens,
                                                    "output_tokens": chunk.usage.completion_tokens})
                continue
            delta = chunk.choices[0].delta
            if delta.role == "assistant" and not delta.content:
                yield ConverseStreamChunk(event_type="messageStart", delta={"role": "assistant"})
                continue
            if delta.content:
                yield ConverseStreamChunk(event_type="contentBlockDelta", delta={"text": delta.content})
            fr = chunk.choices[0].finish_reason
            if fr:
                yield ConverseStreamChunk(event_type="messageStop", stop_reason="end_turn")

    # ------------------------------------------------------------------ #
    # 文本嵌入
    # ------------------------------------------------------------------ #
    def embed(self, content, model_id, content_type="text") -> list[float]:
        if content_type == "text":
            resp = self._embed_client.embeddings.create(model=model_id, input=content)
            return resp.data[0].embedding
        # 图像：降级为 描述 -> 文本嵌入
        return self.embed_multimodal(image_b64=content if isinstance(content, str) else base64.b64encode(content).decode(),
                                     text="", model_id=model_id)

    # ------------------------------------------------------------------ #
    # 多模态嵌入（钩子）
    #   默认实现：多模态 chat 生成图描述 -> 文本嵌入（方案 C）。
    #   若 MaaS 已上线「图像+文本联合嵌入」模型，可在此直连该端点（方案 B）。
    # ------------------------------------------------------------------ #
    def embed_multimodal(self, image_b64, text, model_id) -> list[float]:
        if text:
            prompt = ("请基于这张车辆损伤图片和以下结构化信息，生成一段用于语义检索的简洁中文描述："
                      f"\n{text}\n只输出描述文本，不要解释。")
        else:
            prompt = "请描述这张车辆损伤图片的内容，用于后续语义检索。只输出描述文本。"
        desc = self._describe_image(image_b64, prompt)
        resp = self._embed_client.embeddings.create(model=model_id, input=desc)
        return resp.data[0].embedding

    def _describe_image(self, image_b64, prompt) -> str:
        content = [{"type": "text", "text": prompt}]
        if self.vision_enabled:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}})
        resp = self._chat_client.chat.completions.create(
            model=self.multimodal_model,
            messages=[{"role": "user", "content": content}])
        return resp.choices[0].message.content or ""

    # ------------------------------------------------------------------ #
    # 统一消息模型 -> OpenAI messages
    # ------------------------------------------------------------------ #
    def _to_openai_messages(self, messages, system=None) -> list[dict]:
        out = []
        if system:
            out.append({"role": "system", "content": system})
        for msg in messages:
            role = msg["role"]
            blocks = msg.get("content", [])
            if isinstance(blocks, str):
                out.append({"role": role, "content": blocks})
                continue
            parts = []
            for b in blocks:
                if "text" in b:
                    parts.append({"type": "text", "text": b["text"]})
                elif "image" in b:
                    if not self.vision_enabled:
                        # 纯文本模型：忽略图片 block（上层业务用元数据文本驱动）
                        continue
                    img = b["image"]
                    fmt = img.get("format", "jpeg")
                    src = img.get("source", {})
                    data = src.get("data", "") or src.get("bytes", "")
                    if isinstance(data, bytes):
                        data = base64.b64encode(data).decode()
                    parts.append({"type": "image_url",
                                  "image_url": {"url": f"data:image/{fmt};base64,{data}"}})
            if not parts:
                parts.append({"type": "text", "text": ""})
            out.append({"role": role, "content": parts if len(parts) > 1 else (parts[0]["text"] if parts else "")})
        return out


# ============================================================================
# 工厂
# ============================================================================

def create_model_client(provider="huaweicloud", **kw) -> ModelProvider:
    if provider == "huaweicloud":
        return HuaweiCloudAdapter(**kw)
    raise ValueError(f"Unsupported provider: {provider}")
