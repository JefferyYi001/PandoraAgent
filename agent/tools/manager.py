"""
Simplified ToolManager - loads tools from __all__ list, lazy instantiation
"""

import importlib
import re
from typing import Type

from agent.tools.base_tool import BaseTool


def _camel_to_snake(name: str) -> str:
    s = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s).lower()


class ToolManager:
    _instance = None
    _tools: dict[str, Type[BaseTool]] = {}
    _instances: dict[str, BaseTool] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def reset(cls):
        cls._instance = None
        cls._tools = {}
        cls._instances = {}

    def load_tools(self) -> None:
        from agent.tools import __all__
        module_path = "agent.tools"
        for tool_name in __all__:
            module_name = _camel_to_snake(tool_name)
            module = importlib.import_module(f"{module_path}.{module_name}")
            tool_cls = getattr(module, tool_name)
            if issubclass(tool_cls, BaseTool):
                self._tools[tool_cls.name or tool_name] = tool_cls

    def get_tool(self, name: str) -> BaseTool:
        if name not in self._instances:
            if name not in self._tools:
                raise KeyError(f"Tool '{name}' not found")
            self._instances[name] = self._tools[name]()
        return self._instances[name]

    def list_tools(self) -> list[BaseTool]:
        return [self.get_tool(name) for name in self._tools]

    def get_schemas(self) -> list[dict]:
        return [self.get_tool(name).to_schema() for name in self._tools]
