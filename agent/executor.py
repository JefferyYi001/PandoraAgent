"""
ToolCallLoop - Drives the tool-call execution cycle with LLM
"""

import json
import re

import httpx

from agent.context import AgentContext, AgentState
from agent.tools.manager import ToolManager
from agent.prompt import PromptBuilder
from agent.skills.manager import SkillManager
from config.settings import get_settings
from utils.logger import logger


class ToolCallLoop:
    """Executes tool calls in a loop driven by LLM responses"""

    def __init__(self, context: AgentContext):
        self.context = context
        self.tool_manager = ToolManager()
        self.skill_manager = SkillManager()
        self.settings = get_settings()
        self._running = False

    async def run_step(self) -> AgentState | None:
        """Execute one LLM-driven tool call step. Returns new state or None to continue."""
        if not self._running:
            return None

        # Build prompt
        tool_schemas = self.tool_manager.get_schemas()
        skills_prompt = self.skill_manager.generate_prompt()
        prompt = PromptBuilder.build(self.context, tool_schemas, skills_prompt)

        # Call LLM
        response = await self._call_llm(prompt)
        if not response:
            self.context.consecutive_failures += 1
            if self.context.consecutive_failures >= 3:
                logger.error("LLM failed 3 times, returning to IDLE")
                return AgentState.IDLE
            return None

        self.context.consecutive_failures = 0

        # Parse tool call
        tool_call = self._parse_tool_call(response)
        if not tool_call:
            logger.warning(f"Failed to parse tool call from LLM response: {response[:100]}")
            return None

        # Execute tool
        tool_name = tool_call["tool"]
        tool_params = tool_call.get("params", {})
        logger.info(f"Executing tool: {tool_name} with params: {tool_params}")

        try:
            tool = self.tool_manager.get_tool(tool_name)
            result = tool.execute(tool_params)
            self.context.record_action(tool_name, result.output, result.data)

            if result.success:
                logger.info(f"Tool {tool_name} succeeded: {result.output[:100] if result.output else 'ok'}")
            else:
                logger.warning(f"Tool {tool_name} failed: {result.error}")

        except Exception as e:
            logger.error(f"Tool {tool_name} exception: {e}")
            self.context.record_action(tool_name, f"Error: {e}")
            return None

        return None

    async def _call_llm(self, prompt: str) -> str | None:
        """Call LLM API and return response content"""
        try:
            response = httpx.post(
                f"{self.settings.llm_api_url}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.settings.llm_api_key}",
                },
                json={
                    "model": self.settings.llm_model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": self.settings.llm_max_tokens,
                    "temperature": self.settings.llm_temperature,
                },
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM API call failed: {e}")
            return None

    @staticmethod
    def _parse_tool_call(response: str) -> dict | None:
        """Extract JSON tool call from LLM response"""
        # Try direct JSON parse
        try:
            parsed = json.loads(response)
            if "tool" in parsed:
                return parsed
        except json.JSONDecodeError:
            pass

        # Try to find JSON in text
        match = re.search(r"\{[^{}]*\"tool\"[^{}]*\}", response, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

        return None

    def start(self) -> None:
        self._running = True

    def stop(self) -> None:
        self._running = False
