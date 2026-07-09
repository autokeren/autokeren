"""Tests for Google AI Studio integration."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from autokeren.config import Config
from autokeren.models.aistudio import AIStudioModel, fetch_aistudio_models
from autokeren.models.router import ModelRouter


class TestAIStudioIntegration(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()
        self.cfg.auth.mode = "aistudio"
        self.cfg.auth.gemini_api_key = "mock_key_123"
        self.cfg.cloudflare.primary_model = "gemini-3.5-flash"
        self.cfg.cloudflare.secondary_model = "gemini-3.5-pro"

    @patch("httpx.get")
    def test_fetch_aistudio_models_success(self, mock_get):
        # Mock successful API response from Google
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "models/gemini-3.5-flash",
                    "displayName": "Gemini 1.5 Flash",
                    "description": "Flash model",
                    "inputTokenLimit": 1048576,
                    "supportedGenerationMethods": ["generateContent", "countTokens"]
                },
                {
                    "name": "models/gemini-3.5-pro",
                    "displayName": "Gemini 1.5 Pro",
                    "description": "Pro model",
                    "inputTokenLimit": 2097152,
                    "supportedGenerationMethods": ["generateContent"]
                },
                {
                    "name": "models/embedding-001",
                    "displayName": "Embedding Model",
                    "supportedGenerationMethods": ["embedContent"]
                }
            ]
        }
        mock_get.return_value = mock_response

        models = fetch_aistudio_models(self.cfg)
        
        # Should filter out embedding-001 since it doesn't support generateContent
        self.assertEqual(len(models), 2)
        self.assertEqual(models[0]["id"], "gemini-3.5-flash")
        self.assertEqual(models[0]["name"], "Gemini 1.5 Flash")
        self.assertEqual(models[0]["provider"], "Google AI Studio")
        self.assertEqual(models[1]["id"], "gemini-3.5-pro")

    @patch("httpx.get")
    def test_fetch_aistudio_models_failure_fallback(self, mock_get):
        mock_get.side_effect = Exception("failed request")
        
        models = fetch_aistudio_models(self.cfg)
        
        # Should return fallback models
        self.assertGreater(len(models), 0)
        self.assertEqual(models[0]["id"], "gemini-3.5-flash")
        self.assertEqual(models[0]["provider"], "Google AI Studio")

    @patch("httpx.post")
    def test_aistudio_model_complete_non_stream(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Hello, I am Gemini!"}]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 6,
                "totalTokenCount": 11
            }
        }
        mock_post.return_value = mock_response

        model = AIStudioModel(model_id="gemini-1.5-flash", api_key="test_key")
        resp = model.complete(messages=[
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
            {"role": "user", "content": "how are you?"}
        ])

        self.assertEqual(resp.content, "Hello, I am Gemini!")
        self.assertEqual(resp.usage.total, 11)
        self.assertEqual(resp.model_id, "gemini-1.5-flash")

        # Verify payload contains systemInstruction and merged contents
        args, kwargs = mock_post.call_args
        payload = kwargs["json"]
        self.assertIn("contents", payload)
        # 3 alternating messages
        self.assertEqual(len(payload["contents"]), 3)
        self.assertEqual(payload["contents"][0]["role"], "user")
        self.assertEqual(payload["contents"][1]["role"], "model")

    @patch("httpx.stream")
    def test_aistudio_model_complete_stream(self, mock_stream):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.iter_lines.return_value = [
            b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"Streaming \"}]}}]}",
            b"data: {\"candidates\": [{\"content\": {\"parts\": [{\"text\": \"response\"}]}}], \"usageMetadata\": {\"promptTokenCount\": 2, \"candidatesTokenCount\": 2, \"totalTokenCount\": 4}}"
        ]
        mock_stream.return_value.__enter__.return_value = mock_response

        chunks = []
        def on_chunk(text):
            chunks.append(text)

        model = AIStudioModel(model_id="gemini-1.5-flash", api_key="test_key")
        resp = model.complete(
            messages=[{"role": "user", "content": "hello"}],
            on_chunk=on_chunk
        )

        self.assertEqual(resp.content, "Streaming response")
        self.assertEqual(chunks, ["Streaming ", "response"])
        self.assertEqual(resp.usage.total, 4)

    def test_router_initialization_aistudio(self):
        router = ModelRouter(cfg=self.cfg)
        self.assertEqual(len(router.models), 2)
        # Resolved model IDs
        self.assertEqual(router.models[0].model_id, "gemini-3.5-flash")
        self.assertEqual(router.models[1].model_id, "gemini-3.5-pro")
        self.assertEqual(router.models[0].__class__.__name__, "AIStudioModel")

    def test_model_id_resolution(self):
        # Should resolve Cloudflare model IDs to Gemini model IDs
        model1 = AIStudioModel(model_id="kimi-code", api_key="test_key")
        self.assertEqual(model1.model_id, "gemini-3.5-pro")

        model2 = AIStudioModel(model_id="kimi-2.6", api_key="test_key")
        self.assertEqual(model2.model_id, "gemini-3.5-flash")

        model3 = AIStudioModel(model_id="gemini-3.5-flash", api_key="test_key")
        self.assertEqual(model3.model_id, "gemini-3.5-flash")

    def test_parse_text_tool_calls_single(self):
        from autokeren.models.aistudio import _parse_text_tool_calls

        content = '[TOOL_CALL name=list_files]\n{"path": "src", "recursive": true}'
        cleaned, calls = _parse_text_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "list_files")
        self.assertEqual(calls[0].arguments, {"path": "src", "recursive": True})

    def test_parse_text_tool_calls_with_surrounding_text(self):
        from autokeren.models.aistudio import _parse_text_tool_calls

        content = (
            "Saya akan membaca file tersebut.\n"
            '[TOOL_CALL name=read_file]\n{"path": "main.py"}\n'
            "Lalu analisis."
        )
        cleaned, calls = _parse_text_tool_calls(content)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].name, "read_file")
        self.assertEqual(calls[0].arguments, {"path": "main.py"})
        self.assertIn("Saya akan", cleaned)
        self.assertIn("Lalu analisis", cleaned)

    def test_parse_text_tool_calls_multiple(self):
        from autokeren.models.aistudio import _parse_text_tool_calls

        content = (
            '[TOOL_CALL name=list_files]\n{"path": "."}\n'
            '[TOOL_CALL name=read_file]\n{"path": "README.md"}'
        )
        cleaned, calls = _parse_text_tool_calls(content)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].name, "list_files")
        self.assertEqual(calls[1].name, "read_file")

    def test_parse_text_tool_calls_none(self):
        from autokeren.models.aistudio import _parse_text_tool_calls

        content = "Halo, ini pesan biasa tanpa tool call."
        cleaned, calls = _parse_text_tool_calls(content)
        self.assertEqual(len(calls), 0)
        self.assertEqual(cleaned, content)

    @patch("httpx.post")
    def test_aistudio_fallback_text_tool_call(self, mock_post):
        """Model output [TOOL_CALL] sebagai text → harus ter-parse jadi ToolCall."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": '[TOOL_CALL name=list_files]\n{"path": "src", "recursive": true}'}
                        ]
                    }
                }
            ],
            "usageMetadata": {
                "promptTokenCount": 5,
                "candidatesTokenCount": 10,
                "totalTokenCount": 15,
            },
        }
        mock_post.return_value = mock_response

        model = AIStudioModel(model_id="gemini-3.5-flash", api_key="test_key")
        resp = model.complete(messages=[{"role": "user", "content": "list files"}])

        self.assertEqual(len(resp.tool_calls), 1)
        self.assertEqual(resp.tool_calls[0].name, "list_files")
        self.assertEqual(resp.tool_calls[0].arguments, {"path": "src", "recursive": True})


if __name__ == "__main__":
    unittest.main()
