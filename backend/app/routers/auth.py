from __future__ import annotations

from fastapi import APIRouter, Depends

from ..auth import CurrentUser, authenticate, issue_token
from ..deps import get_current_user
from ..schemas import LoginRequest, LoginResponse, UserOut

router = APIRouter(prefix="/api/auth", tags=["auth"])


def _user_out(u: CurrentUser) -> UserOut:
    return UserOut(
        username=u.username,
        role=u.role,
        group_code=u.group_code,
        display_name=u.display_name,
    )


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest) -> LoginResponse:
    user = authenticate(body.username, body.password)
    return LoginResponse(token=issue_token(user.username), user=_user_out(user))


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
