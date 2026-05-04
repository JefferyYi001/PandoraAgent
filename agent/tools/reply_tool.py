"""
ReplyTool - Generate LLM reply for received message
Calls OpenAI-compatible chat completions API with system prompt and context
"""

import json
import httpx

from agent.tools.base_tool import BaseTool, ToolResult
from utils.logger import logger


class ReplyTool(BaseTool):
    name = "reply"
    description = "Generate an LLM reply for the received message. Uses configured LLM API with system prompt for persona."
    params = {
        "type": "object",
        "properties": {
            "message": {"type": "string", "description": "The received message text"},
            "context": {
                "type": "array", "items": {"type": "string"},
                "description": "Recent conversation context for continuity",
            },
            "system_prompt": {"type": "string", "description": "Optional override system prompt"},
        },
        "required": ["message"],
    }

    def execute(self, params: dict | None = None) -> ToolResult:
        p = params or {}
        if "message" not in p:
            return ToolResult.fail("message is required")

        from config.settings import get_settings
        from config.defaults import get_defaults
        settings = get_settings()
        defaults = get_defaults()

        llm_config = defaults.get("agent", {}).get("llm", {})
        max_tokens = llm_config.get("max_tokens", settings.llm_max_tokens)
        temperature = llm_config.get("temperature", settings.llm_temperature)

        messages = []
        if p.get("system_prompt"):
            messages.append({"role": "system", "content": p["system_prompt"]})
        else:
            messages.append({
                "role": "system",
                "content": self._default_system_prompt(),
            })

        # Add conversation context
        for ctx_msg in p.get("context", []):
            messages.append({"role": "user", "content": ctx_msg})

        messages.append({"role": "user", "content": p["message"]})

        try:
            response = httpx.post(
                f"{settings.llm_api_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {settings.llm_api_key}",
                },
                json={
                    "model": settings.llm_model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
            logger.info(f"LLM reply generated: {reply[:50]}...")
            return ToolResult.ok(reply, data={"reply": reply, "model": settings.llm_model})
        except httpx.TimeoutException:
            return ToolResult.fail("LLM API request timed out")
        except httpx.HTTPStatusError as e:
            return ToolResult.fail(f"LLM API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            return ToolResult.fail(f"LLM API exception: {e}")

    def _default_system_prompt(self) -> str:
        from config.defaults import get_defaults
        defaults = get_defaults()
        return defaults.get("agent", {}).get("llm", {}).get(
            "system_prompt",
            "You are a helpful customer service assistant. Respond naturally in Chinese, "
            "keep replies concise (50-80 characters), use colloquial and friendly tone."
        )
