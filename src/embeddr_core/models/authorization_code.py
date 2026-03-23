from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON


class AuthorizationCode(SQLModel, table=True):
    __tablename__ = "authorization_code"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    code_hash: str = Field(index=True, unique=True)
    code_prefix: str = Field(index=True)
    service_client_id: UUID = Field(foreign_key="service_client.id", index=True)
    user_id: UUID = Field(foreign_key="client.id", index=True)
    operator_id: UUID = Field(foreign_key="operator.id", index=True)
    scopes: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    redirect_uri: str
    code_challenge: Optional[str] = None
    code_challenge_method: str = Field(default="S256")
    state: Optional[str] = None
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    expires_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    used_at: Optional[datetime] = None
