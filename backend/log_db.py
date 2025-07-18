from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Any
from uuid import uuid4

from sqlmodel import SQLModel, Field, create_engine, Session
from sqlalchemy import Column, JSON

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./omni_logs.db")

engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)


class SessionEntry(SQLModel, table=True):
    id: str = Field(default_factory=lambda: uuid4().hex, primary_key=True)
    started_at: datetime = Field(default_factory=datetime.utcnow)
    ended_at: Optional[datetime] = None
    user_agent: str = ""
    locale: Optional[str] = None


class Event(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(foreign_key="sessionentry.id", index=True)
    ts: datetime = Field(default_factory=datetime.utcnow, index=True)
    type: str
    payload: dict = Field(default_factory=dict, sa_column=Column(JSON))


def create_db_and_tables() -> None:
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as s:
        yield s


def log_event(db: Session, session_id: str, ev_type: str, **payload: Any) -> None:
    ev = Event(session_id=session_id, type=ev_type, payload=payload)
    db.add(ev)
    db.commit()
