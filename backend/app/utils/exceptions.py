from __future__ import annotations


class AppException(Exception):
    """Base exception for all domain errors. Handled by a single handler in main.py."""

    status_code: int = 500
    detail: str = "An unexpected error occurred."

    def __init__(self, detail: str | None = None, status_code: int | None = None) -> None:
        self.detail = detail or self.__class__.detail
        self.status_code = status_code or self.__class__.status_code
        super().__init__(self.detail)


class NotFoundError(AppException):
    status_code = 404
    detail = "Resource not found."


class ConflictError(AppException):
    status_code = 409
    detail = "Resource already exists."


class UnauthorizedError(AppException):
    status_code = 401
    detail = "Authentication required."


class ForbiddenError(AppException):
    status_code = 403
    detail = "You do not have permission to perform this action."


class BadRequestError(AppException):
    status_code = 400
    detail = "Invalid request."
