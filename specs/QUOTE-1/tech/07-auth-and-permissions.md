# 07. 인증 시뮬레이션 / 권한

## 인증 (시뮬레이션, 범위 외 로직 없음)

- `config.ACCOUNTS`: `{username: {password, role, group_code, display_name}}` — **유일한 계정 정의처**.
- `POST /auth/login`: 평문 비교(데모). 성공 시 토큰 발급.
- 토큰: `itsdangerous.URLSafeTimedSerializer(TOKEN_SECRET)` 로 `{username}` 서명 + TTL. 검증 시 `ACCOUNTS`에서 현재 role/group 재조회 (토큰에 권한 박제 안 함 → 상수 바꾸면 즉시 반영).
- 실사용 전환 시: `ACCOUNTS`에 개별 계정 추가만 하면 됨. 코드 변경 불필요. (계정 공유 금지 원칙은 운영 규칙.)

## 권한 판정 (`deps.py` — open-1/open-3 격리 지점)

```
def get_current_user(...) -> CurrentUser        # 토큰 검증, 실패 시 NOT_AUTHENTICATED

def require_super_admin(user = Depends(get_current_user)):
    if user.role != "SUPER_ADMIN":
        raise AppError("FORBIDDEN_ROLE", 403, "조회 전용 권한입니다.")
    return user

def scope_group(user) -> str | None:
    # 그룹관리자: 본인 그룹 코드 반환(services/query.py 가 이 값으로 Firestore 등호 필터).
    # 전체관리자: None(무제한). Firestore 전환 전에는 SQL Select에 .where(...)를 얹는
    # apply_scope(query, user) 였음(12-firestore-migration.md 참고).
    if user.role == "GROUP_MANAGER":
        return user.group_code
    return None

def assert_can_view(quote, user):
    if user.role == "GROUP_MANAGER" and quote.group_code != user.group_code:
        raise AppError("NOT_FOUND", 404, "견적서를 찾을 수 없습니다.")
```

- 쓰기 계열 라우터: `Depends(require_super_admin)`.
- 조회 계열: `get_current_user` + `apply_scope` / `assert_can_view`.
- **프론트의 버튼 숨김은 UX일 뿐, 서버가 최종 방어선.**

## 역할 → 화면 (프론트 `RoleGate`)

| 요소 | SUPER_ADMIN | GROUP_MANAGER |
|---|---|---|
| 목록/상세 조회 | 전체 그룹 | 본인 그룹만 |
| 등록/수정/삭제/승인/반려/취소/잠금/발송 버튼 | 노출 | 숨김 |
| 엑셀/PDF export | 노출 | 노출 |
