"""Tests untuk hard/soft sensitive path detection dan ReadFileTool permission flow."""
from __future__ import annotations

from pathlib import Path

from autokeren.security import (
    is_hard_sensitive_read_path,
    is_sensitive_read_path,
    is_soft_sensitive_read_path,
)
from autokeren.tools.file import ReadFileTool


# ---------------------------------------------------------------------------
# is_hard_sensitive_read_path
# ---------------------------------------------------------------------------


class TestHardSensitiveReadPath:
    def test_ssh_key_blocked(self) -> None:
        blocked, reason = is_hard_sensitive_read_path(Path("/home/user/.ssh/id_rsa"))
        assert blocked is True
        assert "blocked" in reason

    def test_aws_credentials_blocked(self) -> None:
        blocked, _ = is_hard_sensitive_read_path(Path("/home/user/.aws/credentials"))
        assert blocked is True

    def test_pem_file_blocked(self) -> None:
        blocked, _ = is_hard_sensitive_read_path(Path("/certs/server.pem"))
        assert blocked is True

    def test_firebase_adminsdk_blocked(self) -> None:
        blocked, _ = is_hard_sensitive_read_path(Path("/project/firebase-adminsdk-key.json"))
        assert blocked is True

    def test_kube_config_blocked(self) -> None:
        blocked, _ = is_hard_sensitive_read_path(Path("/home/user/.kube/config"))
        assert blocked is True

    def test_env_file_NOT_hard_blocked(self) -> None:
        """File .env harus soft block, bukan hard block."""
        blocked, _ = is_hard_sensitive_read_path(Path("/project/.env"))
        assert blocked is False

    def test_config_yaml_NOT_hard_blocked(self) -> None:
        blocked, _ = is_hard_sensitive_read_path(Path("/project/config.yaml"))
        assert blocked is False

    def test_normal_python_file_allowed(self) -> None:
        blocked, _ = is_hard_sensitive_read_path(Path("/project/main.py"))
        assert blocked is False


# ---------------------------------------------------------------------------
# is_soft_sensitive_read_path
# ---------------------------------------------------------------------------


class TestSoftSensitiveReadPath:
    def test_env_file_soft_blocked(self) -> None:
        blocked, reason = is_soft_sensitive_read_path(Path("/project/.env"))
        assert blocked is True
        assert "perlu izin" in reason

    def test_env_production_soft_blocked(self) -> None:
        blocked, _ = is_soft_sensitive_read_path(Path("/project/.env.production"))
        assert blocked is True

    def test_config_yaml_soft_blocked(self) -> None:
        blocked, _ = is_soft_sensitive_read_path(Path("/project/config.yaml"))
        assert blocked is True

    def test_config_yml_soft_blocked(self) -> None:
        blocked, _ = is_soft_sensitive_read_path(Path("/project/config.yml"))
        assert blocked is True

    def test_npmrc_soft_blocked(self) -> None:
        blocked, _ = is_soft_sensitive_read_path(Path("/home/user/.npmrc"))
        assert blocked is True

    def test_ssh_NOT_soft_blocked(self) -> None:
        """SSH key harus hard block, bukan soft block."""
        blocked, _ = is_soft_sensitive_read_path(Path("/home/user/.ssh/id_rsa"))
        assert blocked is False

    def test_normal_file_allowed(self) -> None:
        blocked, _ = is_soft_sensitive_read_path(Path("/project/README.md"))
        assert blocked is False


# ---------------------------------------------------------------------------
# is_sensitive_read_path (backward compat)
# ---------------------------------------------------------------------------


class TestSensitiveReadPathCompat:
    def test_ssh_still_blocked(self) -> None:
        blocked, _ = is_sensitive_read_path(Path("/home/user/.ssh/id_rsa"))
        assert blocked is True

    def test_env_still_blocked(self) -> None:
        blocked, _ = is_sensitive_read_path(Path("/project/.env"))
        assert blocked is True

    def test_normal_file_still_allowed(self) -> None:
        blocked, _ = is_sensitive_read_path(Path("/project/app.py"))
        assert blocked is False


# ---------------------------------------------------------------------------
# ReadFileTool — needs_permission dan permission_desc
# ---------------------------------------------------------------------------


class TestReadFileToolPermission:
    def setup_method(self) -> None:
        self.tool = ReadFileTool(project_root=Path("/project"))

    def test_env_needs_permission(self) -> None:
        assert self.tool.needs_permission(path=".env") is True

    def test_config_yaml_needs_permission(self) -> None:
        assert self.tool.needs_permission(path="config.yaml") is True

    def test_normal_file_no_permission(self) -> None:
        assert self.tool.needs_permission(path="main.py") is False

    def test_ssh_no_permission_because_hard_block(self) -> None:
        """SSH key: bukan soft block, jadi needs_permission=False (hard block terjadi di run())."""
        assert self.tool.needs_permission(path="/home/user/.ssh/id_rsa") is False

    def test_permission_desc_contains_path(self) -> None:
        desc = self.tool.permission_desc(path=".env")
        assert ".env" in desc
        assert "sensitif" in desc

    def test_hard_block_returns_error_in_run(self, tmp_path: Path) -> None:
        tool = ReadFileTool(project_root=tmp_path)
        key_file = tmp_path / "id_rsa"
        key_file.write_text("fake key")
        result = tool.run(path=str(key_file))
        assert result.ok is False
        assert "blocked" in (result.error or "")

    def test_soft_block_readable_after_permission(self, tmp_path: Path) -> None:
        """Setelah permission di-approve (needs_permission sudah dicheck agent),
        run() bisa baca .env tanpa error."""
        tool = ReadFileTool(project_root=tmp_path)
        env_file = tmp_path / ".env"
        env_file.write_text("SECRET=abc123\n")
        result = tool.run(path=str(env_file))
        assert result.ok is True
        assert result.error is None
