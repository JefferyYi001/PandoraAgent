"""
SQLAlchemy declarative models for chat history, templates, and config
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(DeclarativeBase):
    pass


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(Integer, primary_key=True)
    contact_name = Column(String, nullable=False)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)
    status = Column(String, default="active")  # active, completed, abandoned
    total_messages = Column(Integer, default=0)

    messages = relationship("Message", back_populates="session")

    def to_dict(self):
        return {
            "id": self.id,
            "contact_name": self.contact_name,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "status": self.status,
            "total_messages": self.total_messages,
        }


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # incoming / outgoing
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    template_id = Column(Integer, nullable=True)
    tool_trace = Column(JSON, nullable=True)

    session = relationship("ChatSession", back_populates="messages")

    def to_dict(self):
        return {
            "id": self.id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "created_at": self.created_at.isoformat(),
            "template_id": self.template_id,
        }


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    category = Column(String, default="general")
    content = Column(Text, nullable=False)
    variables = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "content": self.content,
            "variables": self.variables,
            "is_active": self.is_active,
        }
