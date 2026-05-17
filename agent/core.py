"""
WechatAgent - FSM state machine + LLM hybrid decision making
Deterministic ops (sentry/extract/send/window) via state machine
Decision ops (THINKING) via direct ReplyTool call (approach A)
"""

import time
import asyncio

from agent.context import AgentContext, AgentState
from agent.tools.manager import ToolManager
from agent.skills.manager import SkillManager
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
        self.context.transition(AgentState.IDLE)
        logger.info("Agent started")

        polling = self.defaults.get("polling", {})
        idle_min = polling.get("interval_min", 3)
        idle_max = polling.get("interval_max", 8)
        active_delay = 0.5  # Short delay between active states
        monitor_delay = polling.get("monitor_interval", 5)  # Longer delay for monitor polling

        while self._running:
            try:
                new_state = await self._process_state()
                if new_state:
                    self.context.transition(new_state)
                    if self.context.state == AgentState.IDLE:
                        await asyncio.sleep(asyncio.get_event_loop().time() % (idle_max - idle_min) + idle_min)
                    elif self.context.state == AgentState.MONITOR:
                        await asyncio.sleep(monitor_delay)
                    else:
                        await asyncio.sleep(active_delay)
                else:
                    if self.context.state == AgentState.IDLE:
                        await asyncio.sleep(asyncio.get_event_loop().time() % (idle_max - idle_min) + idle_min)
                    elif self.context.state == AgentState.MONITOR:
                        await asyncio.sleep(monitor_delay)
                    else:
                        await asyncio.sleep(active_delay)
            except Exception as e:
                logger.error(f"Agent loop error: {e}")
                self.context.consecutive_failures += 1
                if self.context.consecutive_failures >= 5:
                    logger.error("Too many consecutive failures, stopping")
                    await self.stop()
                self.context.transition(AgentState.IDLE)

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
            self.context.alert_position = result.data.get("alert_position")
            return AgentState.SENTRY_OK
        return None

    async def _state_sentry_ok(self) -> AgentState | None:
        """Click taskbar icon to bring WeChat to foreground"""
        alert_position = self.context.alert_position
        if alert_position:
            from automation.humanize import human_click, human_sleep
            human_click(alert_position[0], alert_position[1])
            human_sleep(0.5, 0.8)
            return AgentState.LOCKING
        logger.warning("No alert_position available, falling back to IDLE")
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
            human_sleep(0.3, 0.5)
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
                self.context.record_action("extract", f"Extracted {len(messages)} messages")
                return AgentState.THINKING
            else:
                logger.info("No new messages to process")
                return AgentState.CLEANUP
        logger.warning(f"Extraction failed: {result.error}")
        return AgentState.IDLE

    async def _state_thinking(self) -> AgentState | None:
        """Generate reply via LLM (approach A: direct ReplyTool call)"""
        from agent.tools.reply_tool import ReplyTool
        reply_tool = ReplyTool()
        result = reply_tool.execute({
            "message": self.context.last_message,
            "context": [a["result"] for a in self.context.get_recent_actions(3)],
        })
        if result.success and result.data.get("reply"):
            self.context.pending_reply = result.data["reply"]
            self.context.consecutive_failures = 0
            self.context.record_action("thinking", f"Generated reply: {self.context.pending_reply[:50]}...")
            return AgentState.REPLYING
        logger.warning(f"Reply generation failed: {result.error}")
        return AgentState.IGNORE

    async def _state_replying(self) -> AgentState | None:
        """Send pending reply via WeChat input"""
        reply = self.context.pending_reply
        if not reply:
            logger.warning("No reply to send")
            return AgentState.CLEANUP

        from agent.tools.send_tool import SendTool
        config = self.defaults.get("wechat", {}).get("input_box_region")
        if not config:
            logger.warning("No input_box_region configured")
            return AgentState.CLEANUP

        center = (config[0] + config[2] // 2, config[1] + config[3] // 2)
        send_tool = SendTool()
        result = send_tool.execute({
            "input_box_center": list(center),
            "text": reply,
        })
        if result.success:
            self.context.pending_reply = None
            self.context.record_action("reply", f"Sent reply: {reply[:50]}...")
            return AgentState.MONITOR
        logger.warning(f"Send failed: {result.error}")
        return AgentState.MONITOR

    async def _state_monitor(self) -> AgentState | None:
        """Stay on current chat, wait for new taskbar alerts or timeout"""
        timeout = self.defaults.get("agent", {}).get("monitor_timeout_seconds", 300)
        elapsed = time.time() - self.context.last_message_time

        if elapsed > timeout:
            logger.info(f"Monitor timeout ({timeout}s), returning to cleanup")
            return AgentState.CLEANUP

        # Lightweight check: look for new taskbar alert instead of full extraction
        from agent.tools.sentry_tool import SentryTool
        config = self.defaults.get("wechat", {}).get("taskbar_region")
        if config:
            tool = SentryTool()
            result = tool.execute({"taskbar_region": config})
            if result.success and result.data.get("state") == "alert":
                logger.info("New alert detected during monitor, re-extracting")
                self.context.alert_position = result.data.get("alert_position")
                from automation.humanize import human_click, human_sleep
                human_click(self.context.alert_position[0], self.context.alert_position[1])
                human_sleep(0.3, 0.5)
                from agent.tools.message_extract_tool import MessageExtractTool
                extract_config = self.defaults.get("wechat", {}).get("chat_content_region")
                if extract_config:
                    extract_tool = MessageExtractTool()
                    result = extract_tool.execute({"chat_content_region": extract_config})
                    if result.success and result.data.get("messages"):
                        self.context.last_message = result.data["messages"][-1]
                        self.context.last_message_time = time.time()
                        return AgentState.THINKING

        return None

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