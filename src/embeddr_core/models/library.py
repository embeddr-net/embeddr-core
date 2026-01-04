from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel
from embeddr_core.models.lineage import ImageLineage


class LibraryPath(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    path: str = Field(index=True, unique=True)
    name: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    images: list["LocalImage"] = Relationship(back_populates="library")


class LocalImage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    path: str = Field(index=True, unique=True)
    filename: str
    library_path_id: int | None = Field(
        default=None, foreign_key="librarypath.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    mime_type: str | None = None
    media_type: str = Field(default="image", index=True)
    duration: float | None = None
    fps: float | None = None
    frame_count: int | None = None
    prompt: str | None = None
    tags: str | None = None
    phash: str | None = Field(default=None, index=True)
    is_archived: bool = Field(default=False, index=True)

    library: LibraryPath | None = Relationship(back_populates="images")

    parents: list["LocalImage"] = Relationship(
        back_populates="children",
        link_model=ImageLineage,
        sa_relationship_kwargs={
            "primaryjoin": "LocalImage.id==ImageLineage.child_id",
            "secondaryjoin": "LocalImage.id==ImageLineage.parent_id",
        },
    )
    children: list["LocalImage"] = Relationship(
        back_populates="parents",
        link_model=ImageLineage,
        sa_relationship_kwargs={
            "primaryjoin": "LocalImage.id==ImageLineage.parent_id",
            "secondaryjoin": "LocalImage.id==ImageLineage.child_id",
        },
    )
