"""Dynamic tool loader to hot-load Python tools during runtime."""
from __future__ import annotations

import importlib.util
import inspect
from pathlib import Path
from typing import Any

from autokeren.memory import MemoryManager
from autokeren.tools.base import Tool, ToolRegistry


def load_dynamic_tools(project_root: Path, registry: ToolRegistry, cfg: Any, memory: MemoryManager) -> None:
    """Load dynamic tools from .ak-tools/ folder in the project root."""
    dynamic_dir = project_root / ".ak-tools"
    if not dynamic_dir.exists():
        try:
            dynamic_dir.mkdir(parents=True, exist_ok=True)
            readme = (
                "# Dynamic Tools Directory\n\n"
                "Semua file Python (`*.py`) di folder ini yang mendefinisikan subclass dari `Tool` "
                "akan dimuat secara otomatis oleh Autokeren saat startup.\n\n"
                "Contoh struktur tool:\n"
                "```python\n"
                "from autokeren.tools.base import Tool, ToolResult\n\n"
                "class CustomTool(Tool):\n"
                "    name = \"my_custom_tool\"\n"
                "    description = \"Deskripsi tool saya\"\n"
                "    parameters = {\"type\": \"object\", \"properties\": {}}\n\n"
                "    def __init__(self, project_root):\n"
                "        self.project_root = project_root\n\n"
                "    def run(self) -> ToolResult:\n"
                "        return ToolResult(output=\"Hello World!\")\n"
                "```\n"
            )
            (dynamic_dir / "README.md").write_text(readme, encoding="utf-8")
        except Exception:
            pass
        return

    for path in dynamic_dir.glob("*.py"):
        if path.name.startswith("_"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            if not spec or not spec.loader:
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            for attr_name in dir(module):
                cls = getattr(module, attr_name)
                if isinstance(cls, type) and issubclass(cls, Tool) and cls is not Tool:
                    # Dynamic instantiation based on constructor parameters
                    init_sig = inspect.signature(cls.__init__)
                    kwargs: dict[str, Any] = {}
                    for param_name, param in init_sig.parameters.items():
                        if param_name == "self":
                            continue
                        if param_name == "cfg":
                            kwargs["cfg"] = cfg
                        elif param_name in ("project_root", "path", "root"):
                            kwargs[param_name] = project_root if param.annotation == Path else str(project_root)
                        elif param_name == "memory":
                            kwargs["memory"] = memory
                    
                    try:
                        tool_instance = cls(**kwargs)
                        registry.register(tool_instance)
                    except Exception:
                        pass
        except Exception:
            pass
