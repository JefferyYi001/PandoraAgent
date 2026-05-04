"""
Simplified BaseTool for WechatAssistantAgent
Stripped from CowAgent: removed POST_PROCESS phase, keep core execute interface
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    output: str = ""
    error: str = ""
    data: dict = field(default_factory=dict)

    @classmethod
    def ok(cls, output: str = "", **kwargs) -> "ToolResult":
        return cls(success=True, output=output, **kwargs)

    @classmethod
    def fail(cls, error: str = "", **kwargs) -> "ToolResult":
        return cls(success=False, error=error, **kwargs)


class BaseTool(ABC):
    name: str = ""
    description: str = ""
    params: dict = {}

    @abstractmethod
    def execute(self, params: dict | None = None) -> ToolResult:
        ...

    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.params or {"type": "object", "properties": {}},
        }
