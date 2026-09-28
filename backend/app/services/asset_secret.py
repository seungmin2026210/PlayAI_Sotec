"""계정 비밀번호 암호화 — Fernet(AES-128-CBC + HMAC). specs/ASSET-1 D15, D43.

키는 환경변수 `ASSET_SECRET_KEY`(config.settings.asset_secret_key). 없으면 501
SECRET_KEY_MISSING — 호출자는 비밀번호가 **있을 때만** 이 모듈을 부르므로, 비밀번호 없는
요청은 키 없이도 정상 동작한다. 키 생성:
    python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
키를 잃으면 저장된 비밀번호는 복구 불가.
"""
from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken

from ..config import settings
from ..errors import SECRET_KEY_MISSING, AppError


def _fernet() -> Fernet:
    key = settings.asset_secret_key
    if not key:
        raise AppError(SECRET_KEY_MISSING, 501, "비밀번호 암호화 키(ASSET_SECRET_KEY)가 설정되지 않았습니다.")
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError):
        raise AppError(SECRET_KEY_MISSING, 501, "비밀번호 암호화 키(ASSET_SECRET_KEY) 형식이 올바르지 않습니다.")


def encrypt(plain: str) -> str:
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    f = _fernet()
    try:
        return f.decrypt(token.encode()).decode()
    except InvalidToken:
        raise AppError(
            SECRET_KEY_MISSING, 501, "암호화 키가 저장 당시와 달라 비밀번호를 복호화할 수 없습니다."
        )
