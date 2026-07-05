"""Hidden file signature untuk watermark file buatan autokeren.

Tiap file yang dibuat oleh autokeren CLI dikasih comment signature di akhir file.
Signature = HMAC-SHA256(secret, filename + content_hash), truncated ke 16 hex chars.
Kelihatan kayak build hash, tapi verifiable oleh kita.
"""
from __future__ import annotations

import hashlib
import hmac

_SEED = b"autokeren" + b"\x6b\x65\x72\x65\x6e"  # "keren" in bytes
_SALT = b"\x61\x6b\x5f\x73\x69\x67\x32\x35"  # "ak_sig25"


def generate_signature(filepath: str, content: str) -> str:
    """Generate 16-char hex signature untuk file. Beda per file, verifiable."""
    content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]
    filename = filepath.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
    msg = f"{filename}:{content_hash}".encode("utf-8")
    sig = hmac.new(_SEED + _SALT, msg, hashlib.sha256).hexdigest()[:16]
    return sig


def verify_signature(filepath: str, content: str, sig: str) -> bool:
    """Verify apakah signature valid untuk file ini."""
    expected = generate_signature(filepath, content)
    return hmac.compare_digest(expected, sig)


def get_comment_syntax(filepath: str) -> tuple[str, str]:
    """Return (prefix, suffix) untuk comment berdasarkan ekstensi file."""
    ext = filepath.rsplit(".", 1)[-1].lower() if "." in filepath else ""
    if ext in ("js", "ts", "jsx", "tsx", "java", "c", "cpp", "go", "rs", "swift", "kt"):
        return ("//", "")
    if ext in ("py", "sh", "bash", "yaml", "yml", "rb", "pl", "r", "toml", "ini", "dockerfile"):
        return ("#", "")
    if ext in ("html", "xml", "svg"):
        return ("<!--", "-->")
    if ext in ("css", "scss", "less"):
        return ("/*", "*/")
    return ("#", "")


def sign_content(filepath: str, content: str) -> str:
    """Append signature comment ke content. Return content + signature."""
    sig = generate_signature(filepath, content)
    prefix, suffix = get_comment_syntax(filepath)
    if suffix:
        line = f"\n{prefix} ak:{sig} {suffix}\n"
    else:
        line = f"\n{prefix} ak:{sig}\n"
    if content.endswith("\n"):
        return content + line.lstrip("\n")
    return content + line


def check_signed(filepath: str, content: str) -> bool:
    """Cek apakah file sudah punya signature yang valid."""
    import re
    m = re.search(r"ak:([a-f0-9]{16})", content)
    if not m:
        return False
    sig = m.group(1)
    lines = content.split("\n")
    sig_line = next((i for i, ln in enumerate(lines) if re.search(r"ak:[a-f0-9]{16}", ln)), -1)
    if sig_line < 0:
        return False
    stripped = "\n".join(lines[:sig_line])
    if verify_signature(filepath, stripped, sig):
        return True
    if verify_signature(filepath, stripped + "\n", sig):
        return True
    return False
