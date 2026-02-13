from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID, uuid4

from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy.orm import relationship


class ScopePreset(SQLModel, table=True):
    __tablename__ = "scopepreset"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: Optional[str] = None
    is_system: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    permissions: List["ScopePresetPermission"] = Relationship(
        sa_relationship=relationship(
            "ScopePresetPermission",
            back_populates="role",
            cascade="all, delete",
        )
    )


class ScopePresetPermission(SQLModel, table=True):
    __tablename__ = "scopepresetpermission"

    id: Optional[int] = Field(default=None, primary_key=True)
    role_id: UUID = Field(foreign_key="scopepreset.id", index=True)
    permission: str = Field(index=True)

    role: ScopePreset = Relationship(
        sa_relationship=relationship(
            "ScopePreset", back_populates="permissions"
        )
    )


# Backwards-compatible aliases
Role = ScopePreset
RolePermission = ScopePresetPermission
