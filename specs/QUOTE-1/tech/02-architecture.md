# 02. 아키텍처

## 개요

```
[React SPA :5173] ──HTTP/JSON──> [FastAPI :8000] ──SQLAlchemy──> [PostgreSQL :5432]
       │                              │
   Bearer 토큰                   openpyxl / WeasyPrint (파일 스트림 응답)
```

- 단일 백엔드 서비스. 상태는 전부 DB. 파일 저장 없음(export는 즉석 생성 후 스트림).
- 인증: 로그인 시 `config.ACCOUNTS` 대조 → 서명된 토큰(payload: `username, role, group_code, exp`) 발급. 이후 요청은 `Authorization: Bearer <token>`.
- 권한: 라우터 의존성 `get_current_user` → `deps.require_super_admin` / `deps.scope_filter`.

## 요청 흐름 (예: 견적 등록)

1. `POST /api/quotes` + Bearer 토큰.
2. `get_current_user` 토큰 검증 → `require_super_admin` (그룹관리자면 403).
3. `schemas.QuoteCreate` 검증 (필수/음수 규칙).
4. `services.calculation` 으로 합계·절사·부가세 계산.
5. `services.numbering.allocate()` 트랜잭션 내 `FOR UPDATE` 채번 → 관리번호.
6. `Quote` + `QuoteItem[]` insert, 상태 `SUBMITTED`, `created_at` 설정.
7. `201` + `QuoteRead`.

## 계층 규칙

- **routers**: HTTP·권한·직렬화만. 비즈니스 로직 없음.
- **services**: 순수 함수 우선(계산), DB 트랜잭션 캡슐화(채번/상태).
- **models/schemas**: 저장 형태 / 전송 형태 분리.
- 미정 정책은 services 안의 명명된 함수 1곳에 격리 ([10-provisional-decisions.md](./10-provisional-decisions.md)).

## 프론트 구조

- `auth.tsx`: 토큰 `localStorage` 보관, `AuthProvider` + `useAuth`.
- `api/client.ts`: `fetch` 래퍼, 401 시 로그아웃, 에러 `detail.message` 추출.
- 라우팅: `/login`, `/quotes`, `/quotes/new`, `/quotes/:id`, `/quotes/:id/edit`.
- `RoleGate`: `role` 기준 액션 버튼 렌더 (서버가 최종 방어선).
