"""
Repository pattern for database access - ChatRecord, Template, Config
"""

from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from datetime import datetime

from db.models import ChatSession, Message, Template
from utils.logger import logger


class ChatSessionRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, contact_name: str) -> ChatSession:
        record = ChatSession(contact_name=contact_name)
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_id(self, session_id: int) -> ChatSession | None:
        return self.session.query(ChatSession).filter(ChatSession.id == session_id).first()

    def get_latest_session(self, contact_name: str) -> ChatSession | None:
        return (self.session.query(ChatSession)
                .filter(ChatSession.contact_name == contact_name)
                .order_by(desc(ChatSession.started_at))
                .first())

    def get_recent_sessions(self, contact_name: str, limit: int = 5) -> list[ChatSession]:
        return (self.session.query(ChatSession)
                .filter(ChatSession.contact_name == contact_name)
                .order_by(desc(ChatSession.started_at))
                .limit(limit)
                .all())

    def close_session(self, session_id: int) -> None:
        record = self.get_by_id(session_id)
        if record:
            record.ended_at = datetime.utcnow()
            record.status = "completed"
            self.session.commit()

    def list_sessions(self, limit: int = 20) -> list[ChatSession]:
        return (self.session.query(ChatSession)
                .order_by(desc(ChatSession.started_at))
                .limit(limit)
                .all())


class MessageRepository:
    def __init__(self, session: Session):
        self.session = session

    def add_message(self, session_id: int, role: str, content: str,
                    template_id: int | None = None, tool_trace: dict | None = None) -> Message:
        record = Message(
            session_id=session_id,
            role=role,
            content=content,
            template_id=template_id,
            tool_trace=tool_trace,
        )
        self.session.add(record)
        self.session.commit()
        # Update session message count
        session_record = self.session.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session_record:
            session_record.total_messages += 1
            self.session.commit()
        return record

    def get_session_messages(self, session_id: int, limit: int = 50) -> list[Message]:
        return (self.session.query(Message)
                .filter(Message.session_id == session_id)
                .order_by(desc(Message.created_at))
                .limit(limit)
                .all()[::-1])  # Reverse to chronological order

    def get_context_messages(self, session_id: int, max_count: int = 15) -> list[str]:
        """Get conversation context for LLM: last 3 full + 4-15 condensed"""
        messages = self.get_session_messages(session_id, limit=max_count)
        if not messages:
            return []

        # Last 3 full messages
        result = []
        for msg in messages[-3:]:
            prefix = "对方" if msg.role == "incoming" else "我"
            result.append(f"{prefix}: {msg.content}")

        # Earlier messages condensed
        if len(messages) > 3:
            for msg in messages[3:-3]:
                prefix = "对方" if msg.role == "incoming" else "我"
                preview = msg.content[:30] + "..." if len(msg.content) > 30 else msg.content
                result.append(f"{prefix}: {preview}")

        return result


class TemplateRepository:
    def __init__(self, session: Session):
        self.session = session

    def create(self, name: str, content: str, category: str = "general",
               variables: list | None = None) -> Template:
        record = Template(name=name, content=content, category=category,
                         variables=variables or [])
        self.session.add(record)
        self.session.commit()
        self.session.refresh(record)
        return record

    def get_by_id(self, template_id: int) -> Template | None:
        return self.session.query(Template).filter(Template.id == template_id).first()

    def list_templates(self, category: str | None = None, active_only: bool = True) -> list[Template]:
        query = self.session.query(Template)
        if active_only:
            query = query.filter(Template.is_active == True)
        if category:
            query = query.filter(Template.category == category)
        return query.order_by(Template.name).all()

    def update(self, template_id: int, updates: dict) -> Template | None:
        record = self.get_by_id(template_id)
        if record:
            for key, value in updates.items():
                if hasattr(record, key):
                    setattr(record, key, value)
            self.session.commit()
            self.session.refresh(record)
        return record

    def delete(self, template_id: int) -> bool:
        record = self.get_by_id(template_id)
        if record:
            self.session.delete(record)
            self.session.commit()
            return True
        return False
