"""Config load/save for autokeren."""
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


def _config_dir() -> Path:
    return Path(os.environ.get("AUTOKEREN_CONFIG_DIR", Path.home() / ".config" / "autokeren"))


def _config_path() -> Path:
    return _config_dir() / "config.yaml"


class AuthConfig(BaseModel):
    mode: str = "platform"  # "platform" (default, pakai developers.autokeren.com) atau "direct" (pakai CF sendiri)
    api_key: str = ""       # ak_live_... dari developers.autokeren.com
    base_url: str = "https://api.developers.autokeren.com"


class CloudflareConfig(BaseModel):
    account_id: str = ""
    api_token: str = ""
    primary_model: str = "kimi-code"
    secondary_model: str = "kimi-2.6"
    max_tokens: int = 16384
    temperature: float = 0.3
    timeout: float = 120.0


class RetryConfig(BaseModel):
    max_retries: int = 5
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    circuit_failure_threshold: int = 5
    circuit_open_seconds: int = 30


class TimeTravelConfig(BaseModel):
    enabled: bool = True
    max_checkpoints: int = 50
    auto_checkpoint: bool = True


class ArchitectureGuardianConfig(BaseModel):
    enabled: bool = True
    genome_file: str = ".ak-genome.md"
    block_duplicates: bool = False
    scan_interval: int = 5


class LoopBreakerConfig(BaseModel):
    enabled: bool = True
    max_repeats: int = 3
    auto_switch_model: bool = True
    auto_clear_context: bool = False


class CrossModelReviewConfig(BaseModel):
    enabled: bool = True
    reviewer_model: str = "auto"
    auto_review: bool = False
    auto_fix: bool = True


class VibeSecurityConfig(BaseModel):
    enabled: bool = True
    scan_on_write: bool = True
    block_on_critical: bool = True
    checks: list[str] = Field(default_factory=lambda: ["secrets", "sqli", "xss", "forbidden"])


class LiveEnforcementConfig(BaseModel):
    enabled: bool = True
    rules_file: str = ".ak-rules.yaml"
    block_on_violation: bool = True


class SpecDrivenConfig(BaseModel):
    enabled: bool = True
    num_questions: int = 20
    auto_generate: bool = True
    plan_file: str = "plan.md"
    technical_file: str = "technical-plan.md"


class GhostAgentConfig(BaseModel):
    enabled: bool = True
    max_background: int = 3
    tmux_prefix: str = "ak-ghost"
    branch_isolation: bool = True
    auto_notify: bool = True
    log_dir: str = ".ak-ghost-logs"


class ResearchConfig(BaseModel):
    enabled: bool = True
    sources: list[str] = Field(default_factory=lambda: ["reddit", "hackernews", "web"])
    max_results: int = 10
    max_depth: int = 3
    summarize: bool = True
    min_comment_score: int = 2
    browser_integration: bool = False
    browser_url: str = "http://localhost:9377"


class AutokerenConfig(BaseModel):
    plan_mode: bool = False
    max_iterations: int = 50
    shell_timeout: int = 180
    shell_allowlist: list[str] = Field(default_factory=list)
    project_root: str = "."
    context_window: int = 262144
    compact_tail_turns: int = 6
    auto_compact: bool = False
    auto_compact_threshold: float = 0.8
    memory_enabled: bool = True
    auto_save_session: bool = False
    max_tool_calls: int = 0
    mermaid_render: bool = False
    language: str = ""
    time_travel: TimeTravelConfig = Field(default_factory=TimeTravelConfig)
    architecture_guardian: ArchitectureGuardianConfig = Field(default_factory=ArchitectureGuardianConfig)
    loop_breaker: LoopBreakerConfig = Field(default_factory=LoopBreakerConfig)
    cross_model_review: CrossModelReviewConfig = Field(default_factory=CrossModelReviewConfig)
    vibe_security: VibeSecurityConfig = Field(default_factory=VibeSecurityConfig)
    live_enforcement: LiveEnforcementConfig = Field(default_factory=LiveEnforcementConfig)
    spec_driven: SpecDrivenConfig = Field(default_factory=SpecDrivenConfig)
    ghost_agent: GhostAgentConfig = Field(default_factory=GhostAgentConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)


class CamofoxConfig(BaseModel):
    url: str = ""
    default_profile: str = ""
    user_id: str = ""


class MCPServerConfig(BaseModel):
    name: str
    command: list[str]
    env: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


class Config(BaseModel):
    auth: AuthConfig = Field(default_factory=AuthConfig)
    cloudflare: CloudflareConfig = Field(default_factory=CloudflareConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    autokeren: AutokerenConfig = Field(default_factory=AutokerenConfig)
    camofox: CamofoxConfig = Field(default_factory=CamofoxConfig)
    mcp_servers: list[MCPServerConfig] = Field(default_factory=list)


def load_config(path: Path | None = None) -> Config:
    target = path or _config_path()
    if not target.exists():
        cfg = Config()
    else:
        data = yaml.safe_load(target.read_text()) or {}
        if "models" in data.get("cloudflare", {}):
            data["cloudflare"].setdefault("primary_model", data["cloudflare"]["models"].get("primary"))
            data["cloudflare"].setdefault("secondary_model", data["cloudflare"]["models"].get("secondary"))
        cfg = Config(**data)
    # env fallback
    cfg.cloudflare.account_id = cfg.cloudflare.account_id or os.environ.get("CLOUDFLARE_ACCOUNT_ID") or os.environ.get("CF_ACCOUNT_ID", "")
    cfg.cloudflare.api_token = cfg.cloudflare.api_token or os.environ.get("CLOUDFLARE_API_TOKEN") or os.environ.get("CLOUDFLARE_API_KEY") or os.environ.get("CF_API_TOKEN", "")
    cfg.auth.api_key = cfg.auth.api_key or os.environ.get("AUTOKEREN_API_KEY") or os.environ.get("AK_API_KEY", "")
    return cfg


def save_config(cfg: Config, path: Path | None = None) -> Path:
    target = path or _config_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    out = yaml.safe_dump(cfg.model_dump(), sort_keys=False, default_flow_style=False)
    target.write_text(out)
    os.chmod(target, 0o600)
    return target


def init_config(interactive: bool = False) -> Config:
    cfg = Config()
    if interactive:
        print("Yuk setup autokeren.\n")
        print("Pilih mode autentikasi:")
        print("  1. Platform (default) — pakai API key dari developers.autokeren.com")
        print("  2. Direct — pakai Cloudflare account_id + api_token sendiri")
        choice = input("\nMode [1]: ").strip() or "1"
        if choice == "2":
            cfg.auth.mode = "direct"
            cfg.cloudflare.account_id = input("Cloudflare account id: ").strip()
            cfg.cloudflare.api_token = input("Cloudflare API token: ").strip()
        else:
            cfg.auth.mode = "platform"
            print("\nBuka https://developers.autokeren.com/dashboard/keys buat API key.")
            print("Format: ak_live_...")
            cfg.auth.api_key = input("API key: ").strip()
    save_config(cfg)
    return cfg


def ensure_config() -> Config:
    """Load config, or create empty template if missing."""
    target = _config_path()
    if not target.exists():
        return init_config()
    return load_config()
