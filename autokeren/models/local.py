"""Local LLM model client (Ollama/LocalAI) supporting OpenAI completions schema."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from autokeren.models.base import Message, ModelResponse, TokenUsage, ToolCall


@dataclass
class LocalModel:
    model_id: str
    endpoint: str = "http://localhost:11434"
    timeout: float = 120.0
    auth_mode: str = "local"

    def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_retry: Callable[[int, float, str], None] | None = None,
        **params,
    ) -> ModelResponse:
        # Gunakan OpenAI-compatible endpoint di Ollama / LocalAI
        url = f"{self.endpoint.rstrip('/')}/v1/chat/completions"
        
        # Format messages ke format standard OpenAI
        openai_messages = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content")
            
            item: dict[str, Any] = {"role": role}
            if content is not None:
                item["content"] = content
            if msg.get("tool_calls"):
                item["tool_calls"] = msg.get("tool_calls")
            if role == "tool":
                item["tool_call_id"] = msg.get("tool_call_id")
                item["name"] = msg.get("name")
            openai_messages.append(item)

        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": openai_messages,
            "temperature": params.get("temperature", 0.3),
            "stream": on_chunk is not None,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        if on_chunk is not None:
            content_acc: list[str] = []
            tool_calls_map: dict[int, dict[str, Any]] = {}
            try:
                with httpx.stream("POST", url, json=payload, timeout=self.timeout) as r:
                    if r.status_code != 200:
                        raise RuntimeError(f"Local LLM API error: status {r.status_code}")
                    for line in r.iter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data_str = line[5:].strip()
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_str)
                            choice = chunk.get("choices", [{}])[0]
                            delta = choice.get("delta", {})
                            
                            # Content chunk
                            text = delta.get("content") or ""
                            if text:
                                on_chunk(text)
                                content_acc.append(text)
                                
                            # Tool calls chunk
                            tcs = delta.get("tool_calls") or []
                            for tc in tcs:
                                idx = tc.get("index", 0)
                                if idx not in tool_calls_map:
                                    tool_calls_map[idx] = {"id": tc.get("id"), "name": "", "arguments": ""}
                                if tc.get("id"):
                                    tool_calls_map[idx]["id"] = tc.get("id")
                                fn = tc.get("function") or {}
                                if fn.get("name"):
                                    tool_calls_map[idx]["name"] = fn.get("name")
                                if fn.get("arguments"):
                                    tool_calls_map[idx]["arguments"] += fn.get("arguments")
                        except Exception:
                            continue
            except Exception as e:
                raise RuntimeError(f"Local LLM streaming error: {e}") from e

            # Parse accumulated tool calls
            tool_calls = []
            for idx, tc in sorted(tool_calls_map.items()):
                try:
                    args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                except Exception:
                    args = {"raw": tc["arguments"]}
                tool_calls.append(ToolCall(id=tc["id"] or f"call_{idx}", name=tc["name"], arguments=args))

            return ModelResponse(
                content="".join(content_acc) if content_acc else None,
                tool_calls=tool_calls,
                model_id=self.model_id,
            )
        else:
            try:
                r = httpx.post(url, json=payload, timeout=self.timeout)
                if r.status_code != 200:
                    raise RuntimeError(f"Local LLM API error: status {r.status_code}, response: {r.text}")
                data = r.json()
            except Exception as e:
                raise RuntimeError(f"Local LLM request failed: {e}") from e

            choice = data.get("choices", [{}])[0]
            message = choice.get("message", {})
            content = message.get("content")
            
            tool_calls = []
            for tc in message.get("tool_calls", []):
                fn = tc.get("function", {})
                try:
                    args = json.loads(fn.get("arguments", "{}"))
                except Exception:
                    args = {"raw": fn.get("arguments")}
                tool_calls.append(ToolCall(
                    id=tc.get("id", "call_0"),
                    name=fn.get("name", ""),
                    arguments=args,
                ))

            usage_data = data.get("usage", {})
            usage = TokenUsage(
                prompt=usage_data.get("prompt_tokens", 0),
                completion=usage_data.get("completion_tokens", 0),
                total=usage_data.get("total_tokens", 0),
            )

            return ModelResponse(
                content=content,
                tool_calls=tool_calls,
                usage=usage,
                model_id=self.model_id,
            )
