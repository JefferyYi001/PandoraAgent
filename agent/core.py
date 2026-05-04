"""
WechatAgent - FSM state machine + LLM hybrid decision making
Deterministic ops (sentry/extract/send/window) via state machine
Decision ops (THINKING) via LLM tool-call loop
"""

import time
import asyncio
import random

from agent.context import AgentContext, AgentState
from agent.tools.manager import ToolManager
from agent.skills.manager import SkillManager
from agent.executor import ToolCallLoop
from config.settings import get_settings
from config.defaults import get_defaults
from utils.logger import logger


class WechatAgent:
    """Main agent orchestrating the FSM state machine"""

    def __init__(self):
        self.context = AgentContext()
        self.tool_manager = ToolManager()
        self.skill_manager = SkillManager()
        self.settings = get_settings()
        self.defaults = get_defaults()
        self.loop = ToolCallLoop(self.context)
        self._running = False

    def initialize(self) -> None:
        """Load tools, skills, and prepare for operation"""
        self.tool_manager.load_tools()
        self.skill_manager.load_skills()
        logger.info(f"Agent initialized with {len(self.tool_manager.list_tools())} tools, "
                     f"{len(self.skill_manager.list_skills())} skills")

    async def run(self) -> None:
        """Main agent loop"""
        self._running = True
        self.loop.start()
        self.context.transition(AgentState.IDLE)
        logger.info("Agent started")

        polling = self.defaults.get("vision", {}).get("polling", {})
        min_interval = polling.get("interval", 3)
        max_interval = polling.get("max_interval", 8)

        while self._running:
            try:
                new_state = await self._process_state()
                if new_state:
                    self.context.transition(new_state)

                await asyncio.sleep(random.uniform(min_interval, max_interval))
            except Exception as e:
                logger.error(f"Agent loop error: {e}")
                self.context.consecutive_failures += 1
                if self.context.consecutive_failures >= 5:
                    logger.error("Too many consecutive failures, stopping")
                    await self.stop()
                self.context.transition(AgentState.IDLE)

        self.loop.stop()
        logger.info("Agent stopped")

    async def _process_state(self) -> AgentState | None:
        """Process current FSM state and return next state or None"""
        state = self.context.state

        if state == AgentState.IDLE:
            return await self._state_idle()
        elif state == AgentState.SENTRY_OK:
            return await self._state_sentry_ok()
        elif state == AgentState.LOCKING:
            return await self._state_locking()
        elif state == AgentState.EXTRACTING:
            return await self._state_extracting()
        elif state == AgentState.THINKING:
            return await self._state_thinking()
        elif state == AgentState.REPLYING:
            return await self._state_replying()
        elif state == AgentState.MONITOR:
            return await self._state_monitor()
        elif state == AgentState.IGNORE:
            return await self._state_ignore()
        elif state == AgentState.CLEANUP:
            return await self._state_cleanup()
        return None

    async def _state_idle(self) -> AgentState | None:
        """Poll sentry for taskbar flashing"""
        from agent.tools.sentry_tool import SentryTool
        tool = SentryTool()
        config = self.defaults.get("wechat", {}).get("taskbar_region")
        if not config:
            logger.warning("No taskbar_region configured")
            return None

        result = tool.execute({"taskbar_region": config})
        if result.success and result.data.get("state") == "alert":
            logger.info("Sentry detected alert!")
            return AgentState.SENTRY_OK
        return None

    async def _state_sentry_ok(self) -> AgentState | None:
        """Restore WeChat window and proceed to locking"""
        from agent.tools.window_tool import WindowTool
        tool = WindowTool()
        result = tool.execute({"action": "restore"})
        if result.success:
            return AgentState.LOCKING
        logger.warning(f"Failed to restore window: {result.error}")
        return AgentState.IDLE

    async def _state_locking(self) -> AgentState | None:
        """Check for red dots to identify which contact has new messages"""
        from agent.tools.red_dot_tool import RedDotTool
        tool = RedDotTool()
        config = self.defaults.get("wechat", {}).get("chat_list_region")
        if not config:
            logger.warning("No chat_list_region configured")
            return AgentState.IDLE

        result = tool.execute({"chat_list_region": config})
        if result.success and result.data.get("count", 0) > 0:
            dots = result.data["dots"]
            dot = dots[0]
            from automation.humanize import human_click, human_sleep
            human_click(dot[0] + 130, dot[1])
            human_sleep(0.5, 1.0)
            logger.info(f"Locked target contact via red dot at {dot}")
            return AgentState.EXTRACTING
        logger.info("No red dots found, checking for new messages on current chat")
        return AgentState.EXTRACTING

    async def _state_extracting(self) -> AgentState | None:
        """Extract messages from current chat"""
        from agent.tools.message_extract_tool import MessageExtractTool
        tool = MessageExtractTool()
        config = self.defaults.get("wechat", {}).get("chat_content_region")
        if not config:
            logger.warning("No chat_content_region configured")
            return AgentState.IDLE

        result = tool.execute({"chat_content_region": config})
        if result.success:
            messages = result.data.get("messages", [])
            if messages:
                self.context.last_message = messages[-1]
                self.context.last_message_time = time.time()
                logger.info(f"Extracted messages: {messages}")
                return AgentState.THINKING
            else:
                logger.info("No new messages to process")
                return AgentState.CLEANUP
        logger.warning(f"Extraction failed: {result.error}")
        return AgentState.IDLE

    async def _state_thinking(self) -> AgentState | None:
        """LLM decides: reply, monitor, or ignore"""
        return await self.loop.run_step() or AgentState.REPLYING

    async def _state_replying(self) -> AgentState | None:
        """Generate and send reply"""
        from agent.tools.reply_tool import ReplyTool
        reply_tool = ReplyTool()
        result = reply_tool.execute({
            "message": self.context.last_message,
            "context": [],
        })

        if result.success:
            reply = result.data.get("reply", "")
            from agent.tools.send_tool import SendTool
            config = self.defaults.get("wechat", {}).get("input_box_region")
            if config:
                center = (config[0] + config[2] // 2, config[1] + config[3] // 2)
                send_tool = SendTool()
                send_result = send_tool.execute({
                    "input_box_center": list(center),
                    "text": reply,
                })
                if send_result.success:
                    return AgentState.MONITOR
        logger.warning(f"Reply failed: {result.error}")
        return AgentState.MONITOR

    async def _state_monitor(self) -> AgentState | None:
        """Stay on current chat, wait for more messages or timeout"""
        timeout = self.defaults.get("agent", {}).get("monitor_timeout", 300)
        elapsed = time.time() - self.context.last_message_time

        if elapsed > timeout:
            logger.info(f"Monitor timeout ({timeout}s), returning to cleanup")
            return AgentState.CLEANUP

        from agent.tools.message_extract_tool import MessageExtractTool
        config = self.defaults.get("wechat", {}).get("chat_content_region")
        if not config:
            return AgentState.CLEANUP

        tool = MessageExtractTool()
        result = tool.execute({"chat_content_region": config})
        if result.success and result.data.get("messages"):
            self.context.last_message = result.data["messages"][-1]
            self.context.last_message_time = time.time()
            return AgentState.THINKING

        return None  # Continue monitoring

    async def _state_ignore(self) -> AgentState | None:
        """Ignore current message, return to cleanup"""
        logger.info("Ignoring current message")
        return AgentState.CLEANUP

    async def _state_cleanup(self) -> AgentState | None:
        """Minimize window and return to idle"""
        from agent.tools.window_tool import WindowTool
        tool = WindowTool()
        tool.execute({"action": "minimize"})
        self.context.reset_session()
        return AgentState.IDLE

    async def stop(self) -> None:
        """Stop the agent loop"""
        self._running = False
        self.loop.stop()

    def get_status(self) -> dict:
        """Get current agent status for API/UI"""
        return {
            "running": self._running,
            "state": self.context.state.value,
            "active_contact": self.context.active_contact,
            "last_message": self.context.last_message,
            "consecutive_failures": self.context.consecutive_failures,
            "recent_actions": self.context.get_recent_actions(5),
            "tools_loaded": len(self.tool_manager.list_tools()),
            "skills_loaded": len(self.skill_manager.list_skills()),
        }
