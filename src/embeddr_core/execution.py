from typing import Any, Callable, Dict, Optional, Protocol
from datetime import datetime
from uuid import UUID


class JobContext(Protocol):
    """
    The interface provided to job handlers during execution.
    Isolates the handler from the DB/Execution Spine internals.
    """
    execution_id: UUID
    inputs: Dict[str, Any]

    def set_progress(self, percent: int, message: Optional[str] = None) -> None:
        """Update the progress of the current job."""
        ...

    def log(self, message: str, level: str = "info") -> None:
        """Log a message associated with this execution."""
        ...

    def is_cancelled(self) -> bool:
        """Check if the job has been requested to cancel."""
        ...


class JobHandler(Protocol):
    """
    Signature for a function that executes a job.
    """

    def __call__(self, ctx: JobContext) -> Dict[str, Any]: ...
