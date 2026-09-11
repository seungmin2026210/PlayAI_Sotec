# 11. 테스트 계획

## 도구

- `pytest`, `httpx` + `fastapi.testclient.TestClient`.
- 테스트 DB: Firestore 에뮬레이터(`FIRESTORE_EMULATOR_HOST`, 기본 `127.0.0.1:8090`). 트랜잭션 롤백이 아니라 `conftest.py`가 매 테스트 전 `quotes`/`number_sequences`/`retired_numbers` 문서를 전부 지운다. 에뮬레이터 미기동 시 DB 테스트는 skip, `tests/unit/`만 실행됨(구 설계였던 별도 PostgreSQL 스키마/`DATABASE_URL_TEST`는 폐기 — [`12-firestore-migration.md`](./12-firestore-migration.md)).

## 단위 테스트 (`tests/test_calculation.py`)

| 케이스 | 기대 |
|---|---|
| `items_raw_total` 여러 행 | 정확 합 |
| `supply_amount(12_345_678)` | `12_300_000` (십만단위 내림) |
| `supply_amount(50_000)` | `0` |
| `vat_amount(12_300_000)` | `1_230_000` |
| `total_with_vat` | supply + vat |
| `format_won(13_530_000)` | `"13,530,000원"` |

## 채번 (`tests/test_numbering.py`)

| 케이스 | 기대 |
|---|---|
| 신규 그룹/연도 첫 등록 | `26-A-001` |
| 연속 3건 | `001,002,003` |
| 1건 삭제 후 등록 | 삭제분 결번, 다음 번호로 진행(재사용 X), `retired_numbers` 1행 |
| `last_seq=999` 상태 등록 | `409 SEQ_EXHAUSTED` |
| 동시 2건(threads) 같은 그룹 | 관리번호 중복 없음, 연속 |
| 그룹 A/B 교차 등록 | 시퀀스 독립 (`26-A-001`, `26-B-001`) |

## 상태 전이 (`tests/test_status.py`)

| 케이스 | 기대 |
|---|---|
| SUBMITTED→approve | APPROVED, `approved_at` 설정 |
| SUBMITTED→reject (사유 O) | REJECTED, `reject_reason` 저장 |
| SUBMITTED→reject (사유 X) | 422 |
| APPROVED→reject | 409 INVALID_TRANSITION |
| APPROVED→cancel | 409 INVALID_TRANSITION |
| APPROVED 수정/삭제 | 409 INVALID_TRANSITION (읽기전용 보존) |
| REJECTED→approve | 409 |
| 잠금 후 수정/취소/삭제 | 409 PURCHASE_LOCKED |
| REJECTED 수정 | 409 (읽기전용 보존) |
| SUBMITTED 상태 개별 엑셀/PDF export | 409 EXPORT_NOT_APPROVED |
| APPROVED 개별 엑셀 export | 200 |

## 권한 (`tests/test_permissions.py`)

| 케이스 | 기대 |
|---|---|
| 그룹관리자 `POST /quotes` | 403 FORBIDDEN_ROLE |
| 그룹관리자 목록 | 본인 그룹만 반환 |
| 그룹관리자 타 그룹 상세 | 404 |
| 그룹관리자 export(본인 그룹, 승인됨) | 200 |
| 미인증 요청 | 401 |

## 통합 흐름 (`tests/test_flow.py`)

로그인(Admin) → 등록 → 목록 노출 → 상세 → 수정 → 삭제 → 목록에서 사라짐 + 결번 확인 → 재등록(결번 확인) → 승인 → 목록 엑셀 200 → 개별 엑셀 200 → 발송 200(안내 메시지) → 승인됨 수정/취소/삭제 409 확인.

## 수동 확인 (프론트)

- Admin / test1 각각 로그인 → 버튼 노출 차이 육안 확인.
- 등록 폼 실시간 합계·절사·부가세 미리보기.
- PDF 다운로드 (reportlab, 순수 파이썬이라 시스템 라이브러리 설치 여부와 무관하게 항상 가능 — 구 WeasyPrint 는 폐기됨).
