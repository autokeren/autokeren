"""Tests for Google Antigravity integration."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from autokeren.config import Config
from autokeren.models.antigravity import AntigravityModel, fetch_antigravity_models
from autokeren.models.router import ModelRouter


class TestAntigravityIntegration(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()
        self.cfg.auth.mode = "antigravity"
        self.cfg.cloudflare.primary_model = "Claude Sonnet 4.6 (Thinking)"
        self.cfg.cloudflare.secondary_model = "Gemini 3.5 Flash (Low)"
        # Patch TOKEN_PATH ke file temporary test
        from pathlib import Path
        self.token_path_patcher = patch("autokeren.models.google_auth.TOKEN_PATH", Path("scratch/test_token.json"))
        self.token_path_patcher.start()

    def tearDown(self):
        self.token_path_patcher.stop()
        from pathlib import Path
        test_token = Path("scratch/test_token.json")
        if test_token.exists():
            test_token.unlink()

    @patch("subprocess.run")
    def test_fetch_antigravity_models_success(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "Claude Sonnet 4.6 (Thinking)\nGemini 3.5 Flash (Low)\n"
        mock_run.return_value = mock_proc

        models = fetch_antigravity_models()
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["id"], "Claude Sonnet 4.6 (Thinking)")
        self.assertEqual(models[1]["id"], "Gemini 3.5 Flash (Low)")

    @patch("subprocess.run")
    def test_fetch_antigravity_models_failure_fallback(self, mock_run):
        mock_run.side_effect = Exception("failed to run")
        models = fetch_antigravity_models()
        self.assertGreater(len(models), 0)
        self.assertEqual(models[0]["provider"], "Google Antigravity")

    @patch("httpx.stream")
    @patch("autokeren.models.google_auth.load_token")
    @patch("autokeren.models.google_auth.refresh_access_token")
    @patch("shutil.which")
    def test_antigravity_model_complete(self, mock_which, mock_refresh, mock_load, mock_stream):
        mock_which.return_value = None
        mock_load.return_value = {"refresh_token": "mock_rt", "access_token": "mock_at"}
        mock_refresh.return_value = {"access_token": "new_mock_at"}

        # Mock streaming response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.raise_for_status = MagicMock()
        # Mock iter_lines data stream SSE
        mock_response.iter_lines.return_value = [
            b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"This is a response \"}]}}]}",
            b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"from Antigravity\"}]}}], \"usageMetadata\": {\"promptTokenCount\": 2, \"candidatesTokenCount\": 5, \"totalTokenCount\": 7}}"
        ]
        
        # Setup context manager mock
        mock_stream.return_value.__enter__.return_value = mock_response

        model = AntigravityModel(model_id="Claude Sonnet 4.6 (Thinking)")
        resp = model.complete(messages=[{"role": "user", "content": "hello"}])

        self.assertEqual(resp.content, "This is a response from Antigravity")
        self.assertEqual(resp.model_id, "Claude Sonnet 4.6 (Thinking)")
        self.assertEqual(resp.usage.total, 7)

    def test_router_initialization_antigravity(self):
        router = ModelRouter(cfg=self.cfg)
        self.assertEqual(len(router.models), 2)
        self.assertEqual(router.models[0].model_id, "Claude Sonnet 4.6 (Thinking)")
        self.assertEqual(router.models[1].model_id, "Gemini 3.5 Flash (Low)")
        self.assertEqual(router.models[0].__class__.__name__, "AntigravityModel")


if __name__ == "__main__":
    unittest.main()
