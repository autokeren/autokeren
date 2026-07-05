"""Core agent loop."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from autokeren.config import Config
from autokeren.context import SessionContext
from autokeren.memory import MemoryManager
from autokeren.models.base import ModelResponse
from autokeren.models.router import ModelRouter
from autokeren.prompts import build_system_prompt
from autokeren.session import SessionManager
from autokeren.tools import ToolRegistry, ToolResult


class Agent:
    def __init__(
        self,
        cfg: Config,
        tools: ToolRegistry,
        project_root: str,
        memory: MemoryManager | None = None,
        sessions: SessionManager | None = None,
    ):
        self.cfg = cfg
        self.tools = tools
        self.project_root = project_root
        self.router = ModelRouter(cfg)
        self.context = SessionContext(project_root=Path(project_root))
        self.memory = memory if memory is not None else MemoryManager(project_root)
        self.sessions = sessions if sessions is not None else SessionManager(project_root)
        self._build_system_prompt()
        self.context.messages.append({"role": "system", "content": self._system_prompt})
        self.plan_approved = not cfg.autokeren.plan_mode
        self._tool_call_count = 0
        self._max_tool_calls = cfg.autokeren.max_tool_calls  # safety net, 0 = unlimited
        self._last_neuron_remaining: int | None = None
        self._last_neuron_quota: int | None = None

        # Opt-in UI callbacks (wired by CLI). Default None = no-op.
        self.on_model_start: Callable[[], None] | None = None
        self.on_model_end: Callable[[ModelResponse], None] | None = None
        self.on_tool_start: Callable[[str, dict[str, Any]], None] | None = None
        self.on_tool_end: Callable[[str, ToolResult], None] | None = None
        self.on_tool_output: Callable[[str, str], None] | None = None
        self.on_chunk: Callable[[str], None] | None = None
        self.permission_callback: Callable[[str, str, dict[str, Any]], bool] | None = None

    def _build_system_prompt(self) -> None:
        """Build system prompt dengan memory + AGENTS.md."""
        mem = self.memory.load() if self.cfg.autokeren.memory_enabled else ""
        self._system_prompt = build_system_prompt(
            self.project_root,
            self.tools,
            plan_mode=self.cfg.autokeren.plan_mode,
            memory=mem,
            max_tool_calls=self.cfg.autokeren.max_tool_calls,
        )

    def run(self, user_input: str) -> ModelResponse:
        self.context.add_user(user_input)
        for iteration in range(self.cfg.autokeren.max_iterations):
            if self.on_model_start:
                self.on_model_start()
            try:
                resp = self.router.complete(
                    self.context.messages,
                    tools=self.tools.schemas(),
                    max_tokens=self.cfg.cloudflare.max_tokens,
                    temperature=self.cfg.cloudflare.temperature,
                    on_chunk=self.on_chunk,
                )
            except KeyboardInterrupt:
                if self.on_model_end:
                    self.on_model_end(ModelResponse(content=""))
                return ModelResponse(content="[dibatalkan user]")
            except Exception as e:
                if self.on_model_end:
                    self.on_model_end(ModelResponse(content=""))
                err_msg = str(e) or type(e).__name__
                return ModelResponse(content=f"[red]⚠ Model error: {err_msg}[/red]\n\nCoba ganti model dengan /model, atau ulangi pertanyaan.")
            if self.on_model_end:
                self.on_model_end(resp)

            if resp.neurons_remaining is not None:
                self._last_neuron_remaining = resp.neurons_remaining
                self._last_neuron_quota = resp.neurons_quota

            # Plan mode: before approval, return the response without executing tools.
            if self.cfg.autokeren.plan_mode and not self.plan_approved:
                self.context.add_assistant(resp)
                return resp  # caller will ask user for approval

            if not resp.tool_calls:
                self.context.add_assistant(resp)
                return resp

            self.context.add_assistant(resp)
            for tc in resp.tool_calls:
                self._tool_call_count += 1
                if self._max_tool_calls > 0 and self._tool_call_count > self._max_tool_calls:
                    limit_msg = ToolResult(error=f"batas tool call tercapai ({self._max_tool_calls}). Selesaikan tanpa tool.", ok=False)
                    self.context.add_tool_result(tc.id, tc.name, limit_msg.to_dict(), False)
                    return ModelResponse(content=f"Batas {self._max_tool_calls} tool call tercapai. Selesaikan tugas dengan informasi yang sudah ada.")
                needs_perm, desc = self.tools.check_permission(tc.name, tc.arguments)
                if needs_perm:
                    allowed = self.permission_callback(tc.name, desc, tc.arguments) if self.permission_callback else True
                    if not allowed:
                        denied = ToolResult(error="ditolak oleh user", ok=False)
                        if self.on_tool_end:
                            self.on_tool_end(tc.name, denied)
                        self.context.add_tool_result(tc.id, tc.name, denied.to_dict(), denied.ok)
                        continue
                if self.on_tool_start:
                    self.on_tool_start(tc.name, tc.arguments)
                try:
                    def _on_output(line: str, _name: str = tc.name) -> None:
                        if self.on_tool_output:
                            self.on_tool_output(_name, line)
                    raw_result = self.tools.run(tc.name, tc.arguments, on_output=_on_output)
                except KeyboardInterrupt:
                    raw_result = ToolResult(error="dibatalkan user", ok=False)
                if self.on_tool_end:
                    self.on_tool_end(tc.name, raw_result)
                self.context.add_tool_result(tc.id, tc.name, raw_result.to_dict(), raw_result.ok)

        return ModelResponse(content="Mencapai batas iterasi maksimum tanpa jawaban final.")

    def approve_plan(self) -> None:
        self.plan_approved = True
        self.context.add_user("User approved the plan. Execute it now.")

    def reset(self) -> None:
        """Reset session context, reload memory + system prompt."""
        self.context.reset()
        self._build_system_prompt()
        self.context.messages.append({"role": "system", "content": self._system_prompt})
        self.plan_approved = not self.cfg.autokeren.plan_mode

    def save_session(self, name: str) -> str:
        """Save session ke disk. Return session_id."""
        usage = {
            "prompt": self.router.usage_total.prompt,
            "completion": self.router.usage_total.completion,
            "total": self.router.usage_total.total,
        }
        return self.sessions.save(name, self.context.messages, usage)

    def resume_session(self, identifier: str) -> str:
        """Resume session dari disk. Return status message."""
        data = self.sessions.load(identifier)
        if not data:
            return f"Session '{identifier}' tidak ditemukan."
        messages = data.get("messages", [])
        if not messages:
            return "Session kosong."
        # Reload system prompt dengan memory terbaru, keep rest
        self._build_system_prompt()
        messages[0] = {"role": "system", "content": self._system_prompt}
        self.context.messages = messages
        self.plan_approved = not self.cfg.autokeren.plan_mode
        name = data.get("name", "unknown")
        ts = data.get("timestamp", "")
        n = len(messages)
        return f"Session '{name}' di-resume ({n} pesan, saved {ts})."

    def context_info(self) -> dict[str, Any]:
        """Return info tentang context window usage buat display."""
        tokens = self.context.estimate_tokens()
        window = self.cfg.autokeren.context_window
        pct = round(tokens / window * 100, 1) if window > 0 else 0.0
        u = self.router.usage_total
        return {
            "tokens": tokens,
            "window": window,
            "pct": pct,
            "prompt_tokens": u.prompt,
            "completion_tokens": u.completion,
            "total_tokens": u.total,
        }

    def status_bar_info(self) -> dict[str, Any]:
        """Compact info untuk status bar: model, context, cwd, neurons."""
        info = self.context_info()
        model_id = self.router.models[0].model_id if self.router.models else "?"
        info["model"] = model_id.split("/")[-1] if "/" in model_id else model_id
        info["cwd"] = Path(self.project_root).name
        if self._last_neuron_remaining is not None:
            info["neurons_remaining"] = self._last_neuron_remaining
            info["neurons_quota"] = self._last_neuron_quota
        return info

    def should_compact(self) -> bool:
        """Cek apakah perlu auto-compact berdasarkan threshold."""
        if not self.cfg.autokeren.auto_compact:
            return False
        info = self.context_info()
        return info["pct"] >= self.cfg.autokeren.auto_compact_threshold * 100

    def compact(self) -> str:
        """Compact context: summarize pesan lama, keep system prompt + N pesan terakhir."""
        tail = self.cfg.autokeren.compact_tail_turns
        if len(self.context.messages) <= tail + 1:
            return "Context sudah cukup singkat, tidak perlu compact."

        system_msg = self.context.messages[0]
        recent = self.context.messages[-tail:]
        to_summarize = self.context.messages[1:-tail]

        before_tokens = self.context.estimate_tokens()

        summary_parts: list[str] = []
        for msg in to_summarize:
            role = msg.get("role", "?")
            content = str(msg.get("content", ""))[:800]
            summary_parts.append(f"[{role}] {content}")
        summary_text = "\n".join(summary_parts)

        summary_prompt = (
            "Ringkas percakapan berikut secara singkat dan padat. "
            "Pertahankan: keputusan penting, perubahan file, error yang ditemukan, "
            "dan konteks yang perlu diingat untuk percakapan selanjutnya.\n\n"
            f"{summary_text}"
        )

        resp = self.router.complete(
            [{"role": "user", "content": summary_prompt}],
            max_tokens=1024,
            temperature=0.0,
        )

        self.context.messages = [
            system_msg,
            {"role": "user", "content": f"Ringkasan percakapan sebelumnya:\n{resp.content}"},
            {"role": "assistant", "content": "Baik, saya ingat ringkasan ini. Lanjutkan."},
            *recent,
        ]

        after_tokens = self.context.estimate_tokens()
        saved = before_tokens - after_tokens
        return (
            f"Context di-compact: {len(to_summarize)} pesan diringkas. "
            f"Token {before_tokens:,} → {after_tokens:,} (hemat {saved:,})."
        )

    def status(self) -> dict[str, Any]:
        return {
            "project_root": self.project_root,
            "model_status": self.router.status(),
            "context": self.context.summary(),
        }
