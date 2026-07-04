"""Config load/save for autokeren."""
import os
from pathlib import Path

import yaml
from pydantic import BaseModel, Field


def _config_dir() -> Path:
    return Path(os.environ.get("AUTOKEREN_CONFIG_DIR", Path.home() / ".config" / "autokeren"))


def _config_path() -> Path:
    return _config_dir() / "config.yaml"


class CloudflareConfig(BaseModel):
    account_id: str = ""
    api_token: str = ""
    primary_model: str = "@cf/moonshotai/kimi-k2.7-code"
    secondary_model: str = "@cf/zai-org/glm-5.2"
    max_tokens: int = 4096
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


class AutokerenConfig(BaseModel):
    plan_mode: bool = False
    max_iterations: int = 25
    shell_timeout: int = 180
    shell_allowlist: list[str] = Field(default_factory=lambda: ["node", "npm", "pnpm", "npx", "git", "wrangler", "python3", "pytest"])
    project_root: str = "."
    context_window: int = 262144
    compact_tail_turns: int = 6
    auto_compact: bool = False
    auto_compact_threshold: float = 0.8


class CamofoxConfig(BaseModel):
    url: str = "http://localhost:9377"
    default_profile: str = "pulsa"
    user_id: str = "ajat"


class Config(BaseModel):
    cloudflare: CloudflareConfig = Field(default_factory=CloudflareConfig)
    retry: RetryConfig = Field(default_factory=RetryConfig)
    autokeren: AutokerenConfig = Field(default_factory=AutokerenConfig)
    camofox: CamofoxConfig = Field(default_factory=CamofoxConfig)


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
        print("Yuk setup autokeren.")
        cfg.cloudflare.account_id = input("Cloudflare account id: ").strip()
        cfg.cloudflare.api_token = input("Cloudflare API token: ").strip()
    save_config(cfg)
    return cfg


def ensure_config() -> Config:
    """Load config, or create empty template if missing."""
    target = _config_path()
    if not target.exists():
        return init_config()
    return load_config()
