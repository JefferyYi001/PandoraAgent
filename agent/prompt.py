"""
PromptBuilder - Assemble LLM prompt from tools, skills, context, and system instructions
"""

from agent.context import AgentContext


class PromptBuilder:
    """Builds the complete prompt for LLM decision-making"""

    @staticmethod
    def build(context: AgentContext, tool_schemas: list[dict], skills_prompt: str = "") -> str:
        """Assemble full prompt for THINKING state"""
        parts = []

        # System instructions
        parts.append(PromptBuilder._system_prompt())

        # Current state context
        parts.append(PromptBuilder._state_context(context))

        # Tool descriptions
        if tool_schemas:
            parts.append(PromptBuilder._tool_context(tool_schemas))

        # Skills
        if skills_prompt:
            parts.append(skills_prompt)

        # Decision request
        parts.append(PromptBuilder._decision_request())

        return "\n\n".join(parts)

    @staticmethod
    def _system_prompt() -> str:
        return """You are a WeChat customer service assistant agent. You operate a WeChat desktop client via visual automation (screen recognition, mouse clicks, keyboard input).

Your goal is to:
1. Monitor for new customer messages
2. Extract and understand messages
3. Generate appropriate replies
4. Maintain natural, human-like interaction patterns

You make decisions by calling tools. Each tool performs a specific action (detect messages, extract text, send replies, etc.)."""

    @staticmethod
    def _state_context(context: AgentContext) -> str:
        lines = ["## Current State"]
        lines.append(f"- Current state: {context.state.value}")
        if context.active_contact:
            lines.append(f"- Active contact: {context.active_contact}")
        if context.last_message:
            lines.append(f"- Last message: {context.last_message[:200]}")
        if context.last_message_time:
            import time
            elapsed = time.time() - context.last_message_time
            lines.append(f"- Time since last message: {elapsed:.0f}s")

        recent = context.get_recent_actions(5)
        if recent:
            lines.append("- Recent actions:")
            for action in recent:
                lines.append(f"  - {action['action']}: {action['result']}")

        return "\n".join(lines)

    @staticmethod
    def _tool_context(tool_schemas: list[dict]) -> str:
        lines = ["## Available Tools"]
        lines.append("Use these tools to interact with WeChat. Choose the most appropriate tool based on the current situation.")
        lines.append("")
        for schema in tool_schemas:
            lines.append(f"### {schema['name']}")
            lines.append(f"Description: {schema['description']}")
            params = schema.get("parameters", {}).get("properties", {})
            if params:
                lines.append("Parameters:")
                for pname, pinfo in params.items():
                    desc = pinfo.get("description", "")
                    lines.append(f"  - {pname}: {desc}")
            lines.append("")
        return "\n".join(lines)

    @staticmethod
    def _decision_request() -> str:
        return """## Your Task
Based on the current state and available tools, decide what to do next.

Respond with a tool call in this format:
{"tool": "tool_name", "params": {<parameters>}}

Think step by step about the situation before choosing a tool."""
