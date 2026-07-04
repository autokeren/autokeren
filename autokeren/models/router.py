"""Multi-model router with fallback and cost tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from autokeren.config import Config
from autokeren.models.base import Message, ModelResponse, TokenUsage
from autokeren.models.cloudflare import CloudflareAIError, CloudflareModel
from autokeren.models.retry import CircuitBreaker
from autokeren.utils import redact


@dataclass
class ModelRouter:
    cfg: Config
    models: list[CloudflareModel] = field(default_factory=list)
    breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    usage_total: TokenUsage = field(default_factory=TokenUsage)

    def __post_init__(self):
        if not self.models:
            base = CloudflareModel.from_config(self.cfg)
            primary = base
            from autokeren.models.cloudflare import resolve_model_id
            secondary_model_id = resolve_model_id(self.cfg.cloudflare.secondary_model, base.auth_mode)
            secondary = CloudflareModel(
                account_id=base.account_id,
                api_token=base.api_token,
                api_key=base.api_key,
                model_id=secondary_model_id,
                base_url=base.base_url,
                timeout=base.timeout,
                retry_policy=base.retry_policy,
                auth_mode=base.auth_mode,
            )
            self.models = [primary, secondary]
        for m in self.models:
            self.breakers.setdefault(m.model_id, CircuitBreaker(
                failure_threshold=self.cfg.retry.circuit_failure_threshold,
                open_seconds=float(self.cfg.retry.circuit_open_seconds),
            ))

    def healthy_models(self) -> list[CloudflareModel]:
        return [m for m in self.models if self.breakers[m.model_id].allow()]

    def swap_models(self) -> None:
        """Tukar primary <-> secondary."""
        if len(self.models) >= 2:
            self.models[0], self.models[1] = self.models[1], self.models[0]

    def set_primary(self, model_id: str) -> bool:
        """Jadikan model dengan id tertentu sebagai primary. Return True kalau sukses."""
        for i, m in enumerate(self.models):
            if m.model_id == model_id:
                if i != 0:
                    self.models.insert(0, self.models.pop(i))
                return True
        return False

    def current_model_id(self) -> str:
        return self.models[0].model_id if self.models else "?"

    def model_aliases(self) -> list[dict[str, Any]]:
        """Return list of model info for display."""
        return [
            {"id": m.model_id, "active": m.model_id == self.current_model_id()}
            for m in self.models
        ]

    def complete(
        self,
        messages: list[Message],
        tools: list[dict] | None = None,
        on_chunk: Callable[[str], None] | None = None,
        **params,
    ) -> ModelResponse:
        candidates = self.healthy_models()
        if not candidates:
            raise RuntimeError("all model circuit breakers are open")
        last_error: Exception | None = None
        for model in candidates:
            try:
                resp = model.complete(messages, tools=tools, on_chunk=on_chunk, **params)
                self.breakers[model.model_id].record_success()
                self.usage_total = self.usage_total + resp.usage
                resp.model_id = model.model_id
                return resp
            except CloudflareAIError as e:
                last_error = e
                self.breakers[model.model_id].record_failure()
                if e.status != 429:
                    continue
        raise last_error or RuntimeError("all models failed")

    def status(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "usage": {
                "prompt": self.usage_total.prompt,
                "completion": self.usage_total.completion,
                "total": self.usage_total.total,
            },
            "models": [],
        }
        for m in self.models:
            cb = self.breakers[m.model_id]
            out["models"].append({
                "model_id": m.model_id,
                "circuit": cb.state().value,
                "healthy": cb.allow(),
            })
        return out

    def redacted_dict(self) -> dict[str, Any]:
        """Safe config summary with token redacted."""
        return {
            "account_id": self.cfg.cloudflare.account_id,
            "api_token_tail": redact(self.cfg.cloudflare.api_token),
            "primary_model": self.cfg.cloudflare.primary_model,
            "secondary_model": self.cfg.cloudflare.secondary_model,
        }
