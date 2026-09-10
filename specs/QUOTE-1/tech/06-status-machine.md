# 06. 상태 머신

## 상태

`SUBMITTED` · `APPROVED` · `REJECTED` · `CANCELLED`

## 허용 전이 (`services/status.py: ALLOWED`)

| from | action | to | 추가 조건 |
|---|---|---|---|
| SUBMITTED | approve | APPROVED | — |
| SUBMITTED | reject | REJECTED | `reason` 비어있지 않음 |
| SUBMITTED | cancel | CANCELLED | not purchase_locked |

- 그 외 모든 `(from, action)` → `AppError("INVALID_TRANSITION", 409)`. `APPROVED`에서의 `cancel`/`reject`도 포함(승인은 되돌릴 수 없음).
- `APPROVED`, `REJECTED`, `CANCELLED` 은 종료 상태 (out-edge 없음) — `TERMINAL_STATUSES`.
- 재제출은 상태 전이가 아님 → 신규 `POST /quotes` (원본 `REJECTED` 유지).

## 가드 (`guard_mutable(quote) -> None | raise`)

수정(PUT) / 삭제(DELETE) 공통 선행 검사(취소는 `apply_transition`의 `ALLOWED` 조회로 별도 차단):

1. `quote.deleted_at` → `NOT_FOUND`
2. `quote.purchase_locked` → `PURCHASE_LOCKED` (409)
3. `quote.status in TERMINAL_STATUSES` (`APPROVED`/`REJECTED`/`CANCELLED`) → `INVALID_TRANSITION` (읽기전용 보존)

## `apply_edit_policy(quote, payload)` — open-10 임시 결정 격리 지점

```
# 임시 결정: 전체 필드 수정 허용, 상태값 유지, 감사로그 미기록
quote.<fields> = payload.<fields>
quote.updated_at = now()
# (협의 후) 예: if quote.status == APPROVED: quote.status = SUBMITTED  ← 여기만 수정
```

## 전이 시 타임스탬프

| action | 세팅 |
|---|---|
| approve | `status=APPROVED`, `approved_at=now()` |
| reject | `status=REJECTED`, `rejected_at=now()`, `reject_reason=reason` |
| cancel | `status=CANCELLED`, `cancelled_at=now()` |
| purchase-lock | `purchase_locked=true`, `locked_at=now()` (이미 true면 no-op 200) |
