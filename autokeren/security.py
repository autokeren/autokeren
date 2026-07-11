"""Security module — path protection, dangerous command detection, exfiltration blocking."""
from __future__ import annotations

import re
from pathlib import Path

# ── Hard block: selalu ditolak, tidak bisa di-override ──────────────────
# File-file ini TIDAK PERNAH boleh diakses agent (private keys, SSH, cloud creds)
_HARD_READ_PATTERNS = [
    ".ssh/",
    ".aws/credentials",
    ".aws/config",
    ".gnupg/",
    "id_rsa",
    "id_ed25519",
    "id_ecdsa",
    "id_dsa",
    ".pem",
    ".key",
    ".pfx",
    ".p12",
    ".git-credentials",
    ".kube/config",
    ".pgpass",
    "firebase-adminsdk",
    "service-account",
]

# ── Soft block: minta izin user terlebih dahulu ──────────────────────────
# File-file ini sensitif tapi user kadang perlu akses di project sendiri
_SOFT_READ_PATTERNS = [
    ".env",
    "config.yaml",
    "config.yml",
    "credentials",
    "credentials.json",
    "keystore",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".docker/config",
    "secret",
    "token",
    "oauth",
]

# Legacy alias (union dari keduanya, untuk backward compat)
_SENSITIVE_READ_PATTERNS = _HARD_READ_PATTERNS + _SOFT_READ_PATTERNS


_SENSITIVE_WRITE_PATTERNS = [
    ".ssh/",
    ".bashrc",
    ".bash_profile",
    ".profile",
    ".zshrc",
    ".bash_aliases",
    "/etc/",
    "crontab",
    ".config/autokeren/",
    ".git/config",
    ".git/hooks/",
    ".docker/",
    ".kube/",
    "systemd",
    "init.d",
    "authorized_keys",
    "known_hosts",
    ".npmrc",
    ".pypirc",
    ".netrc",
    ".git-credentials",
]

# ── Dangerous command patterns (hard block) ─────────────────────────────

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
    (r"\bshutdown\b|\breboot\b|\bhalt\b|\bpoweroff\b", "system power control"),
    (r"\biptables\s+-F\b|\biptables\s+-P\b.*DROP", "firewall flush/policy"),
    (r"\bufw\s+disable\b", "firewall disable"),
    (r"\bsystemctl\s+(?:stop|disable|mask)\b", "systemctl stop/disable"),
    (r"\bmount\s+/dev/\w+\s+/", "mount device to root"),
    (r"\bumount\s+/(?:\s|$)", "unmount root"),
]

# ── Exfiltration patterns (hard block) ───────────────────────────────────

_EXFIL_PATTERNS: list[tuple[str, str]] = [
    (r"curl\s+.*\|\s*(?:sh|bash|zsh|python|perl|ruby)\b", "curl piped to shell"),
    (r"wget\s+.*\|\s*(?:sh|bash|zsh|python|perl|ruby)\b", "wget piped to shell"),
    (r"\beval\s*\(", "eval() call"),
    (r"\beval\s+(?:\"\$|\$\()", "eval of variable/subshell"),
    (r"base64\s+.*\|\s*(?:sh|bash|zsh|python)\b", "base64 decoded to shell"),
    (r"echo\s+.*\|\s*(?:base64|openssl)\s+.*\|\s*(?:sh|bash)", "encoded piped to shell"),
    (r"\bnc\s+.*\s+-[a-z]*e\b", "netcat reverse shell"),
    (r"\bncat\s+.*\s+-[a-z]*e\b", "ncat reverse shell"),
    (r"\bbash\s+-i\s+>\&\s*/dev/tcp/", "bash reverse shell /dev/tcp"),
    (r"\bsh\s+-i\s+>\&\s*/dev/tcp/", "sh reverse shell /dev/tcp"),
    (r"\bpython\d?\s+-c\s+.*(?:os\.system|subprocess|popen)", "python code execution"),
    (r"\bperl\s+-e\s+.*(?:system|exec|eval)", "perl code execution"),
    (r"\bruby\s+-e\s+.*(?:system|exec|eval)", "ruby code execution"),
    (r"\bsocat\s+.*(?:EXEC|SYSTEM|fork)", "socat reverse shell"),
    (r"\bscp\s+.*@", "scp to remote host"),
    (r"\brsync\s+.*@.*::", "rsync to remote host"),
    (r"\bcrontab\s+(?:-e|-r)\b", "crontab edit/remove"),
    (r"echo\s+.*>>\s*.*\.ssh/authorized_keys", "inject SSH authorized_keys"),
    (r"echo\s+.*>>\s*.*\.bashrc", "inject into bashrc"),
    (r"echo\s+.*>>\s*.*\.profile", "inject into profile"),
    (r"\bexport\s+(?:HOME|PATH|LD_LIBRARY_PATH|PYTHONPATH)\s*=", "manipulate critical env vars"),
    (r"\benv\s+.*\|\s*(?:curl|wget|nc|scp)", "env exfiltration"),
    (r"\bcat\s+.*\|\s*(?:curl|wget|nc|scp)\b", "cat piped to network tool"),
    (r"\bcp\s+.*\b(?:\.ssh|\.env|\.aws|\.kube|credentials)\b.*\|\s*(?:curl|wget)", "copy sensitive to network"),
    (r"\btar\s+.*\b(?:\.ssh|\.env|\.aws|\.gnupg)\b.*\|\s*(?:curl|wget|nc)", "tar sensitive to network"),
    (r"source\s+/dev/stdin", "source from stdin"),
    (r"\.\s+/dev/stdin", "dot-source from stdin"),
    (r"\bcurl\s+.*\$(?:\(|{)", "curl with variable expansion"),
    (r"\bwget\s+.*\$(?:\(|{)", "wget with variable expansion"),
    (r"\bxargs\s+(?:sh|bash|python|perl)", "xargs to interpreter"),
    (r"\benv\s+.*xargs\s+(?:sh|bash)", "env piped to xargs shell"),
    (r"\btee\s+/(?:etc|usr|var|boot|proc|sys)", "tee to system dir"),
    (r"\bchmod\s+.*\+x.*\|\s*(?:sh|bash)", "chmod +x piped to shell"),
    (r"\binstall\s+-m\s*777\s+/", "install with 777 to root"),
    (r"\bchown\s+-R\s+.*\s+/", "recursive chown on root"),
    (r"\bchattr\s+.*-i\s+/(?:etc|usr|var|boot)", "chattr immutable on system"),
    (r"\bkillall\s+-9\b|\bpkill\s+-9\b.*(?:sshd|bash|systemd|init)", "kill critical processes"),
    (r"\bhistory\s+-c\b", "clear history (cover tracks)"),
    (r"\bshred\s+.*\.(?:ssh|env|bashrc|profile|bash_history)", "shred sensitive files"),
    (r"\btruncate\s+-s\s+0\s+.*\.(?:bash_history|zsh_history)", "truncate history"),
]


