"""Multi-model router with fallback and cost tracking."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from autokeren.config import Config
from autokeren.models.base import Message, ModelResponse, TokenUsage
from autokeren.models.cloudflare import CloudflareModel
from autokeren.models.retry import CircuitBreaker
from autokeren.utils import redact


@dataclass
class ModelRouter:
    cfg: Config
    models: list[Any] = field(default_factory=list)
    breakers: dict[str, CircuitBreaker] = field(default_factory=dict)
    usage_total: TokenUsage = field(default_factory=TokenUsage)

    def __post_init__(self):
        if not self.models:
            if self.cfg.auth.mode == "antigravity":
                from autokeren.models.antigravity import AntigravityModel
                primary = AntigravityModel(
                    model_id=self.cfg.cloudflare.primary_model,
                    timeout=self.cfg.cloudflare.timeout,
                )
                secondary = AntigravityModel(
                    model_id=self.cfg.cloudflare.secondary_model,
                    timeout=self.cfg.cloudflare.timeout,
                )
                self.models = [primary, secondary]
            elif self.cfg.auth.mode == "aistudio":
                from autokeren.models.aistudio import AIStudioModel
                primary = AIStudioModel(
                    model_id=self.cfg.cloudflare.primary_model,
                    api_key=self.cfg.auth.gemini_api_key,
                    timeout=self.cfg.cloudflare.timeout,
                )
                secondary = AIStudioModel(
                    model_id=self.cfg.cloudflare.secondary_model,
                    api_key=self.cfg.auth.gemini_api_key,
                    timeout=self.cfg.cloudflare.timeout,
                )
                self.models = [primary, secondary]
            else:
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

    def switch_model(self, model_id: str) -> bool:
        """Switch primary ke model_id. Kalau belum ada, buat instance baru."""
        if self.set_primary(model_id):
            return True

        if self.cfg.auth.mode == "antigravity":
            from autokeren.models.antigravity import AntigravityModel
            new_agy_model = AntigravityModel(
                model_id=model_id,
                timeout=self.cfg.cloudflare.timeout,
            )
            self.models.insert(0, new_agy_model)
            self.breakers.setdefault(model_id, CircuitBreaker(
                failure_threshold=self.cfg.retry.circuit_failure_threshold,
                open_seconds=float(self.cfg.retry.circuit_open_seconds),
            ))
            if len(self.models) > 5:
                self.models = self.models[:5]
            return True
        elif self.cfg.auth.mode == "aistudio":
            from autokeren.models.aistudio import AIStudioModel
            new_ai_model = AIStudioModel(
                model_id=model_id,
                api_key=self.cfg.auth.gemini_api_key,
                timeout=self.cfg.cloudflare.timeout,
            )
            self.models.insert(0, new_ai_model)
            self.breakers.setdefault(model_id, CircuitBreaker(
                failure_threshold=self.cfg.retry.circuit_failure_threshold,
                open_seconds=float(self.cfg.retry.circuit_open_seconds),
            ))
            if len(self.models) > 5:
                self.models = self.models[:5]
            return True

        base = self.models[0]
        # Pastikan base bertipe CloudflareModel untuk attribute access
        from autokeren.models.cloudflare import CloudflareModel
        if isinstance(base, CloudflareModel):
            from autokeren.models.cloudflare import resolve_model_id
            resolved = resolve_model_id(model_id, base.auth_mode)
            cf_model = CloudflareModel(
                account_id=base.account_id,
                api_token=base.api_token,
                api_key=base.api_key,
                model_id=resolved,
                base_url=base.base_url,
                timeout=base.timeout,
                retry_policy=base.retry_policy,
                auth_mode=base.auth_mode,
            )
            self.models.insert(0, cf_model)
            self.breakers.setdefault(resolved, CircuitBreaker(
                failure_threshold=self.cfg.retry.circuit_failure_threshold,
                open_seconds=float(self.cfg.retry.circuit_open_seconds),
            ))
        if len(self.models) > 5:
            self.models = self.models[:5]
        return True

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
        on_retry: Callable[[int, float, str], None] | None = None,
        **params,
    ) -> ModelResponse:
        candidates = self.healthy_models()
        if not candidates:
            raise RuntimeError("all model circuit breakers are open")
        last_error: Exception | None = None
        for i, model in enumerate(candidates):
            try:
                resp = model.complete(messages, tools=tools, on_chunk=on_chunk, on_retry=on_retry, **params)
                self.breakers[model.model_id].record_success()
                self.usage_total = self.usage_total + resp.usage
                resp.model_id = model.model_id
                return resp
            except Exception as e:
                last_error = e
                self.breakers[model.model_id].record_failure()
                if on_retry and i < len(candidates) - 1:
                    next_model = candidates[i + 1].model_id
                    on_retry(0, 0.0, f"fallback ke model: {next_model}")
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
