"""애플리케이션 에러 — 기획서 9장 / TECH 04 에러 코드 표와 1:1."""
from __future__ import annotations


class AppError(Exception):
    """도메인 규칙 위반. main.py 예외 핸들러가 {detail:{code,message}} 로 직렬화."""

    def __init__(self, code: str, status_code: int, message: str):
        super().__init__(message)
        self.code = code
        self.status_code = status_code
        self.message = message


# 코드 상수 (오타 방지)
INVALID_CREDENTIALS = "INVALID_CREDENTIALS"
NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
FORBIDDEN_ROLE = "FORBIDDEN_ROLE"
NOT_FOUND = "NOT_FOUND"
VALIDATION_ERROR = "VALIDATION_ERROR"
INVALID_TRANSITION = "INVALID_TRANSITION"
PURCHASE_LOCKED = "PURCHASE_LOCKED"
SEQ_EXHAUSTED = "SEQ_EXHAUSTED"
PDF_UNAVAILABLE = "PDF_UNAVAILABLE"
EXPORT_NOT_APPROVED = "EXPORT_NOT_APPROVED"
