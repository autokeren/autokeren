"""Small helpers used across autokeren."""
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def redact(value: str | None, keep: int = 4) -> str:
    """Redact sensitive string, keep last N chars."""
    if not value:
        return ""
    if len(value) <= keep + 2:
        return "***"
    return "***" + value[-keep:]


def sanitize_filename(name: str) -> str:
    return re.sub(r"[^\w\-_.]", "_", name).strip("._")


def is_dangerous_command(cmd: str, blocklist: list[str] | None = None) -> tuple[bool, str]:
    """Delegate to security module for backward compatibility."""
    from autokeren.security import is_dangerous_command as _check
    return _check(cmd, blocklist)


def make_backup(path: Path) -> Path | None:
    """Copy file to .bak-{timestamp} if it exists."""
    if not path.exists():
        return None
    ts = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    bak = path.with_suffix(f"{path.suffix}.bak-{ts}")
    shutil.copy2(path, bak)
    return bak


def human_size(num: float) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if abs(num) < 1024:
            return f"{num:.1f} {unit}"
        num /= 1024
    return f"{num:.1f} TB"
