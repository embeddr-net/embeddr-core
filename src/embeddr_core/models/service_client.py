from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, SQLModel, Column
from sqlalchemy import JSON


class ServiceClient(SQLModel, table=True):
    __tablename__ = "service_client"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    client_id: str = Field(index=True, unique=True)
    client_secret_hash: str
    client_secret_prefix: str = Field(index=True)
    name: str = Field(index=True)
    description: Optional[str] = None
    operator_id: UUID = Field(foreign_key="operator.id", index=True)
    created_by_user_id: UUID = Field(foreign_key="client.id", index=True)
    redirect_uris: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    allowed_scopes: List[str] = Field(default_factory=list, sa_column=Column(JSON))
    grant_types: List[str] = Field(
        default_factory=lambda: ["client_credentials"],
        sa_column=Column(JSON),
    )
    is_public: bool = False  # Public clients don't need client_secret (PKCE-only)
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    last_used_at: Optional[datetime] = None
