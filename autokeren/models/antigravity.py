"""Antigravity model client implementation using agy CLI command integration."""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from typing import Any, Callable

from autokeren.models.base import Message, ModelResponse, TokenUsage


def fetch_antigravity_models() -> list[dict[str, Any]]:
    """Fetch model list dengan memanggil agy models via subprocess."""
    try:
        res = subprocess.run(
            ["agy", "models"],
            capture_output=True,
            text=True,
            timeout=10.0,
        )
        if res.returncode == 0:
            models = []
            for line in res.stdout.splitlines():
                line_clean = line.replace("⠋", "").replace("⠙", "").replace("⠹", "").replace("⠸", "").replace("⠼", "").replace("⠴", "").replace("⠦", "").replace("⠧", "").replace("⠇", "").replace("⠏", "").strip()
                if line_clean:
                    models.append({
                        "id": line_clean,
                        "name": line_clean,
                        "provider": "Google Antigravity",
                        "tier": "antigravity",
                        "context": 1000000,
                        "desc": f"Model {line_clean} via Google Antigravity SDK",
                        "icon": "⚡",
                    })
            return models
    except Exception:
        pass
    
    # Fallback default models jika command gagal/timeout
    return [
        {"id": "Claude Sonnet 4.6 (Thinking)", "name": "Claude Sonnet 4.6 (Thinking)", "provider": "Google Antigravity", "tier": "antigravity", "context": 1000000, "desc": "Sonnet via Antigravity", "icon": "⚡"},
        {"id": "Gemini 3.5 Flash (Low)", "name": "Gemini 3.5 Flash (Low)", "provider": "Google Antigravity", "tier": "antigravity", "context": 1000000, "desc": "Gemini via Antigravity", "icon": "⚡"},
    ]


@dataclass
class AntigravityModel:
    model_id: str
    timeout: float = 180.0
    auth_mode: str = "antigravity"

    def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        on_retry: Callable[[int, float, str], None] | None = None,
        **params,
    ) -> ModelResponse:
        """Kirim turn percakapan ke agy CLI atau direct REST API jika agy tidak ada."""
        last_message = messages[-1]["content"] if messages else "Hello"



        # -------------------------------------------------------------
        # Subprocess Flow (Utama jika agy CLI terinstall di sistem)
        # -------------------------------------------------------------
        import shutil
        if shutil.which("agy"):
            try:
                # Siapkan command agy
                cmd = ["agy", "-p", last_message, "--dangerously-skip-permissions"]
                if self.model_id:
                    cmd += ["--model", self.model_id]
                
                # Jalankan agy secara stream non-interaktif
                proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1
                )
                
                full_content_parts = []
                # Streaming output baris per baris ke callback TUI
                if proc.stdout:
                    for line in iter(proc.stdout.readline, ""):
                        if line:
                            full_content_parts.append(line)
                            if on_chunk:
                                on_chunk(line)
                                
                proc.wait(timeout=self.timeout)
                if proc.returncode == 0:
                    content = "".join(full_content_parts)
                    prompt_tokens = len(last_message.split())
                    completion_tokens = len(content.split())
                    return ModelResponse(
                        content=content,
                        usage=TokenUsage(
                            prompt=prompt_tokens,
                            completion=completion_tokens,
                            total=prompt_tokens + completion_tokens
                        ),
                        model_id=self.model_id
                    )
            except Exception:
                pass  # Fallback ke REST API jika subprocess gagal

        # -------------------------------------------------------------
        # Direct REST API Flow (Fallback jika user tidak punya agy)
        # -------------------------------------------------------------
        from autokeren.models.google_auth import load_token, refresh_access_token, save_token
        token_data = load_token()
        if not token_data or not token_data.get("refresh_token"):
            raise RuntimeError("Anda belum login Google. Harap jalankan autokeren dengan flag --agy terlebih dahulu.")

        # Ambil/Refresh access token
        access_token = token_data.get("access_token")
        try:
            new_tokens = refresh_access_token(token_data["refresh_token"])
            if new_tokens:
                token_data.update(new_tokens)
                save_token(token_data)
                access_token = token_data.get("access_token")
        except Exception:
            pass

        if not access_token:
            raise RuntimeError("Gagal mendapatkan Access Token Google. Jalankan ulang autokeren --agy untuk login kembali.")


        # Panggil REST endpoint Gemini API / Cloudcode PA internal
        import httpx
        url = "https://daily-cloudcode-pa.googleapis.com/v1internal:streamGenerateContent?alt=sse"
        
        # Format payload resmi yang digunakan oleh Antigravity CLI / Cloud Code PA
        model_name = "Gemini 3.5 Flash (Medium)"
        if "pro" in self.model_id.lower() or "sonnet" in self.model_id.lower() or "opus" in self.model_id.lower():
            model_name = "Gemini 3.1 Pro (High)"
        elif "high" in self.model_id.lower():
            model_name = "Gemini 3.5 Flash (High)"
            
        payload = {
            "request": {
                "contents": [
                    {
                        "role": "user",
                        "parts": [{"text": last_message}]
                    }
                ],
                "model": f"models/{model_name.lower().replace(' (medium)', '').replace(' (high)', '').replace(' ', '-')}"
            }
        }
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }
        
        try:
            full_content_parts = []
            prompt_tokens = len(last_message.split())
            completion_tokens = 0
            total_tokens = 0

            with httpx.stream("POST", url, json=payload, headers=headers, timeout=self.timeout) as r:
                if r.status_code != 200:
                    err_body = r.read().decode("utf-8")
                    raise RuntimeError(f"Google API HTTP Error {r.status_code}: {err_body}")
                # Baca baris SSE stream
                for line in r.iter_lines():
                    if not line:
                        continue
                    # Decode bytes ke string jika bertipe bytes
                    line_str = line.decode("utf-8") if isinstance(line, bytes) else line
                    if line_str.startswith("data:"):
                        data_str = line_str[5:].strip()
                        if not data_str:
                            continue
                        try:
                            chunk_json = json.loads(data_str)
                            # Parsing candidates
                            candidates = chunk_json.get("candidates", [])
                            if candidates:
                                text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                                if text_part:
                                    full_content_parts.append(text_part)
                                    if on_chunk:
                                        on_chunk(text_part)
                            # Ambil metadata token jika ada di chunk terakhir
                            meta_usage = chunk_json.get("usageMetadata", {})
                            if meta_usage:
                                prompt_tokens = meta_usage.get("promptTokenCount", prompt_tokens)
                                completion_tokens = meta_usage.get("candidatesTokenCount", completion_tokens)
                                total_tokens = meta_usage.get("totalTokenCount", total_tokens)
                        except Exception:
                            pass
            
            content = "".join(full_content_parts)
            if not completion_tokens:
                completion_tokens = len(content.split())
            if not total_tokens:
                total_tokens = prompt_tokens + completion_tokens

            usage = TokenUsage(
                prompt=prompt_tokens,
                completion=completion_tokens,
                total=total_tokens,
            )
            
            return ModelResponse(
                content=content,
                usage=usage,
                model_id=self.model_id,
            )
        except httpx.HTTPStatusError as e:
            try:
                # Membaca data chunk yang tersisa / content secara aman
                err_body = e.response.read().decode("utf-8")
            except Exception as read_err:
                err_body = f"Gagal membaca content stream: {read_err}"
            raise RuntimeError(f"Google API HTTP Error {e.response.status_code}: {err_body}") from e
        except Exception as e:
            raise RuntimeError(f"Google API Request Failed: {e}") from e
