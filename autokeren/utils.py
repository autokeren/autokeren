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


_HARD_BLOCK_PATTERNS: list[tuple[str, str]] = [
    (r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+/(?:\s|$|\*)", "rm -rf on root"),
    (r"rm\s+-[a-z]*r[a-z]*f[a-z]*\s+/(?:home|usr|var|etc|boot|proc|sys)", "rm -rf on system dir"),
    (r"\bmkfs\b", "mkfs filesystem format"),
    (r"\bdd\s+.*\b(?:of|if)=/dev/(?:sd|nvme|hd)", "dd to disk device"),
    (r">\s*/dev/(?:sd|nvme|hd)", "write to disk device"),
    (r":\(\)\s*\{\s*:\|:\&\s*\}\s*;:", "fork bomb"),
    (r"\b--no-preserve-root\b", "no-preserve-root flag"),
    (r"\bfind\s+/\s+.*-delete\b", "find / -delete"),
    (r"\bchmod\s+-R\s+777\s+/", "chmod 777 on root"),
]


def is_dangerous_command(cmd: str, blocklist: list[str] | None = None) -> tuple[bool, str]:
    """Check for potentially destructive shell commands.

    Hard block: rm -rf root/system, mkfs, dd to devices, fork bombs — irreversible.
    Commands like sudo, git push --force, DROP TABLE are NOT blocked here —
    they go through the normal permission confirmation system instead.
    """
    if blocklist:
        lowered = cmd.lower()
        for item in blocklist:
            if item.lower() in lowered:
                return True, f"blocked pattern: {item}"

    for pattern, desc in _HARD_BLOCK_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, f"blocked: {desc}"
    return False, ""


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
