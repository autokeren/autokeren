"""Cloudflare Workers AI inference client."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable

import httpx

from autokeren.models.base import Message, ModelResponse, TokenUsage, ToolCall
from autokeren.models.retry import RetryPolicy, retry_call

_PLATFORM_MODEL_MAP: dict[str, str] = {
    "@cf/moonshotai/kimi-k2.7-code": "kimi-code",
    "@cf/moonshotai/kimi-k2.6": "kimi-2.6",
    "@cf/zai-org/glm-5.2": "glm-5.2",
    "@cf/zai-org/glm-4.7-flash": "glm-flash",
    "@cf/meta/llama-4-scout-17b-16e-instruct": "llama-4-scout",
    "@cf/google/gemma-4-26b-a4b-it": "gemma-4",
    "@cf/nvidia/nemotron-3-120b-a12b": "nemotron",
}


def resolve_model_id(model_id: str, auth_mode: str) -> str:
    """Map @cf/... model IDs to platform aliases when in platform mode."""
    if auth_mode != "platform":
        return model_id
    if not model_id.startswith("@cf/"):
        return model_id
    return _PLATFORM_MODEL_MAP.get(model_id, "kimi-2.6")


def fetch_available_models(cfg) -> list[dict[str, Any]]:
    """Fetch model list dari API. Return list of {id, name, provider, tier, context, desc, icon}.

    Platform mode: GET {base_url}/v1/models (public, no auth needed)
    Direct mode: return hardcoded list dari _PLATFORM_MODEL_MAP keys
    """
    if cfg.auth.mode == "platform":
        try:
            url = f"{cfg.auth.base_url}/v1/models"
            resp = httpx.get(url, timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                return data.get("data", [])
        except Exception:
            pass

    return [
        {"id": mid, "name": alias, "provider": "Cloudflare", "tier": "direct", "context": 0, "desc": "", "icon": ""}
        for mid, alias in _PLATFORM_MODEL_MAP.items()
    ]


def _extract_partial_args(raw: str) -> dict[str, Any]:
    """Extract partial arguments from truncated JSON (e.g. when max_tokens cut off tool call).

    Tries complete JSON parse first, then falls back to per-key extraction
    that handles truncated string values.
    """
    import re

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        pass

    result: dict[str, Any] = {}

    _SHORT_KEYS = ("path", "project_id", "file_path", "name", "description", "message", "old_string")
    _LONG_KEYS = ("content", "script", "command", "new_string")

    for key in _SHORT_KEYS:
        m = re.search(rf'"{key}"\s*:\s*"((?:[^"\\]|\\.)*)"', raw)
        if m:
            try:
                result[key] = json.loads(f'"{m.group(1)}"')
            except Exception:
                result[key] = m.group(1)

    for key in _LONG_KEYS:
        m = re.search(rf'"{key}"\s*:\s*"', raw)
        if not m:
            continue
        content_raw = raw[m.end():]
        while content_raw and content_raw[-1] in ('"', "}", " ", "\n", "\r", "\t"):
            content_raw = content_raw[:-1]
        if content_raw.endswith("\\"):
            content_raw = content_raw[:-1]
        try:
            result[key] = json.loads(f'"{content_raw}"')
        except Exception:
            result[key] = (
                content_raw.replace("\\n", "\n")
                .replace("\\t", "\t")
                .replace('\\"', '"')
                .replace("\\\\", "\\")
            )

    return result


class CloudflareAIError(Exception):
    def __init__(self, message: str, status: int | None = None, response: dict | None = None):
        super().__init__(message)
        self.status = status
        self.response = response or {}


@dataclass
class CloudflareModel:
    account_id: str
    api_token: str = field(repr=False)
    model_id: str
    base_url: str = "https://api.cloudflare.com/client/v4"
    timeout: float = 120.0
    retry_policy: RetryPolicy | None = None
    auth_mode: str = "direct"
    api_key: str = field(default="", repr=False)

    def _endpoint(self) -> str:
        return f"{self.base_url}/accounts/{self.account_id}/ai/run/{self.model_id}"

    def _openai_endpoint(self) -> str:
        if self.auth_mode == "platform":
            return f"{self.base_url}/v1/chat/completions"
        return f"{self.base_url}/accounts/{self.account_id}/ai/v1/chat/completions"

    def _headers(self) -> dict[str, str]:
        token = self.api_key if self.auth_mode == "platform" else self.api_token
        return {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_config(cls, cfg) -> "CloudflareModel":
        if cfg.auth.mode == "platform":
            return cls(
                account_id="",
                api_token="",
                api_key=cfg.auth.api_key,
                model_id=resolve_model_id(cfg.cloudflare.primary_model, "platform"),
                base_url=cfg.auth.base_url,
                timeout=cfg.cloudflare.timeout,
                auth_mode="platform",
                retry_policy=RetryPolicy(
                    max_retries=cfg.retry.max_retries,
                    base_delay=cfg.retry.base_delay,
                    max_delay=cfg.retry.max_delay,
                    exponential_base=cfg.retry.exponential_base,
                    jitter=cfg.retry.jitter,
                ),
            )
        return cls(
            account_id=cfg.cloudflare.account_id or "",
            api_token=cfg.cloudflare.api_token or "",
            model_id=cfg.cloudflare.primary_model,
            timeout=cfg.cloudflare.timeout,
            retry_policy=RetryPolicy(
                max_retries=cfg.retry.max_retries,
                base_delay=cfg.retry.base_delay,
                max_delay=cfg.retry.max_delay,
                exponential_base=cfg.retry.exponential_base,
                jitter=cfg.retry.jitter,
            ),
        )

    def _call_once(self, messages: list[Message], tools: list[dict] | None = None, **params) -> ModelResponse:
        if self.auth_mode == "platform":
            return self._call_once_openai(messages, tools=tools, **params)
        payload = {
            "messages": messages,
            "max_tokens": params.get("max_tokens", 4096),
            "temperature": params.get("temperature", 0.3),
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            r = httpx.post(
                self._endpoint(),
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as e:
            raise CloudflareAIError("request timeout", status=None) from e
        except httpx.ConnectError as e:
            raise CloudflareAIError(f"connection error: {e}", status=None) from e

        try:
            data = r.json()
        except Exception as e:
            raise CloudflareAIError(f"invalid json: {r.text[:200]}", status=r.status_code) from e

        if r.status_code != 200 or not data.get("success"):
            errors = data.get("errors", [data.get("message", "unknown error")])
            raise CloudflareAIError(
                f"Workers AI error: {errors}",
                status=r.status_code,
                response=data,
            )

        result = data.get("result", {})
        return self._parse_response(result)

    def _call_once_openai(self, messages: list[Message], tools: list[dict] | None = None, **params) -> ModelResponse:
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": params.get("max_tokens", 8192),
            "temperature": params.get("temperature", 0.3),
            "stream": False,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"
        try:
            r = httpx.post(
                self._openai_endpoint(),
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as e:
            raise CloudflareAIError("request timeout", status=None) from e
        except httpx.ConnectError as e:
            raise CloudflareAIError(f"connection error: {e}", status=None) from e

        try:
            data = r.json()
        except Exception as e:
            raise CloudflareAIError(f"invalid json: {r.text[:200]}", status=r.status_code) from e

        if r.status_code != 200:
            err_msg = data.get("error", {}).get("message", str(data)) if isinstance(data.get("error"), dict) else str(data)
            raise CloudflareAIError(f"API error: {err_msg}", status=r.status_code, response=data)

        return self._parse_openai_response(data, r.headers)

    def _parse_response(self, result: dict[str, Any]) -> ModelResponse:
        usage = TokenUsage(
            prompt=result.get("usage", {}).get("prompt_tokens", 0),
            completion=result.get("usage", {}).get("completion_tokens", 0),
            total=result.get("usage", {}).get("total_tokens", 0),
        )
        choice = result.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content")
        tool_calls = []
        for tc in message.get("tool_calls", []) or []:
            try:
                args = json.loads(tc.get("function", {}).get("arguments", "{}"))
            except Exception:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("function", {}).get("name", ""),
                    arguments=args,
                )
            )
        return ModelResponse(
            content=content or ("" if tool_calls else None),
            tool_calls=tool_calls,
            usage=usage,
            model_id=self.model_id,
            finish_reason=choice.get("finish_reason"),
            raw=result,
        )

    def _parse_openai_response(self, data: dict[str, Any], headers: Any = None) -> ModelResponse:
        usage_data = data.get("usage", {})
        usage = TokenUsage(
            prompt=usage_data.get("prompt_tokens", 0),
            completion=usage_data.get("completion_tokens", 0),
            total=usage_data.get("total_tokens", 0),
        )
        choices = data.get("choices", [])
        choice = choices[0] if choices else {}
        message = choice.get("message", {})
        content = message.get("content")
        tool_calls = []
        for tc in message.get("tool_calls", []) or []:
            raw_args = tc.get("function", {}).get("arguments", "{}")
            try:
                args = json.loads(raw_args)
            except json.JSONDecodeError:
                args = _extract_partial_args(raw_args)
            tool_calls.append(
                ToolCall(
                    id=tc.get("id", ""),
                    name=tc.get("function", {}).get("name", ""),
                    arguments=args,
                )
            )
        neurons_used = 0
        neurons_remaining = None
        neurons_quota = None
        if headers:
            try:
                neurons_used = int(headers.get("X-Neurons-Used", 0))
                neurons_remaining = int(headers.get("X-Neurons-Remaining")) if headers.get("X-Neurons-Remaining") else None
                neurons_quota = int(headers.get("X-Neurons-Quota")) if headers.get("X-Neurons-Quota") else None
            except (ValueError, TypeError):
                pass

        return ModelResponse(
            content=content or ("" if tool_calls else None),
            tool_calls=tool_calls,
            usage=usage,
            model_id=data.get("model", self.model_id),
            finish_reason=choice.get("finish_reason"),
            raw=data,
            neurons_used=neurons_used,
            neurons_remaining=neurons_remaining,
            neurons_quota=neurons_quota,
        )

    def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        **params,
    ) -> ModelResponse:
        policy = self.retry_policy or RetryPolicy()

        def _call():
            if on_chunk is not None:
                try:
                    return self._stream_once(messages, tools=tools, on_chunk=on_chunk, **params)
                except CloudflareAIError:
                    raise
            return self._call_once(messages, tools=tools, **params)

        return retry_call(_call, policy)

    def _stream_once(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        **params,
    ) -> ModelResponse:
        """Streaming via OpenAI-compatible endpoint. Supports text + tool_calls SSE."""
        payload: dict[str, Any] = {
            "model": self.model_id,
            "messages": messages,
            "max_tokens": params.get("max_tokens", 8192),
            "temperature": params.get("temperature", 0.3),
            "stream": True,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = "auto"

        full_text = ""
        tc_acc: dict[int, dict[str, str]] = {}
        usage = TokenUsage()

        try:
            with httpx.stream(
                "POST",
                self._openai_endpoint(),
                headers=self._headers(),
                json=payload,
                timeout=self.timeout,
            ) as r:
                if r.status_code != 200:
                    body = r.read().decode("utf-8", errors="replace")[:500]
                    raise CloudflareAIError(f"stream error: {body}", status=r.status_code)

                for line in r.iter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    raw = line[6:]
                    if raw.strip() == "[DONE]":
                        break
                    try:
                        chunk = json.loads(raw)
                    except json.JSONDecodeError:
                        continue

                    choices = chunk.get("choices", [])
                    if not choices:
                        continue
                    delta = choices[0].get("delta", {})

                    text = delta.get("content", "")
                    if text:
                        full_text += text
                        if on_chunk:
                            on_chunk(text)

                    for tc_delta in delta.get("tool_calls", []) or []:
                        idx = tc_delta.get("index", 0)
                        if idx not in tc_acc:
                            tc_acc[idx] = {"id": "", "name": "", "arguments": ""}
                        if tc_delta.get("id"):
                            tc_acc[idx]["id"] = tc_delta["id"]
                        func = tc_delta.get("function", {})
                        if func.get("name"):
                            tc_acc[idx]["name"] = func["name"]
                        if func.get("arguments"):
                            tc_acc[idx]["arguments"] += func["arguments"]

                    u = chunk.get("usage")
                    if u:
                        usage = TokenUsage(
                            prompt=u.get("prompt_tokens", 0),
                            completion=u.get("completion_tokens", 0),
                            total=u.get("total_tokens", 0),
                        )
        except httpx.TimeoutException as e:
            raise CloudflareAIError("request timeout", status=None) from e
        except httpx.ConnectError as e:
            raise CloudflareAIError(f"connection error: {e}", status=None) from e

        tool_calls: list[ToolCall] = []
        for idx in sorted(tc_acc):
            tc = tc_acc[idx]
            try:
                args = json.loads(tc["arguments"]) if tc["arguments"] else {}
            except json.JSONDecodeError:
                args = _extract_partial_args(tc["arguments"]) if tc["arguments"] else {}
            tool_calls.append(ToolCall(id=tc["id"], name=tc["name"], arguments=args))

        return ModelResponse(
            content=full_text or ("" if tool_calls else None),
            tool_calls=tool_calls,
            usage=usage,
            model_id=self.model_id,
        )
