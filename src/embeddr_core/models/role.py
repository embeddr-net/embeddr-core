from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.orm import relationship


class Role(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    is_system: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    permissions: List["RolePermission"] = Relationship(
        sa_relationship=relationship(
            "RolePermission",
            back_populates="role",
            cascade="all, delete",
        )
    )


class RolePermission(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: UUID = Field(foreign_key="role.id", index=True)
    permission: str = Field(index=True)

    role: Role = Relationship(
        sa_relationship=relationship("Role", back_populates="permissions")
    )
