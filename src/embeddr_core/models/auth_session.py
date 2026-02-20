from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel


class AuthSession(SQLModel, table=True):
    __tablename__ = "authsession"

    id: UUID = Field(default_factory=uuid4, primary_key=True)

    user_id: UUID = Field(foreign_key="client.id", index=True)
    operator_id: Optional[UUID] = Field(
        default=None, foreign_key="operator.id", index=True
    )
    api_key_id: Optional[UUID] = Field(
        default=None, foreign_key="clientcredential.id", index=True
    )

    token_hash: str = Field(index=True, unique=True)
    token_prefix: str = Field(index=True)
    session_name: Optional[str] = None
    auth_method: str = Field(default="session", index=True)
    user_agent: Optional[str] = None
    ip_address: Optional[str] = None
    rotated_from_id: Optional[UUID] = Field(
        default=None, foreign_key="authsession.id", index=True
    )

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_used_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None

    @property
    def is_active(self) -> bool:
        if self.revoked_at is not None:
            return False
        if self.expires_at and self.expires_at < datetime.now(timezone.utc):
            return False
        return True
