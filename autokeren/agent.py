"""Core agent loop."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from autokeren.checkpoints import CheckpointManager
from autokeren.config import Config
from autokeren.context import SessionContext
from autokeren.enforcer import EnforcementEngine
from autokeren.genome import GuardianChecker, GenomeScanner, ProjectGenome
from autokeren.loop import LoopBreaker, PatternDetector
from autokeren.memory import MemoryManager
from autokeren.security_guard import SecurityScanner
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
        role: str = "",
        model_id: str | None = None,
    ):
        self.cfg = cfg
        self.tools = tools
        self.project_root = project_root
        self.router = ModelRouter(cfg)
        if model_id:
            self.router.switch_model(model_id)
        self.context = SessionContext(project_root=Path(project_root))
        self.memory = memory if memory is not None else MemoryManager(project_root)
        self.sessions = sessions if sessions is not None else SessionManager(project_root)
        self._build_system_prompt(role=role)
        self.context.messages.append({"role": "system", "content": self._system_prompt})
        self.plan_approved = not cfg.autokeren.plan_mode
        self._tool_call_count = 0
        self._max_tool_calls = cfg.autokeren.max_tool_calls  # safety net, 0 = unlimited
        self._last_neuron_remaining: int | None = None
        self._last_neuron_quota: int | None = None
        self.interrupted = False

        # Time-Travel checkpoints
        tt = cfg.autokeren.time_travel
        self.checkpoints: CheckpointManager | None = None
        if tt.enabled:
            self.checkpoints = CheckpointManager(
                project_root=Path(project_root),
                session_id="default",
                max_checkpoints=tt.max_checkpoints,
                auto_checkpoint=tt.auto_checkpoint,
            )

        # Architecture Guardian
        ag = cfg.autokeren.architecture_guardian
        self.guardian_enabled = ag.enabled
        self._genome: ProjectGenome | None = None
        self._guardian_checker: GuardianChecker | None = None
        self._genome_scanner: GenomeScanner | None = None
        self._tool_calls_since_scan = 0
        self._genome_scanned = False
        if ag.enabled:
            self._genome_scanner = GenomeScanner(Path(project_root))

        # Loop Breaker
        lb = cfg.autokeren.loop_breaker
        self.loop_breaker: LoopBreaker | None = None
        self._pattern_detector: PatternDetector | None = None
        if lb.enabled:
            self.loop_breaker = LoopBreaker(
                max_repeats=lb.max_repeats,
                auto_switch_model=lb.auto_switch_model,
                auto_clear_context=lb.auto_clear_context,
            )
            self._pattern_detector = PatternDetector()

        # Vibe-Security Guard
        vs = cfg.autokeren.vibe_security
        self.security_scanner: SecurityScanner | None = None
        if vs.enabled:
            self.security_scanner = SecurityScanner(checks=vs.checks)

        # Live Architecture Enforcement
        le = cfg.autokeren.live_enforcement
        self.enforcer: EnforcementEngine | None = None
        if le.enabled:
            rules_path = Path(project_root) / le.rules_file
            if rules_path.exists():
                self.enforcer = EnforcementEngine(rules_path)

        # Opt-in UI callbacks (wired by CLI). Default None = no-op.
        self.on_model_start: Callable[[], None] | None = None
        self.on_model_end: Callable[[ModelResponse], None] | None = None
        self.on_tool_start: Callable[[str, dict[str, Any]], None] | None = None
        self.on_tool_end: Callable[[str, ToolResult], None] | None = None
        self.on_tool_output: Callable[[str, str], None] | None = None
        self.on_chunk: Callable[[str], None] | None = None
        self.on_retry: Callable[[int, float, str], None] | None = None
        self.permission_callback: Callable[[str, str, dict[str, Any]], bool] | None = None
        self._consecutive_no_tool_prompts = 0

    def _build_system_prompt(self, role: str = "") -> None:
        """Build system prompt dengan memory + AGENTS.md."""
        mem = self.memory.load() if self.cfg.autokeren.memory_enabled else ""
        self._system_prompt = build_system_prompt(
            self.project_root,
            self.tools,
            plan_mode=self.cfg.autokeren.plan_mode,
            memory=mem,
            max_tool_calls=self.cfg.autokeren.max_tool_calls,
        )
        if role:
            self._system_prompt += (
                f"\n\n## Peran Spesifik Anda\n"
                f"Anda bertindak sebagai sub-agent spesialis dengan peran: {role}.\n"
                f"Fokuslah sepenuhnya pada tugas Anda dan kembalikan output terbaik sesuai dengan keahlian peran ini."
            )
        
        # Tambahkan instruksi pemaksaan bahasa respon AI
        lang_code = self.cfg.autokeren.language
        if not lang_code:
            import os
            lang_env = os.environ.get("LANG", "").lower()
            lang_code = "en"
            for code in ["id", "zh", "ja", "de", "ar", "es", "pt"]:
                if code in lang_env:
                    lang_code = code
                    break

        lang_names = {
            "id": "Indonesian",
            "en": "English",
            "zh": "Chinese",
            "ja": "Japanese",
            "de": "German",
            "ar": "Arabic",
            "es": "Spanish",
            "pt": "Portuguese",
        }
        lang_name = lang_names.get(lang_code, "English")
        self._system_prompt += f"\n\nIMPORTANT: You must respond to the user in {lang_name}."

    def _ensure_genome_scanned(self) -> None:
        """Lazy genome scan — only scan on first write_file/patch_file, not at startup."""
        if self._genome_scanned or not self._genome_scanner:
            return
        self._genome = self._genome_scanner.scan()
        ag = self.cfg.autokeren.architecture_guardian
        self._guardian_checker = GuardianChecker(self._genome, block_duplicates=ag.block_duplicates) if self._genome else None
        self._genome_scanned = True

    def check_interrupt(self) -> None:
        """Angkat KeyboardInterrupt jika bendera interupsi aktif."""
        if self.interrupted:
            self.interrupted = False
            raise KeyboardInterrupt("Interrupted by user")

    def _add_assistant_and_log(self, resp: ModelResponse) -> None:
        self.context.add_assistant(resp)
        if self.cfg.autokeren.memory_enabled and resp.content:
            self.memory.log_message(session_id="default", role="assistant", content=resp.content)

    def run(self, user_input: str) -> ModelResponse:
        self.context.add_user(user_input)
        if self.cfg.autokeren.memory_enabled:
            self.memory.log_message(session_id="default", role="user", content=user_input)
            relevant = self.memory.search_relevant(user_input, limit=3)
            if relevant:
                ctx_msg = "ℹ️ MEMORI HISTORIS RELEVAN DARI SESI SEBELUMNYA:\n" + "\n".join(f"- {r}" for r in relevant)
                self.context.messages.insert(-1, {"role": "system", "content": ctx_msg})
        try:
            for iteration in range(self.cfg.autokeren.max_iterations):
                self.check_interrupt()

                if self.on_model_start:
                    self.on_model_start()

                def _on_chunk(text: str) -> None:
                    self.check_interrupt()
                    if self.on_chunk:
                        self.on_chunk(text)

                try:
                    resp = self.router.complete(
                        self.context.messages,
                        tools=self.tools.schemas(),
                        max_tokens=self.cfg.cloudflare.max_tokens,
                        temperature=self.cfg.cloudflare.temperature,
                        on_chunk=_on_chunk,
                        on_retry=self.on_retry,
                    )
                except Exception as e:
                    import os
                    import time
                    if os.environ.get("AUTOKEREN_DEBUG") == "1":
                        raise
                    err_msg = str(e) or type(e).__name__
                    if iteration < self.cfg.autokeren.max_iterations - 1:
                        if not self.router.has_healthy():
                            if self.on_retry:
                                self.on_retry(iteration + 1, 5.0, f"Semua model down ({err_msg}). Reset circuit breakers, mencoba lagi...")
                            self.router.reset_breakers()
                            backoff = min(3.0 * (2 ** min(iteration, 5)), 60.0)
                            time.sleep(backoff)
                            continue
                        if self.on_retry:
                            self.on_retry(iteration + 1, 3.0, f"Error: {err_msg} | Mencoba berpindah model...")
                        time.sleep(3.0)
                        self.router.swap_models()
                        continue
                    if self.on_model_end:
                        self.on_model_end(ModelResponse(content=""))
                    return ModelResponse(content=f"[red]⚠ Model error: {err_msg}[/red]\n\nCoba ganti model dengan /model, atau ulangi pertanyaan.")

                if self.on_model_end:
                    self.on_model_end(resp)

                if resp.neurons_remaining is not None:
                    self._last_neuron_remaining = resp.neurons_remaining
                    self._last_neuron_quota = resp.neurons_quota

                # Plan mode: sebelum persetujuan, kembalikan respon tanpa jalankan tool
                if self.cfg.autokeren.plan_mode and not self.plan_approved:
                    self._add_assistant_and_log(resp)
                    return resp

                if not resp.tool_calls:
                    has_run_tools = any(isinstance(m, dict) and m.get("role") == "tool" for m in self.context.messages)
                    if has_run_tools and self._consecutive_no_tool_prompts < 2 and iteration < self.cfg.autokeren.max_iterations - 1:
                        continuation_keywords = ["akan", "mari", "selanjutnya", "berikutnya", "mencoba", "perlu", "harus", "apology", "maaf"]
                        content_lower = (resp.content or "").lower()
                        needs_continue = any(kw in content_lower for kw in continuation_keywords)
                        if needs_continue:
                            self._consecutive_no_tool_prompts += 1
                            self._add_assistant_and_log(resp)
                            self.context.messages.append({
                                "role": "system",
                                "content": (
                                    "⚠️ KAMU SEDANG DALAM MODE OTONOM. Jangan sekadar menjelaskan langkah selanjutnya "
                                    "atau meminta maaf. Gunakan tool yang sesuai secara langsung untuk melanjutkan tugas "
                                    "sampai selesai sepenuhnya."
                                )
                            })
                            continue

                    self._consecutive_no_tool_prompts = 0
                    self._add_assistant_and_log(resp)
                    return resp

                self._consecutive_no_tool_prompts = 0
                self._add_assistant_and_log(resp)
                for tc in resp.tool_calls:
                    self.check_interrupt()

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
                    # Architecture Guardian: check sebelum write/patch
                    if (
                        self.guardian_enabled
                        and self._genome_scanner
                        and tc.name in ("write_file", "patch_file")
                    ):
                        self._ensure_genome_scanned()
                        _gpath = tc.arguments.get("path", "")
                        _gcontent = tc.arguments.get("content", tc.arguments.get("new_string", ""))
                        if _gpath and _gcontent and self._guardian_checker:
                            guard = self._guardian_checker.check_before_write(_gpath, _gcontent)
                            if guard.blocked:
                                blocked_result = ToolResult(
                                    error=f"⚠️ ARCHITECTURE GUARDIAN BLOCKED:\n{guard.reason}\n\nSaran: {guard.suggestion}",
                                    ok=False,
                                )
                                if self.on_tool_end:
                                    self.on_tool_end(tc.name, blocked_result)
                                self.context.add_tool_result(tc.id, tc.name, blocked_result.to_dict(), False)
                                continue
                            if guard.warnings:
                                self.context.messages.append({
                                    "role": "system",
                                    "content": "ℹ️ Guardian warning: " + "; ".join(guard.warnings),
                                })
                    # Live Enforcement: check rules sebelum write/patch
                    if (
                        self.enforcer
                        and tc.name in ("write_file", "patch_file")
                    ):
                        _epath = tc.arguments.get("path", "")
                        _econtent = tc.arguments.get("content", tc.arguments.get("new_string", ""))
                        if _epath and _econtent:
                            enfo = self.enforcer.check_before_write(_epath, _econtent)
                            if enfo.blocked:
                                block_msgs = [v.message for v in enfo.violations if v.action == "block"]
                                blocked_result = ToolResult(
                                    error="⛔ LIVE ENFORCEMENT BLOCKED:\n" + "\n".join(f"  • {m}" for m in block_msgs),
                                    ok=False,
                                )
                                if self.on_tool_end:
                                    self.on_tool_end(tc.name, blocked_result)
                                self.context.add_tool_result(tc.id, tc.name, blocked_result.to_dict(), False)
                                continue
                    _before_snap: dict[str, str | None] | None = None
                    if self.checkpoints and self.checkpoints.auto_checkpoint and tc.name in ("write_file", "patch_file"):
                        _path = tc.arguments.get("path", "")
                        if _path:
                            _before_snap = self.checkpoints.snapshot_files([_path])
                    
                    def _on_output(line: str, _name: str = tc.name) -> None:
                        self.check_interrupt()
                        if self.on_tool_output:
                            self.on_tool_output(_name, line)
                    
                    raw_result = self.tools.run(tc.name, tc.arguments, on_output=_on_output)
                    
                    if self.on_tool_end:
                        self.on_tool_end(tc.name, raw_result)
                    # Loop Breaker: track errors
                    if self.loop_breaker and not raw_result.ok:
                        lb_action = self.loop_breaker.track_error(
                            error=raw_result.error or str(raw_result.to_dict()),
                            tool_name=tc.name,
                            context={"args": tc.arguments},
                        )
                        if lb_action.action == "break":
                            self.context.messages.append({
                                    "role": "system",
                                    "content": lb_action.suggestion,
                                })
                            self.run_self_improvement(
                                failed_tool_name=tc.name,
                                error_message=raw_result.error or str(raw_result.to_dict()),
                                tool_args=tc.arguments
                            )
                            if lb_action.switch_model:
                                self.router.swap_models()
                            if lb_action.clear_context:
                                self.compact()
                            self.loop_breaker.reset()
                    # Pattern Detector: track all tool calls
                    if self._pattern_detector:
                        from autokeren.loop.patterns import ToolCallEntry
                        self._pattern_detector.track(ToolCallEntry(
                            name=tc.name,
                            args=tc.arguments,
                            success=raw_result.ok,
                            message="",
                        ))
                        pat = self._pattern_detector.detect()
                        if pat.detected:
                            self.context.messages.append({
                                "role": "system",
                                "content": f"⚠️ PATTERN DETECTED: {pat.pattern} — {pat.detail}. Coba pendekatan berbeda.",
                            })
                            self._pattern_detector.reset()
                    if self.checkpoints and self.checkpoints.auto_checkpoint:
                        self.checkpoints.save(
                            tool_name=tc.name,
                            tool_args=tc.arguments,
                            tool_result=raw_result.to_dict(),
                            tool_ok=raw_result.ok,
                            before_snapshot=_before_snap,
                        )
                    # Vibe-Security: scan after write
                    if (
                        self.security_scanner
                        and tc.name in ("write_file", "patch_file")
                        and raw_result.ok
                    ):
                        _sec_path = tc.arguments.get("path", "")
                        _sec_content = tc.arguments.get("content", tc.arguments.get("new_string", ""))
                        if _sec_path and _sec_content:
                            findings = self.security_scanner.scan(_sec_path, _sec_content)
                            if findings:
                                critical = [f for f in findings if f.severity == "CRITICAL"]
                                if critical:
                                    warn_text = SecurityScanner.format_findings(findings)
                                    self.context.messages.append({
                                        "role": "system",
                                        "content": f"🛡️ SECURITY ALERT:\n{warn_text}\n\nFix critical issues sebelum lanjut.",
                                    })
                    # Architecture Guardian: auto-rescan genome
                    if self.guardian_enabled and self._genome_scanner and tc.name in ("write_file", "patch_file"):
                        self._tool_calls_since_scan += 1
                        ag_cfg = self.cfg.autokeren.architecture_guardian
                        if self._tool_calls_since_scan >= ag_cfg.scan_interval:
                            self._genome = self._genome_scanner.scan()
                            self._guardian_checker = GuardianChecker(self._genome, block_duplicates=ag_cfg.block_duplicates)
                            self._tool_calls_since_scan = 0
                    self.context.add_tool_result(tc.id, tc.name, raw_result.to_dict(), raw_result.ok)

            return ModelResponse(content="Mencapai batas iterasi maksimum tanpa jawaban final.")
        except KeyboardInterrupt:
            if self.on_model_end:
                self.on_model_end(ModelResponse(content=""))
            return ModelResponse(content="[dibatalkan user]")


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
        messages = self._clean_orphaned_tool_calls(messages)
        self._build_system_prompt()
        messages[0] = {"role": "system", "content": self._system_prompt}
        self.context.messages = messages
        self.plan_approved = not self.cfg.autokeren.plan_mode
        name = data.get("name", "unknown")
        ts = data.get("timestamp", "")
        n = len(messages)
        return f"Session '{name}' di-resume ({n} pesan, saved {ts})."

    @staticmethod
    def _clean_orphaned_tool_calls(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Hapus tool_calls dari pesan assistant terakhir kalau ga ada tool result setelahnya."""
        if not messages:
            return messages
        last = messages[-1]
        if last.get("role") == "assistant" and last.get("tool_calls"):
            if "content" not in last or not last.get("content"):
                messages = messages[:-1]
            else:
                last.pop("tool_calls", None)
        return messages

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
        from autokeren import __version__
        todo_tool = self.tools.get("todo")
        todos = []
        if todo_tool and hasattr(todo_tool, "get_todos"):
            todos = todo_tool.get_todos()
        
        kanban_tasks = []
        try:
            from autokeren.kanban import KanbanDB
            db = KanbanDB(self.project_root)
            kanban_tasks = db.list_tasks()
        except Exception:
            pass

        return {
            "project_root": self.project_root,
            "model_status": self.router.status(),
            "context": self.context.summary(),
            "todos": todos,
            "kanban_tasks": kanban_tasks,
            "version": __version__,
        }

    def run_autonomous(self, goal: str, context: str = "") -> dict[str, Any]:
        """Run autonomous planning: decompose goal, execute sub-tasks, reflect.

        Returns dict with tracker summary, results, and lessons.
        """
        from autokeren.autoplan import PlanExecutor, Reflector

        reflector = Reflector(router=self.router, memory=self.memory)
        executor = PlanExecutor(
            agent=self,
            router=self.router,
            max_retries_per_task=2,
            on_task_start=lambda t: None,
            on_task_done=lambda t, r: reflector.reflect(t, r),
            on_progress=lambda msg: None,
        )

        mem_context = context
        if self.cfg.autokeren.memory_enabled:
            mem_context = (self.memory.load() or "") + chr(10) + context

        tracker = executor.execute_plan(goal=goal, context=mem_context)

        return {
            "tracker": tracker.to_dict(),
            "results": [r.to_dict() for r in executor.results],
            "lessons": [lesson.to_dict() for lesson in reflector.lessons],
            "reflection_summary": reflector.summary(),
            "patterns": reflector.get_patterns(),
        }

    def run_self_improvement(self, failed_tool_name: str, error_message: str, tool_args: dict[str, Any]) -> bool:
        """Menjalankan siklus self-evolution mandiri jika sebuah tool gagal berulang kali."""
        if getattr(self, "_evolving", False):
            return False
        self._evolving = True
        
        try:
            # Cari path file tool-nya
            tool_file = Path(self.project_root) / "autokeren" / "tools" / f"{failed_tool_name}.py"
            if not tool_file.exists():
                # Jika kustom tool dinamis
                tool_file = Path(self.project_root) / ".ak-tools" / f"{failed_tool_name}.py"
                
            if not tool_file.exists():
                return False
                
            if self.on_tool_output:
                self.on_tool_output("self_evolution", f"🛠️ [bold magenta]SELF-EVOLUTION TRIGGERED:[/bold magenta] Tool '{failed_tool_name}' gagal berulang kali dengan error: {error_message}. Memulai self-refactoring...")

            goal = (
                f"Perbaiki bug/keterbatasan pada tool '{failed_tool_name}' yang berada di {tool_file.name}. "
                f"Tool tersebut dipanggil dengan argumen: {tool_args} "
                f"dan menghasilkan error: {error_message}. "
                f"Refaktor implementasi Python tool tersebut di file {tool_file.name}, "
                f"tambahkan test case baru di tests/ jika diperlukan, dan jalankan pytest untuk memvalidasi perbaikan."
            )
            
            # Jalankan autonomous run untuk memperbaiki dirinya sendiri!
            self.run_autonomous(goal, context=f"File target: {tool_file}\nError: {error_message}")
            
            # Muat ulang registry agar perubahan tool langsung diterapkan secara hot-reload!
            from autokeren.cli import build_registry
            new_registry = build_registry(self.cfg, Path(self.project_root), self.memory)
            self.tools = new_registry
            
            if self.on_tool_output:
                self.on_tool_output("self_evolution", f"✨ [bold green]SELF-EVOLUTION SUKSES:[/bold green] Tool '{failed_tool_name}' berhasil direfaktor dan dimuat ulang secara hot-reload!")
            return True
            
        except Exception as e:
            if self.on_tool_output:
                self.on_tool_output("self_evolution", f"❌ [bold red]SELF-EVOLUTION GAGAL:[/bold red] Gagal merefaktor tool: {e}")
            return False
        finally:
            self._evolving = False
