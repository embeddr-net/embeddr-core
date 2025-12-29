from datetime import datetime

from sqlmodel import Field, Relationship, SQLModel

from .library import LocalImage


class Collection(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    items: list["CollectionItem"] = Relationship(
        back_populates="collection", sa_relationship_kwargs={"cascade": "all, delete"}
    )


class CollectionItem(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    collection_id: int = Field(foreign_key="collection.id")
    image_id: int = Field(foreign_key="localimage.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    collection: Collection = Relationship(back_populates="items")
    image: LocalImage = Relationship()
