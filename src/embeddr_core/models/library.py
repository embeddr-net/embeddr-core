from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel


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
    library_path_id: int | None = Field(default=None, foreign_key="librarypath.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Metadata
    width: int | None = None
    height: int | None = None
    file_size: int | None = None
    mime_type: str | None = None
    prompt: str | None = None

    library: LibraryPath | None = Relationship(back_populates="images")
