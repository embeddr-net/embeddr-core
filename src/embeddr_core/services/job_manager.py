import threading
import uuid
from collections.abc import Callable
from enum import Enum
from typing import Any


class JobStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class JobManager:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(JobManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.current_job_id: str | None = None
        self.status: JobStatus = JobStatus.IDLE
        self.progress: int = 0
        self.total: int = 0
        self.message: str = ""
        self.error: str | None = None
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self.job_type: str = ""

    def start_job(self, job_type: str, target_func: Callable, *args, **kwargs) -> str:
        with self._lock:
            if self.status == JobStatus.RUNNING:
                raise ValueError("A job is already running")

            self.current_job_id = str(uuid.uuid4())
            self.status = JobStatus.RUNNING
            self.progress = 0
            self.total = 0
            self.message = f"Starting {job_type}..."
            self.error = None
            self.job_type = job_type
            self._stop_event.clear()

            # Wrap the target function to handle status updates
            def wrapper():
                try:
                    # Inject stop_event and progress_callback if the function accepts them
                    # We assume the target function signature is compatible or we pass them as kwargs
                    kwargs["stop_event"] = self._stop_event
                    kwargs["progress_callback"] = self._update_progress

                    result = target_func(*args, **kwargs)

                    with self._lock:
                        if self.status != JobStatus.STOPPED:
                            self.status = JobStatus.COMPLETED
                            self.message = "Job completed successfully"
                except Exception as e:
                    with self._lock:
                        if self.status != JobStatus.STOPPED:
                            self.status = JobStatus.FAILED
                            self.error = str(e)
                            self.message = f"Job failed: {str(e)}"
                finally:
                    # Cleanup or final status check?
                    pass

            self._thread = threading.Thread(target=wrapper)
            self._thread.start()
            return self.current_job_id

    def stop_job(self):
        with self._lock:
            if self.status == JobStatus.RUNNING:
                self._stop_event.set()
                self.status = JobStatus.STOPPED
                self.message = "Job stopped by user"

    def _update_progress(self, current: int, total: int, message: str = None):
        # This is called from the worker thread, so we don't need the lock for simple assignments
        # but for consistency/safety with reads:
        self.progress = current
        self.total = total
        if message:
            self.message = message

    def get_status(self) -> dict[str, Any]:
        return {
            "job_id": self.current_job_id,
            "status": self.status,
            "progress": self.progress,
            "total": self.total,
            "message": self.message,
            "error": self.error,
            "job_type": self.job_type,
        }


job_manager = JobManager()
