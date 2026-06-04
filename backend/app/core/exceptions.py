from fastapi import HTTPException


class SoulraException(Exception):
    """Base application exception."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class IngestionError(SoulraException):
    def __init__(self, message: str):
        super().__init__(message, code="INGESTION_FAILED")


class RetrievalError(SoulraException):
    def __init__(self, message: str):
        super().__init__(message, code="RETRIEVAL_FAILED")


class NotFoundError(SoulraException):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} '{id}' not found", code="NOT_FOUND")
