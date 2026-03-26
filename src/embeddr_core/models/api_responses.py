"""
Standard API response models for Embeddr.

All endpoints should use these base models (or domain-specific subclasses)
to ensure a consistent response contract across the API surface.

Usage::

    from embeddr_core.models.api_responses import (
        OkResponse,
        ErrorResponse,
        PaginatedResponse,
        ErrorCode,
    )

    # Simple success
    return OkResponse(message="Artifact deleted")

    # Paginated list
    return PaginatedResponse[Artifact](items=rows, total=count, limit=50, offset=0)

    # Error (typically raised via HTTPException, but the error handler
    # middleware will wrap it into this shape automatically)
    ErrorResponse(error_code=ErrorCode.NOT_FOUND, message="Artifact not found")
"""

from enum import Enum
from typing import Any, Dict, Generic, List, Optional, TypeVar

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Error codes
# ---------------------------------------------------------------------------

class ErrorCode(str, Enum):
    """
    Machine-readable error codes returned in ErrorResponse.error_code.

    Clients should switch on these rather than parsing the human-readable
    message string.
    """

    # Generic
    NOT_FOUND = "not_found"
    INVALID_INPUT = "invalid_input"
    CONFLICT = "conflict"
    INTERNAL_ERROR = "internal_error"
    NOT_IMPLEMENTED = "not_implemented"

    # Auth
    UNAUTHENTICATED = "unauthenticated"
    PERMISSION_DENIED = "permission_denied"
    SESSION_EXPIRED = "session_expired"
    INVALID_CREDENTIALS = "invalid_credentials"

    # Domain
    ARTIFACT_NOT_FOUND = "artifact_not_found"
    EXECUTION_NOT_FOUND = "execution_not_found"
    PLUGIN_NOT_FOUND = "plugin_not_found"
    RELATION_NOT_FOUND = "relation_not_found"
    TYPE_NOT_FOUND = "type_not_found"
    DUPLICATE_RELATION = "duplicate_relation"

    # Execution
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"
    RESOURCE_BUSY = "resource_busy"


# ---------------------------------------------------------------------------
# Base response models
# ---------------------------------------------------------------------------

class OkResponse(BaseModel):
    """Simple success response for mutations that don't return a domain object."""

    ok: bool = True
    message: Optional[str] = None


class ErrorResponse(BaseModel):
    """
    Standard error envelope. The error handler middleware wraps all
    HTTPException responses into this shape so clients always get a
    consistent JSON structure.
    """

    ok: bool = False
    error_code: str = Field(
        description="Machine-readable error code (see ErrorCode enum)"
    )
    message: str = Field(
        description="Human-readable error description"
    )
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional structured details (e.g. field validation errors)",
    )


T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Standard paginated list response.

    All list endpoints that support limit/offset should return this shape
    so clients can rely on a single pagination contract.
    """

    items: List[T]
    total: int = Field(description="Total number of items matching the query")
    limit: int = Field(description="Maximum items returned in this page")
    offset: int = Field(description="Number of items skipped")
