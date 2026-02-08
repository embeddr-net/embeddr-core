from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.orm import relationship

if TYPE_CHECKING:
    from .api_key import ApiKey
    from .role import Role


class UserAccount(SQLModel, table=True):
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
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc))

    roles: List["UserRole"] = Relationship(
        sa_relationship=relationship(
            "UserRole",
            back_populates="user",
            cascade="all, delete",
        )
    )
    api_keys: List["ApiKey"] = Relationship(
        sa_relationship=relationship(
            "ApiKey",
            back_populates="user",
            cascade="all, delete",
        )
    )


class UserRole(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: UUID = Field(foreign_key="useraccount.id", index=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)

    user: UserAccount = Relationship(
        sa_relationship=relationship("UserAccount", back_populates="roles")
    )
    role: "Role" = Relationship(sa_relationship=relationship("Role"))
