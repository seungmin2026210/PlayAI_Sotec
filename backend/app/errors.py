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

# 구매관리 · 자산관리 (PURCHASE-1)
PRODUCT_INACTIVE = "PRODUCT_INACTIVE"
ALREADY_RETIRED = "ALREADY_RETIRED"

# 자산관리 (ASSET-1)
ALREADY_IMPORTED = "ALREADY_IMPORTED"
ASSET_NOT_IDLE = "ASSET_NOT_IDLE"
ASSET_IN_USE = "ASSET_IN_USE"
ASSET_NOT_IN_USE = "ASSET_NOT_IN_USE"
ASSET_DISPOSED = "ASSET_DISPOSED"
ASSET_HAS_HISTORY = "ASSET_HAS_HISTORY"
ASSET_DELETED = "ASSET_DELETED"
ASSET_IMPORTED = "ASSET_IMPORTED"
MEMBER_INACTIVE = "MEMBER_INACTIVE"
MEMBER_EXISTS = "MEMBER_EXISTS"
SECRET_KEY_MISSING = "SECRET_KEY_MISSING"


def validation(message: str) -> AppError:
    """도메인 규칙 위반(날짜 규칙 등) — 400 VALIDATION_ERROR. 스키마 레벨 422 와 구분."""
    return AppError(VALIDATION_ERROR, 400, message)
