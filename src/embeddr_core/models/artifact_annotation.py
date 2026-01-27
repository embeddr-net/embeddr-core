from datetime import datetime, timezone
from uuid import UUID, uuid4
from typing import Optional
from sqlmodel import Field, SQLModel


class ArtifactAnnotation(SQLModel, table=True):
    """
    Stores text-based derived metadata for artifacts.
    Examples: Captions, Transcriptions, Summaries, Translations.
    Separated from Artifact to allow multiple annotations and better indexing.
    """
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    artifact_id: UUID = Field(foreign_key="artifact.id", index=True)

    # The content of the annotation
    text: str

    # Type of annotation: "caption", "transcription", "summary", "ocr", etc.
    annotation_type: str = Field(index=True)

    # Which plugin/model generated this? e.g. "plugin:caption:blip", "user"
    plugin_name: Optional[str] = Field(default=None, index=True)

    # Confidence score (0.0 - 1.0) if applicable
    confidence: Optional[float] = None

    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
