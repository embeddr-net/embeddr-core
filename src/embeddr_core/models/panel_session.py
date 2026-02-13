"""Panel session model.

A PanelSession represents a UI panel (media frame, lightbox, comparison
view, etc.) that is owned by a client credential / user.  Sessions
persist across reconnections and can be queried by the LLM or other
tools so that actions like "put this image in my last active media
frame" work without the user having to provide explicit panel IDs.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, JSON, SQLModel


class PanelSession(SQLModel, table=True):
    __tablename__ = "panelsession"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    # Owning identity — at least one of client_id or credential_id should
    # be set so we can scope queries per-credential.
    client_id: Optional[UUID] = Field(
        default=None, foreign_key="client.id", index=True
    )
    credential_id: Optional[UUID] = Field(
        default=None, foreign_key="clientcredential.id", index=True
    )
    operator_id: Optional[UUID] = Field(
        default=None, foreign_key="operator.id", index=True
    )

    # Panel tracking
    panel_id: str = Field(index=True)
    # e.g. "media_frame", "lightbox", "compare"
    panel_type: str = Field(index=True)
    window_id: Optional[str] = Field(default=None, index=True)
    title: Optional[str] = None

    # Freeform metadata (layout prefs, zoom state, etc.)
    meta: Optional[Dict[str, Any]] = Field(default=None, sa_type=JSON)

    # Items currently shown in the panel (artifact IDs, URLs, etc.)
    items: Optional[List[Dict[str, Any]]] = Field(default=None, sa_type=JSON)

    # Timestamps
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_active_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    closed_at: Optional[datetime] = None

    @property
    def is_active(self) -> bool:
        return self.closed_at is None
