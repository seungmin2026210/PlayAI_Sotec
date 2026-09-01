# 03. 데이터 모델

## 테이블

### `quotes`

| 컬럼 | 타입 | 제약 | 비고 |
|---|---|---|---|
| id | bigserial | PK | |
| mgmt_no | varchar(16) | UNIQUE, NOT NULL | `YY-G-NNN` |
| seq_year | smallint | NOT NULL | 채번에 쓰인 연도(2026) |
| group_code | char(1) | NOT NULL, CHECK in (A..E) | |
| seq_no | smallint | NOT NULL | 1..999 |
| title | varchar(200) | NOT NULL | 견적서명 |
| issue_date | date | NOT NULL | 발행일자 |
| issuer_name | varchar(80) | NOT NULL | 발행 담당자명 |
| customer_name | varchar(200) | NOT NULL | 수신처(고객사)명 |
| customer_contact_name | varchar(80) | NULL | |
| customer_contact_phone | varchar(40) | NULL | |
| vat_included | boolean | NOT NULL | 부가세 포함/미포함 (견적 단위 1회) |
| supply_amount | bigint | NOT NULL | 공급가액 합계 (십만단위 절사 후) |
| vat_amount | bigint | NOT NULL | supply_amount * 0.1 |
| total_with_vat | bigint | NOT NULL | supply_amount + vat_amount |
| items_raw_total | bigint | NOT NULL | 절사 전 항목 합계 (감사/재현용) |
| status | varchar(12) | NOT NULL | SUBMITTED/APPROVED/REJECTED/CANCELLED |
| reject_reason | text | NULL | 반려 시 필수 |
| purchase_locked | boolean | NOT NULL default false | 구매관리 반영 잠금 |
| created_by | varchar(40) | NOT NULL | username |
| created_at | timestamptz | NOT NULL | |
| updated_at | timestamptz | NULL | |
| approved_at | timestamptz | NULL | 상태 전이 시각(감사 대비) |
| rejected_at | timestamptz | NULL | |
| cancelled_at | timestamptz | NULL | |
| locked_at | timestamptz | NULL | |
| deleted_at | timestamptz | NULL | soft delete (결번) |

인덱스: `(group_code, status)`, `(issue_date)`, `(seq_year, group_code, seq_no)`, `(deleted_at)`.

### `quote_items`

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | bigserial | PK |
| quote_id | bigint | FK → quotes.id ON DELETE CASCADE |
| line_no | smallint | NOT NULL (1부터) |
| name | varchar(200) | NOT NULL |
| qty | integer | NOT NULL, CHECK > 0 |
| unit_price | bigint | NOT NULL, CHECK > 0 (공급가액 기준) |
| line_amount | bigint | NOT NULL (qty * unit_price, 저장 시 계산) |

### `number_sequences` (동시성 제어)

| 컬럼 | 타입 | 제약 |
|---|---|---|
| seq_year | smallint | PK(복합) |
| group_code | char(1) | PK(복합) |
| last_seq | smallint | NOT NULL default 0 |

채번: `SELECT ... FOR UPDATE` → `last_seq + 1`. 행 없으면 `INSERT ... ON CONFLICT DO NOTHING` 후 재조회.

### `retired_numbers` (결번 대장)

| 컬럼 | 타입 | 제약 |
|---|---|---|
| id | bigserial | PK |
| mgmt_no | varchar(16) | UNIQUE |
| seq_year | smallint | NOT NULL |
| group_code | char(1) | NOT NULL |
| seq_no | smallint | NOT NULL |
| retired_at | timestamptz | NOT NULL |
| retired_by | varchar(40) | NOT NULL |
| reason | varchar(20) | NOT NULL ('DELETED') |

- 삭제 시: `quotes.deleted_at` 설정 + `retired_numbers` insert. `number_sequences.last_seq`는 **되돌리지 않음**(결번 유지, 재사용 금지).

## 상태-불변식

- `status='REJECTED'` → 해당 행 이후 수정 불가 (읽기전용 보존).
- `purchase_locked=true` → status 무관하게 수정/취소/삭제 불가.
- `deleted_at IS NOT NULL` → 모든 조회에서 제외.
- `reject_reason` 은 `status='REJECTED'` 일 때만 NOT NULL 이어야 함(앱 레벨 검증).
