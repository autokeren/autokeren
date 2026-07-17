"""Tests for OpenAI API integration."""
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from autokeren.config import Config
from autokeren.models.openai import OpenAIModel, fetch_openai_models
from autokeren.models.router import ModelRouter


class TestOpenAIIntegration(unittest.TestCase):
    def setUp(self):
        self.cfg = Config()
        self.cfg.auth.mode = "openai"
        self.cfg.auth.openai_api_key = "sk-proj-mock123"
        self.cfg.cloudflare.primary_model = "gpt-5.6"
        self.cfg.cloudflare.secondary_model = "gpt-4o"

    def test_fetch_openai_models(self):
        models = fetch_openai_models(self.cfg)
        self.assertTrue(len(models) >= 4)
        ids = [m["id"] for m in models]
        self.assertIn("gpt-5.6", ids)
        self.assertIn("gpt-4o-mini", ids)

    @patch("httpx.post")
    def test_openai_model_complete_non_stream(self, mock_post):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Hello ajat!",
                        "tool_calls": [
                            {
                                "id": "call_abc",
                                "type": "function",
                                "function": {
                                    "name": "write_file",
                                    "arguments": '{"path": "hello.txt", "content": "world"}'
                                }
                            }
                        ]
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 15,
                "total_tokens": 25
            }
        }
        mock_post.return_value = mock_response

        model = OpenAIModel(model_id="gpt-5.6", api_key="sk-proj-mock123")
        res = model.complete([{"role": "user", "content": "hi"}], tools=[])

        self.assertEqual(res.content, "Hello ajat!")
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.tool_calls[0].name, "write_file")
        self.assertEqual(res.tool_calls[0].arguments["path"], "hello.txt")
        self.assertEqual(res.usage.total, 25)

    @patch("httpx.stream")
    def test_openai_model_complete_stream(self, mock_stream):
        # Mock streaming chunks
        chunks = [
            b'data: {"choices": [{"delta": {"role": "assistant", "content": "Hello"}}]}\n',
            b'data: {"choices": [{"delta": {"content": " ajat!"}}]}\n',
            b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_xyz", "function": {"name": "run_shell"}}]}}]}\n',
            b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": "{\\"command\\":"}}]}}]}\n',
            b'data: {"choices": [{"delta": {"tool_calls": [{"index": 0, "function": {"arguments": " \\"ls\\"}"}}]}}]}\n',
            b"data: [DONE]\n"
        ]

        class MockStreamContext:
            def __enter__(self):
                mock_r = MagicMock()
                mock_r.status_code = 200
                mock_r.iter_lines.return_value = chunks
                return mock_r
            def __exit__(self, exc_type, exc_val, exc_tb):
                pass

        mock_stream.return_value = MockStreamContext()

        accumulated = []
        def on_chunk(text: str):
            accumulated.append(text)

        model = OpenAIModel(model_id="gpt-5.6", api_key="sk-proj-mock123")
        res = model.complete([{"role": "user", "content": "hi"}], on_chunk=on_chunk)

        self.assertEqual(res.content, "Hello ajat!")
        self.assertEqual("".join(accumulated), "Hello ajat!")
        self.assertEqual(len(res.tool_calls), 1)
        self.assertEqual(res.tool_calls[0].name, "run_shell")
        self.assertEqual(res.tool_calls[0].arguments["command"], "ls")

    def test_router_initialization_openai(self):
        router = ModelRouter(self.cfg)
        self.assertEqual(len(router.models), 2)
        self.assertEqual(router.models[0].auth_mode, "openai")
        self.assertEqual(router.models[0].model_id, "gpt-5.6")
        self.assertEqual(router.models[1].model_id, "gpt-4o")