def is_hard_sensitive_read_path(path: Path) -> tuple[bool, str]:
    """Hard block: path yang TIDAK PERNAH boleh dibaca agent, tidak bisa di-override."""
    str_path = str(path).lower()
    home = str(Path.home()).lower()

    for pattern in _HARD_READ_PATTERNS:
        if pattern in str_path:
            return True, f"blocked: sensitive file ({pattern})"
        if pattern in str_path.replace(home, "~"):
            return True, f"blocked: sensitive file ({pattern})"

    resolved = str(path.resolve())
    if resolved.startswith(f"{Path.home()}/.config/autokeren"):
        return True, "blocked: autokeren config directory"

    return False, ""


def is_soft_sensitive_read_path(path: Path) -> tuple[bool, str]:
    """Soft block: path yang sensitif tapi bisa diakses setelah izin user."""
    str_path = str(path).lower()
    home = str(Path.home()).lower()

    for pattern in _SOFT_READ_PATTERNS:
        if pattern in str_path:
            return True, f"sensitive file ({pattern}) — perlu izin"
        if pattern in str_path.replace(home, "~"):
            return True, f"sensitive file ({pattern}) — perlu izin"

    return False, ""


def is_sensitive_read_path(path: Path) -> tuple[bool, str]:
    """Backward-compat: return True jika path masuk hard ATAU soft block."""
    blocked, reason = is_hard_sensitive_read_path(path)
    if blocked:
        return True, reason
    return is_soft_sensitive_read_path(path)


def is_sensitive_write_path(path: Path) -> tuple[bool, str]:
    """Check if path is sensitive and should be blocked from writing."""
    str_path = str(path).lower()
    home = str(Path.home()).lower()

    for pattern in _SENSITIVE_WRITE_PATTERNS:
        if pattern in str_path:
            return True, f"blocked: sensitive write target ({pattern})"
        if pattern in str_path.replace(home, "~"):
            return True, f"blocked: sensitive write target ({pattern})"

    if str_path.startswith("/etc/") or str_path.startswith("/usr/") or str_path.startswith("/var/"):
        return True, "blocked: system directory"

    return False, ""


def is_dangerous_command(cmd: str, blocklist: list[str] | None = None) -> tuple[bool, str]:
    """Check for destructive, exfiltration, or injection shell commands.

    Hard block: irreversible operations, reverse shells, exfiltration.
    Returns (is_blocked, reason).
    """
    if blocklist:
        lowered = cmd.lower()
        for item in blocklist:
            if item.lower() in lowered:
                return True, f"blocked pattern: {item}"

    for pattern, desc in _HARD_BLOCK_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, f"blocked: {desc}"

    for pattern, desc in _EXFIL_PATTERNS:
        if re.search(pattern, cmd, re.IGNORECASE):
            return True, f"blocked: {desc}"

    return False, ""
