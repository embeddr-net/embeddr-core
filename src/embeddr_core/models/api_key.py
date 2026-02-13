from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, JSON, Relationship, SQLModel
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .user_account import Client


class ClientCredential(SQLModel, table=True):
    __tablename__ = "clientcredential"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="client.id", index=True)
    operator_id: Optional[UUID] = Field(
        default=None, foreign_key="operator.id", index=True
    )
    name: str = Field(index=True)
    key_hash: str = Field(index=True, unique=True)
    key_prefix: str = Field(index=True)
    scopes: List[str] = Field(default=[], sa_type=JSON)
    is_active: bool = True
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    user: "Client" = Relationship(
        sa_relationship=relationship("Client", back_populates="api_keys")
    )
    permissions: List["ClientCredentialPermission"] = Relationship(
        sa_relationship=relationship(
            "ClientCredentialPermission",
            back_populates="api_key",
            cascade="all, delete",
        )
    )


class ClientCredentialPermission(SQLModel, table=True):
    __tablename__ = "clientcredentialpermission"

    id: Optional[int] = Field(default=None, primary_key=True)
    api_key_id: UUID = Field(foreign_key="clientcredential.id", index=True)
    permission: str = Field(index=True)

    api_key: ClientCredential = Relationship(
        sa_relationship=relationship(
            "ClientCredential", back_populates="permissions"
        )
    )


# Backwards-compatible aliases
ApiKey = ClientCredential
ApiKeyPermission = ClientCredentialPermission
