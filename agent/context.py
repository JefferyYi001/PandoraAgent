"""
AgentContext - Current state, active contact, conversation history, action tracking
"""

import time
from enum import Enum
from dataclasses import dataclass, field


class AgentState(Enum):
    IDLE = "idle"
    SENTRY_OK = "sentry_ok"
    LOCKING = "locking"
    EXTRACTING = "extracting"
    THINKING = "thinking"
    REPLYING = "replying"
    MONITOR = "monitor"
    IGNORE = "ignore"
    CLEANUP = "cleanup"


@dataclass
class AgentContext:
    """Holds current agent state for FSM transitions and LLM context"""
    state: AgentState = AgentState.IDLE
    active_contact: str | None = None
    last_message: str = ""
    last_message_time: float = 0.0
    monitor_start_time: float = 0.0
    action_history: list[dict] = field(default_factory=list)
    current_session_id: int | None = None
    consecutive_failures: int = 0
    pending_reply: str | None = None
    alert_position: list | None = None

    def transition(self, new_state: AgentState) -> None:
        old = self.state
        self.state = new_state
        from utils.logger import logger
        logger.info(f"State transition: {old.value} → {new_state.value}")

    def record_action(self, action: str, result: str, details: dict | None = None) -> None:
        self.action_history.append({
            "action": action,
            "result": result,
            "details": details or {},
            "timestamp": time.time(),
        })
        if len(self.action_history) > 20:
            self.action_history = self.action_history[-20:]

    def reset_session(self) -> None:
        self.active_contact = None
        self.last_message = ""
        self.last_message_time = 0.0
        self.monitor_start_time = 0.0
        self.current_session_id = None
        self.pending_reply = None
        self.alert_position = None
        self.consecutive_failures = 0
        self.action_history.clear()

    def get_recent_actions(self, n: int = 5) -> list[dict]:
        return self.action_history[-n:]