# 04. API 명세

Base: `/api`. 인증: `Authorization: Bearer <token>` (로그인 제외).

## 인증

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| POST | `/auth/login` | 공개 | body `{username, password}` → `{token, user:{username,role,group_code,display_name}}`. 실패 401 |
| GET | `/auth/me` | 인증 | 현재 사용자 |

## 메타

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| GET | `/meta` | 인증 | `{groups:[{code,name}], company:{biz_no,ceo_name,...}, vat_rate, statuses:[...]}` |

## 견적서

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| GET | `/quotes` | 인증 | 목록. 쿼리: `mgmt_no, title, group_code, status, issue_date_from, issue_date_to, issuer_name, page, size`. 그룹관리자는 `group_code` 강제=본인 그룹 |
| POST | `/quotes` | 전체관리자 | 등록. 채번 + 계산 + 상태 SUBMITTED |
| GET | `/quotes/{id}` | 인증 | 상세. 그룹관리자가 타 그룹이면 404 |
| PUT | `/quotes/{id}` | 전체관리자 | 수정 (전체 필드). 잠금/승인됨/반려됨/취소됨이면 409. 상태 유지 |
| DELETE | `/quotes/{id}` | 전체관리자 | soft delete + 결번. 잠금/승인됨/반려됨/취소됨이면 409 |
| POST | `/quotes/{id}/approve` | 전체관리자 | SUBMITTED→APPROVED. 그 외 상태 409. 승인 즉시 읽기전용(수정/취소/삭제 불가) |
| POST | `/quotes/{id}/reject` | 전체관리자 | body `{reason}` 필수. SUBMITTED→REJECTED. reason 없으면 422 |
| POST | `/quotes/{id}/cancel` | 전체관리자 | SUBMITTED→CANCELLED. 잠금/그 외 상태(APPROVED 포함)면 409 |
| POST | `/quotes/{id}/purchase-lock` | 전체관리자 | 자리표시. `purchase_locked=true`, `locked_at` 설정 (idempotent) |
| POST | `/quotes/{id}/send` | 전체관리자 | 자리표시. 항상 `200 {message:"이메일 발송 기능은 준비 중입니다."}` |

## Export

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| GET | `/quotes/{id}/export.xlsx` | 인증(조회권 있는 자) | 개별 엑셀. `status != APPROVED` 면 `409 EXPORT_NOT_APPROVED` |
| GET | `/quotes/{id}/export.pdf` | 인증(조회권 있는 자) | 개별 PDF. `status != APPROVED` 면 `409 EXPORT_NOT_APPROVED` |
| GET | `/quotes/export.xlsx` | 인증 | 목록 엑셀 (동일 필터 파라미터 적용, 그룹관리자 스코프 강제). 상태 무관하게 전부 포함(목록 형식이라 개별 export 승인 제약과 무관) |

## 에러 코드

| code | HTTP | 의미 |
|---|---|---|
| `INVALID_CREDENTIALS` | 401 | 로그인 실패 |
| `NOT_AUTHENTICATED` | 401 | 토큰 없음/만료 |
| `FORBIDDEN_ROLE` | 403 | 그룹관리자가 쓰기 시도 |
| `NOT_FOUND` | 404 | 없음 / 스코프 밖 / 삭제됨 |
| `VALIDATION_ERROR` | 422 | 필수 누락, 음수/0, 반려사유 없음 |
| `INVALID_TRANSITION` | 409 | 허용 안 된 상태 전이 |
| `PURCHASE_LOCKED` | 409 | 구매관리 반영으로 잠김 |
| `SEQ_EXHAUSTED` | 409 | 관리번호 999 초과 (open-11) |
| `EXPORT_NOT_APPROVED` | 409 | 승인되지 않은 견적서를 개별 엑셀/PDF로 내보내려 시도 |

응답 형태: `{ "detail": { "code": "...", "message": "..." } }`.
