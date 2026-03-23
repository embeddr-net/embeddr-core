from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .api_key import ClientCredential
    from .role import ScopePreset


class Client(SQLModel, table=True):
    __tablename__ = "client"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    username: str = Field(index=True, unique=True)
    display_name: Optional[str] = None
    avatar_url: Optional[str] = None
    password_hash: Optional[str] = None
    password_salt: Optional[str] = None
    operator_id: Optional[UUID] = Field(
        default=None, foreign_key="operator.id", index=True
    )
    is_active: bool = True
    is_admin: bool = False
    must_change_password: bool = Field(default=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    roles: List["ClientScopePreset"] = Relationship(
        sa_relationship=relationship(
            "ClientScopePreset",
            back_populates="user",
            cascade="all, delete",
        )
    )
    api_keys: List["ClientCredential"] = Relationship(
        sa_relationship=relationship(
            "ClientCredential",
            back_populates="user",
            cascade="all, delete",
        )
    )


class ClientScopePreset(SQLModel, table=True):
    __tablename__ = "client_scope_preset"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="client.id", index=True)
    role_id: UUID = Field(foreign_key="scopepreset.id", index=True)

    user: Client = Relationship(
        sa_relationship=relationship("Client", back_populates="roles")
    )
    role: "ScopePreset" = Relationship(
        sa_relationship=relationship("ScopePreset")
    )


# Backwards-compatible aliases
UserAccount = Client
UserRole = ClientScopePreset
