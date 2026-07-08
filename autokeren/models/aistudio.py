"""Google AI Studio (Gemini API) model client implementation."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

import httpx

from autokeren.models.base import Message, ModelResponse, TokenUsage, ToolCall


def fetch_aistudio_models(cfg) -> list[dict[str, Any]]:
    """Fetch model list secara dinamis dari Google AI Studio API."""
    api_key = cfg.auth.gemini_api_key
    if not api_key:
        # Fallback default models jika key kosong
        return [
            {
                "id": "gemini-1.5-flash",
                "name": "Gemini 1.5 Flash",
                "provider": "Google AI Studio",
                "tier": "aistudio",
                "context": 1048576,
                "desc": "Model Gemini 1.5 Flash via AI Studio",
                "icon": "♊",
            },
            {
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "provider": "Google AI Studio",
                "tier": "aistudio",
                "context": 2097152,
                "desc": "Model Gemini 1.5 Pro via AI Studio",
                "icon": "♊",
            },
            {
                "id": "gemini-2.0-flash-exp",
                "name": "Gemini 2.0 Flash Exp",
                "provider": "Google AI Studio",
                "tier": "aistudio",
                "context": 1048576,
                "desc": "Model Gemini 2.0 Flash Exp via AI Studio",
                "icon": "♊",
            },
        ]

    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
        resp = httpx.get(url, timeout=10.0)
        if resp.status_code == 200:
            data = resp.json()
            models = []
            for m in data.get("models", []):
                methods = m.get("supportedGenerationMethods", [])
                if "generateContent" in methods:
                    name_raw = m["name"]
                    model_id = name_raw.split("/")[-1]
                    display_name = m.get("displayName", model_id)
                    context_limit = m.get("inputTokenLimit", 1000000)
                    desc = m.get("description", "")
                    
                    models.append({
                        "id": model_id,
                        "name": display_name,
                        "provider": "Google AI Studio",
                        "tier": "aistudio",
                        "context": context_limit,
                        "desc": desc,
                        "icon": "♊",
                    })
            if models:
                return models
    except Exception:
        pass

    # Fallback default models jika request error/timeout
    return [
        {
            "id": "gemini-1.5-flash",
            "name": "Gemini 1.5 Flash",
            "provider": "Google AI Studio",
            "tier": "aistudio",
            "context": 1048576,
            "desc": "Model Gemini 1.5 Flash via AI Studio",
            "icon": "♊",
        },
        {
            "id": "gemini-1.5-pro",
            "name": "Gemini 1.5 Pro",
            "provider": "Google AI Studio",
            "tier": "aistudio",
            "context": 2097152,
            "desc": "Model Gemini 1.5 Pro via AI Studio",
            "icon": "♊",
        },
    ]


def resolve_aistudio_model_id(model_id: str) -> str:
    """Map Cloudflare/platform aliases to valid Gemini model IDs in AI Studio."""
    model_lower = model_id.lower()
    if "gemini" in model_lower:
        return model_id
    # Default mappings
    if "pro" in model_lower or "code" in model_lower:
        return "gemini-1.5-pro"
    return "gemini-1.5-flash"


@dataclass
class AIStudioModel:
    model_id: str
    api_key: str
    timeout: float = 120.0
    auth_mode: str = "aistudio"

    def __post_init__(self):
        self.model_id = resolve_aistudio_model_id(self.model_id)

    def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_retry: Callable[[int, float, str], None] | None = None,
        **params,
    ) -> ModelResponse:
        """Kirim turn percakapan ke Google AI Studio REST API."""
        if not self.api_key:
            raise RuntimeError("API Key Google AI Studio belum diisi.")

        # Format model_id
        model_name = self.model_id
        if not model_name.startswith("models/") and "/" not in model_name:
            model_name = f"models/{model_name}"

        # Konversi messages ke format Gemini contents
        contents: list[dict[str, Any]] = []
        system_parts = []
        for msg in messages:
            role = msg.get("role")
            content = msg.get("content") or ""
            
            if role == "system":
                system_parts.append(content)
            elif role == "tool":
                # Respon dari tool execution
                # Sesuai spec Gemini API, functionResponse ditaruh di dalam part
                contents.append({
                    "role": "user",
                    "parts": [
                        {
                            "functionResponse": {
                                "name": msg.get("name") or "",
                                "response": {"result": content}
                            }
                        }
                    ]
                })
            elif msg.get("tool_calls"):
                # Call dari model ke tool
                parts = []
                if content:
                    parts.append({"text": content})
                for tc in msg.get("tool_calls", []):
                    func = tc.get("function", {})
                    args = func.get("arguments", {})
                    if isinstance(args, str):
                        try:
                            args = json.loads(args)
                        except Exception:
                            args = {"raw": args}
                    parts.append({
                        "functionCall": {
                            "name": func.get("name") or tc.get("name") or "",
                            "args": args
                        }
                    })
                contents.append({
                    "role": "model",
                    "parts": parts
                })
            else:
                gemini_role = "model" if role == "assistant" else "user"
                # Gemini API tidak mengizinkan string kosong dalam part text
                text_content = content if content else " "
                contents.append({
                    "role": gemini_role,
                    "parts": [{"text": text_content}]
                })

        # Gabungkan role berurutan agar mematuhi aturan strict alternation (user -> model -> user)
        merged_contents: list[dict[str, Any]] = []
        for item in contents:
            if merged_contents and merged_contents[-1]["role"] == item["role"]:
                last_parts = merged_contents[-1]["parts"]
                if isinstance(last_parts, list):
                    last_parts.extend(item["parts"])
            else:
                merged_contents.append(item)

        payload: dict[str, Any] = {
            "contents": merged_contents
        }

        # Tambahkan systemInstruction jika ada
        if system_parts:
            payload["systemInstruction"] = {
                "parts": [{"text": "\n".join(system_parts)}]
            }

        # Tambahkan generationConfig
        max_tok = params.get("max_tokens") or 8192
        temp = params.get("temperature") or 0.3
        payload["generationConfig"] = {
            "temperature": temp,
            "maxOutputTokens": max_tok
        }

        # Tambahkan tools jika ada
        if tools:
            function_declarations = []
            for tool in tools:
                if tool.get("type") == "function":
                    func = tool.get("function", {})
                    function_declarations.append({
                        "name": func.get("name"),
                        "description": func.get("description"),
                        "parameters": func.get("parameters")
                    })
            if function_declarations:
                payload["tools"] = [{"functionDeclarations": function_declarations}]

        # Tentukan endpoint (streaming vs non-streaming)
        is_stream = on_chunk is not None
        if is_stream:
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:streamGenerateContent?alt=sse&key={self.api_key}"
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/{model_name}:generateContent?key={self.api_key}"

        try:
            full_content_parts = []
            tool_calls: list[ToolCall] = []
            prompt_tokens = 0
            completion_tokens = 0
            total_tokens = 0

            if is_stream:
                with httpx.stream("POST", url, json=payload, timeout=self.timeout) as r:
                    if r.status_code != 200:
                        err_body = r.read().decode("utf-8")
                        raise RuntimeError(f"Google API HTTP Error {r.status_code}: {err_body}")
                    
                    for line in r.iter_lines():
                        if not line:
                            continue
                        line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                        if line_str.startswith("data:"):
                            data_str = line_str[5:].strip()
                            if not data_str:
                                continue
                            try:
                                chunk_json = json.loads(data_str)
                                candidates = chunk_json.get("candidates", [])
                                if candidates:
                                    candidate = candidates[0]
                                    parts = candidate.get("content", {}).get("parts", [])
                                    for part in parts:
                                        # Parse text
                                        text_part = part.get("text", "")
                                        if text_part:
                                            full_content_parts.append(text_part)
                                            if on_chunk:
                                                on_chunk(text_part)
                                        # Parse function calls
                                        func_call = part.get("functionCall")
                                        if func_call:
                                            name = func_call.get("name", "")
                                            args = func_call.get("args", {})
                                            tool_calls.append(ToolCall(
                                                id=f"call_{len(tool_calls)}",
                                                name=name,
                                                arguments=args
                                            ))
                                # Parse usage metadata jika ada
                                meta_usage = chunk_json.get("usageMetadata", {})
                                if meta_usage:
                                    prompt_tokens = meta_usage.get("promptTokenCount", prompt_tokens)
                                    completion_tokens = meta_usage.get("candidatesTokenCount", completion_tokens)
                                    total_tokens = meta_usage.get("totalTokenCount", total_tokens)
                            except Exception:
                                pass
            else:
                resp = httpx.post(url, json=payload, timeout=self.timeout)
                if resp.status_code != 200:
                    raise RuntimeError(f"Google API HTTP Error {resp.status_code}: {resp.text}")
                
                data = resp.json()
                candidates = data.get("candidates", [])
                if candidates:
                    candidate = candidates[0]
                    parts = candidate.get("content", {}).get("parts", [])
                    for part in parts:
                        text_part = part.get("text", "")
                        if text_part:
                            full_content_parts.append(text_part)
                        
                        func_call = part.get("functionCall")
                        if func_call:
                            name = func_call.get("name", "")
                            args = func_call.get("args", {})
                            tool_calls.append(ToolCall(
                                id=f"call_{len(tool_calls)}",
                                name=name,
                                arguments=args
                            ))
                
                meta_usage = data.get("usageMetadata", {})
                if meta_usage:
                    prompt_tokens = meta_usage.get("promptTokenCount", prompt_tokens)
                    completion_tokens = meta_usage.get("candidatesTokenCount", completion_tokens)
                    total_tokens = meta_usage.get("totalTokenCount", total_tokens)

            content = "".join(full_content_parts)
            if not completion_tokens:
                completion_tokens = len(content.split())
            if not total_tokens:
                total_tokens = prompt_tokens + completion_tokens

            return ModelResponse(
                content=content if content else None,
                tool_calls=tool_calls,
                usage=TokenUsage(
                    prompt=prompt_tokens,
                    completion=completion_tokens,
                    total=total_tokens,
                ),
                model_id=self.model_id,
            )

        except httpx.HTTPStatusError as e:
            try:
                err_body = e.response.read().decode("utf-8")
            except Exception as read_err:
                err_body = f"Gagal membaca content: {read_err}"
            raise RuntimeError(f"Google API HTTP Error {e.response.status_code}: {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"Google API Request Failed: {e}") from e
