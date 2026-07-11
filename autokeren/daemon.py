"""JSON-RPC 2.0 daemon wrapper for autokeren Python Agent."""
from __future__ import annotations

import json
import sys
import threading
from pathlib import Path
from typing import Any

from autokeren.agent import Agent
from autokeren.config import load_config
from autokeren.memory import MemoryManager
from autokeren.cli import build_registry
from autokeren.kanban import KanbanDB


class JSONRPCDaemon:
    def __init__(self) -> None:
        self.agent: Agent | None = None
        self.pending_requests: dict[str | int, threading.Event] = {}
        self.request_responses: dict[str | int, Any] = {}
        self.lock = threading.Lock()
        self.next_client_req_id = 1000

    def send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Kirim notifikasi JSON-RPC ke standard output."""
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def send_request(self, method: str, params: dict[str, Any]) -> Any:
        """Kirim request ke client Go (misal konfirmasi izin) dan tunggu respon."""
        with self.lock:
            req_id = self.next_client_req_id
            self.next_client_req_id += 1
            evt = threading.Event()
            self.pending_requests[req_id] = evt

        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": req_id
        }
        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()

        # Tunggu sampai client mengirimkan response balik ke stdin
        evt.wait()

        with self.lock:
            resp = self.request_responses.pop(req_id, None)
            self.pending_requests.pop(req_id, None)

        if resp and "error" in resp:
            raise RuntimeError(resp["error"].get("message", "Request failed"))
        return resp.get("result") if resp else None

    def send_response(self, req_id: str | int | None, result: Any = None, error: Any = None) -> None:
        """Kirim respon atas request dari client Go."""
        if req_id is None:
            return
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": req_id
        }
        if error is not None:
            payload["error"] = error
        else:
            payload["result"] = result

        sys.stdout.write(json.dumps(payload, ensure_ascii=False) + "\n")
        sys.stdout.flush()

    def handle_request(self, req: dict[str, Any]) -> None:
        req_id = req.get("id")
        method = req.get("method")
        params = req.get("params", {})

        # Jika ini adalah response dari request yang dikirim daemon ke client
        if req_id is not None and method is None and ("result" in req or "error" in req):
            with self.lock:
                if req_id in self.pending_requests:
                    self.request_responses[req_id] = req
                    self.pending_requests[req_id].set()
            return

        # Peta method request
        if method == "agent.init":
            self.handle_agent_init(req_id, params)
        elif method == "agent.run":
            # Jalankan di background thread agar tidak memblokir input stdin selanjutnya
            threading.Thread(target=self.handle_agent_run, args=(req_id, params), daemon=True).start()
        elif method == "agent.interrupt":
            self.handle_agent_interrupt(req_id)
        elif method == "agent.compact":
            self.handle_agent_compact(req_id)
        elif method == "agent.status":
            self.handle_agent_status(req_id)
        elif method == "agent.reset":
            self.handle_agent_reset(req_id)
        elif method == "agent.switch_model":
            self.handle_agent_switch_model(req_id, params)
        elif method == "agent.list_models":
            self.handle_agent_list_models(req_id)
        elif method == "kanban.list":
            self.handle_kanban_list(req_id)
        elif method == "kanban.add":
            self.handle_kanban_add(req_id, params)
        elif method == "kanban.move":
            self.handle_kanban_move(req_id, params)
        elif method == "kanban.delete":
            self.handle_kanban_delete(req_id, params)
        else:
            self.send_response(
                req_id,
                error={"code": -32601, "message": f"Method not found: {method}"}
            )

    def handle_agent_init(self, req_id: str | int | None, params: dict[str, Any]) -> None:
        try:
            project_root = params.get("project_root", ".")
            cfg_path = params.get("config_path")
            cfg = load_config(Path(cfg_path) if cfg_path else None)

            # Menerapkan opsi config dinamis dari CLI
            if params.get("agy"):
                cfg.auth.mode = "antigravity"
                if not params.get("model"):
                    cfg.cloudflare.primary_model = "Gemini 3.5 Flash (Low)"
            elif params.get("aistudio"):
                cfg.auth.mode = "aistudio"
                if not params.get("model"):
                    cfg.cloudflare.primary_model = "gemini-3.5-flash"
            
            if params.get("plan"):
                cfg.autokeren.plan_mode = True

            if params.get("model"):
                model_name = str(params.get("model"))
                if cfg.auth.mode in ("antigravity", "aistudio"):
                    cfg.cloudflare.primary_model = model_name
                else:
                    from autokeren.models.cloudflare import resolve_model_id
                    if cfg.auth.mode == "platform":
                        cfg.cloudflare.primary_model = resolve_model_id(model_name, "platform")
                    else:
                        cfg.cloudflare.primary_model = model_name

            project_path = Path(project_root).expanduser().resolve()
            memory = MemoryManager(str(project_path))
            reg = build_registry(cfg, project_path, memory)

            # Daftarkan optional tools yang ada di cli.py agar daemon memiliki toolset yang sama persis
            from autokeren.tools import RewindTool, GenomeTool, ReviewTool, ResearchTool
            temp_agent = Agent(cfg, reg, str(project_path), memory=memory)
            if temp_agent.checkpoints:
                reg.register(RewindTool(temp_agent.checkpoints))
            if temp_agent._genome_scanner and temp_agent._genome:
                reg.register(GenomeTool(temp_agent._genome_scanner, temp_agent._genome))
            if cfg.autokeren.cross_model_review.enabled:
                coder_model = temp_agent.router.current_model_id()
                reg.register(ReviewTool(str(project_path), coder_model=coder_model, router=temp_agent.router))
            if cfg.autokeren.research.enabled:
                rc = cfg.autokeren.research
                reg.register(ResearchTool(
                    router=temp_agent.router,
                    max_results=rc.max_results,
                    max_depth=rc.max_depth,
                    summarize=rc.summarize,
                    min_comment_score=rc.min_comment_score,
                ))

            # Inisialisasi Agent
            self.agent = temp_agent

            # Pasang callbacks agen untuk dikirim sebagai notifikasi JSON-RPC ke Go TUI
            self.agent.on_model_start = lambda: self.send_notification("ui.on_model_start", {})
            self.agent.on_model_end = lambda resp: self.send_notification(
                "ui.on_model_end",
                {
                    "content": resp.content,
                    "model_id": resp.model_id,
                    "usage": {
                        "prompt": resp.usage.prompt,
                        "completion": resp.usage.completion,
                        "total": resp.usage.total
                    } if resp.usage else None
                }
            )
            self.agent.on_chunk = lambda text: self.send_notification("ui.on_chunk", {"text": text})
            self.agent.on_tool_start = lambda name, args: self.send_notification(
                "ui.on_tool_start", {"name": name, "arguments": args}
            )
            self.agent.on_tool_end = lambda name, res: self.send_notification(
                "ui.on_tool_end", {"name": name, "result": res.to_dict()}
            )
            self.agent.on_tool_output = lambda name, line: self.send_notification(
                "ui.on_tool_output", {"name": name, "line": line}
            )
            self.agent.on_retry = lambda attempt, delay, msg: self.send_notification(
                "ui.on_retry", {"attempt": attempt, "delay": delay, "message": msg}
            )

            # Sambungkan callback izin interaktif ke client Go
            self.agent.permission_callback = lambda name, desc, args: self.send_request(
                "ui.confirm_permission",
                {
                    "tool_name": name,
                    "description": desc,
                    "arguments": args
                }
            )

            self.send_response(req_id, result="initialized")
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_agent_run(self, req_id: str | int | None, params: dict[str, Any]) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            user_input = params.get("user_input", "")
            resp = self.agent.run(user_input)
            self.send_response(
                req_id,
                result={
                    "content": resp.content,
                    "model_id": resp.model_id,
                    "usage": {
                        "prompt": resp.usage.prompt,
                        "completion": resp.usage.completion,
                        "total": resp.usage.total
                    } if resp.usage else None
                }
            )
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_agent_interrupt(self, req_id: str | int | None) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            self.agent.interrupted = True
            self.send_response(req_id, result="Interrupted")
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_agent_compact(self, req_id: str | int | None) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            msg = self.agent.compact()
            self.send_response(req_id, result={"message": msg, "context_info": self.agent.context_info()})
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_agent_status(self, req_id: str | int | None) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            status_data = self.agent.status()
            status_data["context_info"] = self.agent.context_info()
            status_data["status_bar_info"] = self.agent.status_bar_info()
            self.send_response(req_id, result=status_data)
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_agent_reset(self, req_id: str | int | None) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            self.agent.reset()
            self.send_response(req_id, result="reset_complete")
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_agent_switch_model(self, req_id: str | int | None, params: dict[str, Any]) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            model_id = params.get("model_id", "")
            if not model_id:
                self.send_response(req_id, error={"code": -32602, "message": "model_id parameter is required"})
                return
            success = self.agent.router.switch_model(model_id)
            if success:
                self.send_response(req_id, result="switch_success")
            else:
                self.send_response(req_id, error={"code": -32001, "message": f"Failed to switch to model: {model_id}"})
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_agent_list_models(self, req_id: str | int | None) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            cfg = self.agent.cfg
            all_models = []
            
            # Ambil daftar model sesuai mode auth
            if cfg.auth.mode == "antigravity":
                from autokeren.models.antigravity import fetch_antigravity_models
                # Panggil fetch
                try:
                    all_models = fetch_antigravity_models()
                except Exception:
                    all_models = [{"id": "kimi-code", "name": "Kimi K2.7-Code"}, {"id": "glm-5.2", "name": "GLM 5.2"}]
            elif cfg.auth.mode == "aistudio":
                from autokeren.models.aistudio import fetch_aistudio_models
                try:
                    all_models = fetch_aistudio_models(cfg)
                except Exception:
                    all_models = [{"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"}, {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"}]
            else:
                from autokeren.models.cloudflare import fetch_available_models
                try:
                    all_models = fetch_available_models(cfg)
                except Exception:
                    all_models = [{"id": "@cf/meta/llama-3-8b-instruct", "name": "Llama 3 8B"}, {"id": "@cf/qwen/qwen1.5-14b-chat", "name": "Qwen 1.5 14B"}]

            current = self.agent.router.current_model_id()
            result = []
            for m in all_models:
                m_id = m.get("id", "")
                m_name = m.get("name", m_id)
                result.append({
                    "id": m_id,
                    "name": m_name,
                    "active": m_id == current
                })
                
            self.send_response(req_id, result=result)
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def _get_kanban_db(self) -> KanbanDB:
        if not self.agent:
            raise RuntimeError("Agent not initialized")
        from autokeren.kanban import KanbanDB
        return KanbanDB(self.agent.project_root)

    def handle_kanban_list(self, req_id: str | int | None) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            db = self._get_kanban_db()
            tasks = db.list_tasks()
            self.send_response(req_id, result=tasks)
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_kanban_add(self, req_id: str | int | None, params: dict[str, Any]) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            db = self._get_kanban_db()
            title = params.get("title", "")
            if not title:
                self.send_response(req_id, error={"code": -32602, "message": "title parameter is required"})
                return
            desc = params.get("description")
            status = params.get("status", "todo")
            priority = params.get("priority", "medium")
            task_id = db.add_task(title, desc, status, priority)
            self.send_response(req_id, result={"id": task_id, "status": "success"})
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_kanban_move(self, req_id: str | int | None, params: dict[str, Any]) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            db = self._get_kanban_db()
            task_id = params.get("id", 0)
            status = params.get("status", "")
            if task_id <= 0 or not status:
                self.send_response(req_id, error={"code": -32602, "message": "id and status parameters are required"})
                return
            success = db.move_task(task_id, status)
            if success:
                self.send_response(req_id, result={"id": task_id, "status": f"moved_to_{status}"})
            else:
                self.send_response(req_id, error={"code": -32002, "message": f"Task {task_id} not found"})
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})

    def handle_kanban_delete(self, req_id: str | int | None, params: dict[str, Any]) -> None:
        if not self.agent:
            self.send_response(req_id, error={"code": -32000, "message": "Agent not initialized"})
            return
        try:
            db = self._get_kanban_db()
            task_id = params.get("id", 0)
            if task_id <= 0:
                self.send_response(req_id, error={"code": -32602, "message": "id parameter is required"})
                return
            success = db.delete_task(task_id)
            if success:
                self.send_response(req_id, result={"id": task_id, "status": "deleted"})
            else:
                self.send_response(req_id, error={"code": -32002, "message": f"Task {task_id} not found"})
        except Exception as e:
            self.send_response(req_id, error={"code": -32603, "message": str(e)})


    def run(self) -> None:
        """Main loop membaca JSON-RPC baris demi baris dari stdin."""
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req = json.loads(line)
                self.handle_request(req)
            except Exception as e:
                self.send_notification("ui.error", {"message": f"Daemon loop error: {e}"})


if __name__ == "__main__":
    # Bersihkan buffer output agar real-time streaming lancar
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True) # type: ignore[attr-defined]
    if hasattr(sys.stdin, "reconfigure"):
        sys.stdin.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    
    daemon = JSONRPCDaemon()
    daemon.run()
