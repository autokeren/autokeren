from __future__ import annotations

import base64
import json
from typing import Any

from autokeren.tools.camofox import CamofoxTool


class MockConfig:
    class camofox:
        user_id = "test_user"
        default_profile = "test_profile"


def test_camofox_tool_rpc_not_configured():
    cfg = MockConfig()
    tool = CamofoxTool(cfg)
    # Tanpa set_rpc_callback, run harus gagal secara anggun
    res = tool.run("navigate", url="https://example.com")
    assert not res.ok
    assert "not connected" in res.error


def test_camofox_tool_navigate():
    cfg = MockConfig()
    tool = CamofoxTool(cfg)
    
    called_action = None
    called_args = None
    
    def mock_rpc(action: str, args: dict[str, Any]) -> dict[str, Any]:
        nonlocal called_action, called_args
        called_action = action
        called_args = args
        return {"ok": True, "output": {"status": "navigated"}}
        
    tool.set_rpc_callback(mock_rpc)
    res = tool.run("navigate", url="https://google.com")
    
    assert res.ok
    assert called_action == "navigate"
    assert called_args["url"] == "https://google.com"
    assert res.output["status"] == "navigated"


def test_camofox_tool_net_start_and_get():
    cfg = MockConfig()
    tool = CamofoxTool(cfg)
    
    eval_expression = ""
    
    def mock_rpc(action: str, args: dict[str, Any]) -> dict[str, Any]:
        nonlocal eval_expression
        if action == "eval":
            eval_expression = args.get("expression", "")
            # Simulasi output dari JS network logs
            if "window.__networkLogs" in eval_expression and "JSON.stringify" in eval_expression:
                return {
                    "ok": True, 
                    "output": {
                        "result": json.dumps([
                            {"type": "fetch", "url": "https://api.com", "method": "GET", "status": 200}
                        ])
                    }
                }
            return {"ok": True, "output": {"result": "interceptor_injected"}}
        return {"ok": False, "error": "unknown action"}
        
    tool.set_rpc_callback(mock_rpc)
    
    # 1. Test net_start
    res_start = tool.run("net_start")
    assert res_start.ok
    assert "window.__cf_interceptor" in eval_expression
    
    # 2. Test net_get
    res_get = tool.run("net_get")
    assert res_get.ok
    assert res_get.output["count"] == 1
    assert res_get.output["logs"][0]["url"] == "https://api.com"


def test_camofox_tool_screenshot(tmp_path):
    cfg = MockConfig()
    tool = CamofoxTool(cfg)
    
    dummy_bytes = b"dummy_png_data"
    dummy_b64 = base64.b64encode(dummy_bytes).decode()
    
    def mock_rpc(action: str, args: dict[str, Any]) -> dict[str, Any]:
        if action == "screenshot":
            return {"ok": True, "output": {"bytes": len(dummy_bytes), "base64": dummy_b64}}
        return {"ok": False, "error": "unknown"}
        
    tool.set_rpc_callback(mock_rpc)
    
    save_file = tmp_path / "test_screenshot.png"
    res = tool.run("screenshot", save_path=str(save_file))
    
    assert res.ok
    assert save_file.exists()
    assert save_file.read_bytes() == dummy_bytes
    assert res.output["screenshot_path"] == str(save_file.resolve())


def test_camofox_tool_on_output():
    cfg = MockConfig()
    tool = CamofoxTool(cfg)
    
    outputs = []
    def mock_on_output(line: str) -> None:
        outputs.append(line)
        
    def mock_rpc(action: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "output": "ok"}
        
    tool.set_rpc_callback(mock_rpc)
    res = tool.run("navigate", url="https://google.com", on_output=mock_on_output)
    
    assert res.ok
    assert len(outputs) == 1
    assert "Navigasi ke https://google.com" in outputs[0]


def test_camofox_tool_screenshot_default_path():
    cfg = MockConfig()
    tool = CamofoxTool(cfg)
    
    dummy_bytes = b"dummy_png_data"
    dummy_b64 = base64.b64encode(dummy_bytes).decode()
    
    def mock_rpc(action: str, args: dict[str, Any]) -> dict[str, Any]:
        return {"ok": True, "output": {"bytes": len(dummy_bytes), "base64": dummy_b64}}
        
    tool.set_rpc_callback(mock_rpc)
    res = tool.run("screenshot", save_path="")
    assert res.ok
    assert "/tmp/autokeren-camofox-" in res.output["screenshot_path"]
