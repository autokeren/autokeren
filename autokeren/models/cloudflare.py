"""Cloudflare Workers AI inference client."""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

import httpx

from autokeren.models.base import Message, ModelResponse, TokenUsage, ToolCall
from autokeren.models.retry import RetryPolicy, retry_call


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

    def _endpoint(self) -> str:
        return f"{self.base_url}/accounts/{self.account_id}/ai/run/{self.model_id}"

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    @classmethod
    def from_config(cls, cfg) -> "CloudflareModel":
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

    def complete(self, messages: list[Message], tools: list[dict] | None = None, **params) -> ModelResponse:
        policy = self.retry_policy or RetryPolicy()

        def _call():
            return self._call_once(messages, tools=tools, **params)

        return retry_call(_call, policy)

    async def stream(self, messages: list[Message], **params) -> AsyncIterator[str]:
        raise NotImplementedError("streaming not yet implemented")
