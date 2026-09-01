"""로그인 시뮬레이션 (기획서 3.3, 실제 인증 로직은 범위 외).

토큰에는 username 만 담고, role/group 은 매 요청 시 config.ACCOUNTS 에서 재조회한다.
→ 상수만 바꾸면 권한이 즉시 반영되고, 토큰에 권한이 박제되지 않는다.
"""
from __future__ import annotations

from dataclasses import dataclass

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from .config import ACCOUNTS, settings
from .errors import INVALID_CREDENTIALS, NOT_AUTHENTICATED, AppError

_serializer = URLSafeTimedSerializer(settings.token_secret, salt="quote-auth")
_MAX_AGE = settings.token_ttl_hours * 3600


@dataclass(frozen=True)
class CurrentUser:
    username: str
    role: str
    group_code: str | None
    display_name: str


def authenticate(username: str, password: str) -> CurrentUser:
    acct = ACCOUNTS.get(username)
    if acct is None or acct["password"] != password:
        raise AppError(INVALID_CREDENTIALS, 401, "아이디 또는 비밀번호가 올바르지 않습니다.")
    return _to_user(username, acct)


def issue_token(username: str) -> str:
    return _serializer.dumps({"u": username})


def resolve_token(token: str) -> CurrentUser:
    try:
        data = _serializer.loads(token, max_age=_MAX_AGE)
    except SignatureExpired:
        raise AppError(NOT_AUTHENTICATED, 401, "세션이 만료되었습니다. 다시 로그인하세요.")
    except BadSignature:
        raise AppError(NOT_AUTHENTICATED, 401, "유효하지 않은 토큰입니다.")

    username = data.get("u")
    acct = ACCOUNTS.get(username)
    if acct is None:
        raise AppError(NOT_AUTHENTICATED, 401, "존재하지 않는 계정입니다.")
    return _to_user(username, acct)


def _to_user(username: str, acct: dict) -> CurrentUser:
    return CurrentUser(
        username=username,
        role=acct["role"],
        group_code=acct.get("group_code"),
        display_name=acct.get("display_name", username),
    )
