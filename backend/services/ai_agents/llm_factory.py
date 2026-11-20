"""LLM client factory hỗ trợ Google Gemini và OpenRouter (OpenAI-compatible).

Cho phép dùng một cấu hình thống nhất trong `backend/.env` (`LLM_PROVIDER=openrouter`
với các model đa phương thức & tool-calling như `qwen/qwen3.7-flash`) cho cả
`FitnessAdvisorAgent` (chat + tool calling) và `meal_vision` (nhận diện ảnh bữa ăn)
mà không cần cài thêm SDK ngoài `httpx` và `langchain_core`.
"""
from __future__ import annotations

import json
import uuid
from typing import Any, Sequence

import httpx
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.utils.function_calling import convert_to_openai_tool
from langchain_google_genai import ChatGoogleGenerativeAI

from core.config import settings


def _serialize_message(msg: BaseMessage) -> dict[str, Any]:
    """Chuyển LangChain Message sang định dạng OpenAI/OpenRouter Chat Completions."""
    if isinstance(msg, SystemMessage):
        return {"role": "system", "content": str(msg.content or "")}
    if isinstance(msg, ToolMessage):
        return {
            "role": "tool",
            "tool_call_id": str(getattr(msg, "tool_call_id", "") or ""),
            "content": str(msg.content or ""),
        }
    if isinstance(msg, AIMessage):
        payload: dict[str, Any] = {
            "role": "assistant",
            "content": str(msg.content or ""),
        }
        tcs = getattr(msg, "tool_calls", None) or []
        if tcs:
            payload["tool_calls"] = [
                {
                    "id": str(tc.get("id") or f"call_{uuid.uuid4().hex[:12]}"),
                    "type": "function",
                    "function": {
                        "name": str(tc.get("name") or ""),
                        "arguments": json.dumps(tc.get("args") or {}, ensure_ascii=False),
                    },
                }
                for tc in tcs
            ]
        return payload
    # HumanMessage hoặc message khác (hỗ trợ cả text lẫn danh sách phần tử ảnh image_url)
    content = msg.content
    if isinstance(content, list):
        parts: list[dict[str, Any]] = []
        for item in content:
            if isinstance(item, dict):
                parts.append(item)
            else:
                parts.append({"type": "text", "text": str(item)})
        return {"role": "user", "content": parts}
    return {"role": "user", "content": str(content or "")}


def _parse_tool_args(raw_args: Any) -> dict[str, Any]:
    if isinstance(raw_args, dict):
        return raw_args
    if isinstance(raw_args, str) and raw_args.strip():
        try:
            parsed = json.loads(raw_args)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


class OpenRouterChatModel:
    """Adapter tương thích `.bind_tools()` và `.ainvoke()` gọi OpenRouter Chat Completions."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        temperature: float = 0.3,
        reasoning_effort: str | None = None,
        tools: Sequence[dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> None:
        self.model = (model or settings.OPENROUTER_MODEL).strip()
        self.api_key = (api_key if api_key is not None else settings.OPENROUTER_API_KEY).strip()
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        self.temperature = temperature
        effort = settings.OPENROUTER_REASONING_EFFORT if reasoning_effort is None else reasoning_effort
        self.reasoning_effort = effort.strip() if effort else ""
        self._tools = list(tools) if tools else []
        self._tool_choice = tool_choice

    def bind_tools(
        self,
        tools: Sequence[Any],
        *,
        tool_choice: str | None = None,
        **_: Any,
    ) -> OpenRouterChatModel:
        converted = [
            t if isinstance(t, dict) and t.get("type") == "function" else convert_to_openai_tool(t)
            for t in tools
        ]
        choice = tool_choice
        if choice == "any":
            choice = "required"
        return OpenRouterChatModel(
            model=self.model,
            api_key=self.api_key,
            base_url=self.base_url,
            temperature=self.temperature,
            reasoning_effort=self.reasoning_effort,
            tools=converted,
            tool_choice=choice,
        )

    async def ainvoke(self, messages: Sequence[BaseMessage], **_: Any) -> AIMessage:
        if not self.api_key:
            raise RuntimeError("Thiếu OPENROUTER_API_KEY.")

        body: dict[str, Any] = {
            "model": self.model,
            "messages": [_serialize_message(m) for m in messages],
            "temperature": self.temperature,
        }
        if self.reasoning_effort:
            body["reasoning"] = {"effort": self.reasoning_effort, "exclude": True}
        if self._tools:
            body["tools"] = self._tools
            if self._tool_choice:
                body["tool_choice"] = self._tool_choice

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://fitai.local",
            "X-Title": settings.APP_NAME,
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError("OpenRouter không trả về lựa chọn phản hồi nào.")
        msg = choices[0].get("message") or {}
        text = str(msg.get("content") or "")
        raw_tcs = msg.get("tool_calls") or []
        parsed_tcs = [
            {
                "name": str((tc.get("function") or {}).get("name") or ""),
                "args": _parse_tool_args((tc.get("function") or {}).get("arguments")),
                "id": str(tc.get("id") or f"call_{i}"),
                "type": "tool_call",
            }
            for i, tc in enumerate(raw_tcs)
            if (tc.get("function") or {}).get("name")
        ]
        return AIMessage(content=text, tool_calls=parsed_tcs)


def build_chat_llm(*, temperature: float = 0.3) -> Any:
    """Trả về LLM client theo `settings.LLM_PROVIDER` ('openrouter' hoặc 'gemini')."""
    if settings.LLM_PROVIDER.strip().lower() == "openrouter":
        return OpenRouterChatModel(temperature=temperature)
    return ChatGoogleGenerativeAI(
        model=settings.GEMINI_MODEL,
        google_api_key=settings.GOOGLE_API_KEY,
        temperature=temperature,
        convert_system_message_to_human=True,
    )
