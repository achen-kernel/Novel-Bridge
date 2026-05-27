"""
Structured pipeline error hierarchy.

All pipeline-phase errors should use PipelineError (or a subclass) instead of
bare Exception. This ensures that errors surface with a machine-readable code,
a human-readable message, and optional structured detail that the frontend can
render without exposing raw Python tracebacks.
"""


class PipelineError(Exception):
    """Base error for all pipeline-phase failures."""

    def __init__(
        self,
        phase: str,
        book_id: int,
        code: str,
        message: str,
        detail: dict | None = None,
    ):
        self.phase = phase
        self.book_id = book_id
        self.code = code
        self.detail = detail or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "book_id": self.book_id,
            "code": self.code,
            "message": str(self.args[0]) if self.args else "",
            "detail": self.detail,
        }


# ── Common error codes ──

FK_CONSTRAINT = "FK_CONSTRAINT"
DB_CONNECTION = "DB_CONNECTION"
MODEL_FAILURE = "MODEL_FAILURE"
BOOK_NOT_FOUND = "BOOK_NOT_FOUND"
PHASE_FAILED = "PHASE_FAILED"
INVALID_STATE = "INVALID_STATE"
TIMEOUT = "TIMEOUT"


# ── Convenience constructors ──

def db_error(phase: str, book_id: int, message: str, detail: dict | None = None) -> PipelineError:
    return PipelineError(phase, book_id, DB_CONNECTION, message, detail)


def model_error(phase: str, book_id: int, message: str, detail: dict | None = None) -> PipelineError:
    return PipelineError(phase, book_id, MODEL_FAILURE, message, detail)


def not_found_error(phase: str, book_id: int, message: str, detail: dict | None = None) -> PipelineError:
    return PipelineError(phase, book_id, BOOK_NOT_FOUND, message, detail)


def phase_failed_error(phase: str, book_id: int, message: str, detail: dict | None = None) -> PipelineError:
    return PipelineError(phase, book_id, PHASE_FAILED, message, detail)
