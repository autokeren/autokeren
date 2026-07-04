"""Core agent loop."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from autokeren.config import Config
from autokeren.context import SessionContext
from autokeren.models.base import ModelResponse
from autokeren.models.router import ModelRouter
from autokeren.prompts import build_system_prompt
from autokeren.tools import ToolRegistry


class Agent:
    def __init__(self, cfg: Config, tools: ToolRegistry, project_root: str):
        self.cfg = cfg
        self.tools = tools
        self.project_root = project_root
        self.router = ModelRouter(cfg)
        self.context = SessionContext(project_root=Path(project_root))
        self._system_prompt = build_system_prompt(project_root, tools, plan_mode=cfg.autokeren.plan_mode)
        self.context.messages.append({"role": "system", "content": self._system_prompt})
        self.plan_approved = not cfg.autokeren.plan_mode

    def run(self, user_input: str) -> ModelResponse:
        self.context.add_user(user_input)
        for iteration in range(self.cfg.autokeren.max_iterations):
            resp = self.router.complete(
                self.context.messages,
                tools=self.tools.schemas(),
                max_tokens=self.cfg.cloudflare.max_tokens,
                temperature=self.cfg.cloudflare.temperature,
            )

            # Plan mode: before approval, return the response without executing tools.
            if self.cfg.autokeren.plan_mode and not self.plan_approved:
                self.context.add_assistant(resp)
                return resp  # caller will ask user for approval

            if not resp.tool_calls:
                self.context.add_assistant(resp)
                return resp

            self.context.add_assistant(resp)
            for tc in resp.tool_calls:
                raw_result = self.tools.run(tc.name, tc.arguments)
                self.context.add_tool_result(tc.id, tc.name, raw_result.to_dict(), raw_result.ok)

        return ModelResponse(content="Reached max iterations without final answer.")

    def approve_plan(self) -> None:
        self.plan_approved = True
        self.context.add_user("User approved the plan. Execute it now.")

    def reset(self) -> None:
        """Reset session context, re-adding the system prompt."""
        self.context.reset()
        self.context.messages.append({"role": "system", "content": self._system_prompt})
        self.plan_approved = not self.cfg.autokeren.plan_mode

    def status(self) -> dict[str, Any]:
        return {
            "project_root": self.project_root,
            "model_status": self.router.status(),
            "context": self.context.summary(),
        }
