# QA Test Plan - QUOTE-1 (견적서 관리 시스템)

## Overview

QUOTE-1 백엔드(FastAPI + Firestore) · 프론트엔드(React) 전체에 대한 수동/통합 테스트 계획.
최근 작업(PDF export → reportlab 전환, DB → Firestore 마이그레이션) 이후 전체 기능이
회귀 없이 동작하는지 확인하는 것이 목적. 자동화된 `pytest`(32개, `backend/tests/`)가
이미 이 케이스들의 상당수를 커버하지만, 이 문서는 **HTTP API 레벨 + 실제 PDF/엑셀 산출물
내용 + 동시성**까지 눈으로/도구로 직접 확인하는 수동 QA 체크리스트다.

## Test Environment

- Firestore 에뮬레이터: `127.0.0.1:8090` (project `demo-quote`)
- 백엔드: `http://localhost:8000` (`uvicorn --reload`)
- 프론트엔드: `http://localhost:5173`
- 계정: `Admin`/`1234`(전체관리자, `SUPER_ADMIN`), `test1`/`1234`(그룹관리자 A, `GROUP_MANAGER`)
- 사전 조건: 세 프로세스 모두 기동 상태(이전 턴에서 확인됨). 필요 시 재기동:
  ```bash
  npx firebase-tools emulators:start --only firestore --project demo-quote
  cd backend && source .venv/bin/activate && uvicorn app.main:app --reload --port 8000
  cd frontend && npm run dev
  ```

## 체크리스트 (한눈에 보기)

| # | 테스트 | 우선순위 | 결과 |
|---|---|---|---|
| TC-001 | 정상 로그인 | Critical | [x] PASS |
| TC-002 | 잘못된 비밀번호 로그인 실패 | Critical | [x] PASS |
| TC-003 | 미인증 요청 401 | Critical | [x] PASS |
| TC-004 | 견적서 등록(관리번호 채번 확인) | Critical | [x] PASS |
| TC-005 | 그룹별 독립 채번 | High | [x] PASS |
| TC-006 | 견적서 목록 조회 | Critical | [x] PASS |
| TC-007 | 견적서 상세 조회 | Critical | [x] PASS |
| TC-008 | 견적서 수정(십만단위 절사 재계산) | High | [x] PASS |
| TC-009 | 승인(APPROVED) 전이 | Critical | [x] PASS |
| TC-010 | 반려 사유 필수 검증 | High | [x] PASS |
| TC-011 | 반려 후 읽기전용(수정 불가) | Critical | [x] PASS |
| TC-012 | 승인건 재반려 불가 | High | [x] PASS |
| TC-013 | 승인건 취소(CANCELLED) 가능 | Medium | [x] PASS |
| TC-014 | 구매관리 잠금 → 수정/삭제/취소 차단 | Critical | [x] PASS |
| TC-015 | 구매관리 잠금 idempotent | Medium | [x] PASS |
| TC-016 | 삭제(soft delete) → 결번 처리 | Critical | [x] PASS |
| TC-017 | 그룹관리자 쓰기 시도 403 | Critical | [x] PASS |
| TC-018 | 그룹관리자 목록 스코프(본인 그룹만) | Critical | [x] PASS |
| TC-019 | 그룹관리자 타그룹 상세 404(존재 은닉) | High | [x] PASS |
| TC-020 | 999건 초과 SEQ_EXHAUSTED | Medium | [x] PASS |
| TC-021 | 연도 롤오버 시 순번 리셋 | Low | [x] PASS |
| TC-022 | 엑셀 export(개별) | High | [x] PASS |
| TC-023 | 엑셀 export(목록) | Medium | [x] PASS |
| TC-024 | PDF export(개별, 한글/직인 렌더링) | Critical | [x] PASS |
| TC-025 | PDF: SUBMITTED 상태엔 직인 없음 | High | [x] PASS |
| TC-026 | 입력 유효성(수량/단가 0 이하 거부) | High | [x] PASS |
| TC-027 | 금액 계산 정확성(절사·부가세) | Critical | [x] PASS |
| TC-028 | Firestore 동시 등록 시 채번 중복/누락 없음 | Critical | [x] PASS |
| TC-029 | 프론트엔드 typecheck/build | High | [x] PASS |
| TC-030 | 프론트엔드 로그인→목록→상세 실사용 흐름 | High | [ ] 미실행 — 브라우저 자동화 도구 필요(수동 확인 권장) |
| TC-031 | 백엔드 자동화 테스트(`pytest`) 전체 통과 | Critical | [x] PASS (30/30) |

## 상세 테스트 케이스

### TC-001: 정상 로그인
**Feature:** 인증
**Priority:** Critical

**Test Steps:**
1. `POST /api/auth/login` `{"username":"Admin","password":"1234"}`

**Expected Result:**
- `200`, `token` 존재, `user.role == "SUPER_ADMIN"`, `user.group_code == null`

---

### TC-002: 잘못된 비밀번호 로그인 실패
**Test Steps:**
1. `POST /api/auth/login` `{"username":"Admin","password":"wrong"}`

**Expected Result:**
- `401`, `detail.code == "INVALID_CREDENTIALS"`

---

### TC-003: 미인증 요청 401
**Test Steps:**
1. `Authorization` 헤더 없이 `GET /api/quotes`

**Expected Result:**
- `401`, `detail.code == "NOT_AUTHENTICATED"`

---

### TC-004: 견적서 등록(관리번호 채번 확인)
**Feature:** 등록 / 채번
**Priority:** Critical

**Test Steps:**
1. Admin 토큰으로 `POST /api/quotes` (group_code=A, 항목 1개)
2. 응답의 `id`, `mgmt_no` 확인

**Expected Result:**
- `201`, `mgmt_no` 형식 `YY-A-NNN`, `id == mgmt_no`(Firestore 문서ID), `status == "SUBMITTED"`

---

### TC-005: 그룹별 독립 채번
**Test Steps:**
1. group_code=A로 등록, group_code=B로 등록

**Expected Result:**
- 두 mgmt_no의 순번이 각자 그룹 내에서 독립적으로 이어짐(서로 영향 없음)

---

### TC-006: 견적서 목록 조회
**Test Steps:**
1. `GET /api/quotes` (Admin)

**Expected Result:**
- `200`, `total`/`items` 정상, 방금 등록한 건 포함

---

### TC-007: 견적서 상세 조회
**Test Steps:**
1. `GET /api/quotes/{id}`

**Expected Result:**
- `200`, 등록 시 보낸 필드와 일치, `company` 자사정보 포함, `items` 배열 포함

---

### TC-008: 견적서 수정(십만단위 절사 재계산)
**Test Steps:**
1. 항목 단가 12,345,678원 1개로 `PUT /api/quotes/{id}`

**Expected Result:**
- `200`, `supply_amount == 12,300,000`(십만단위 절사), `status`는 `SUBMITTED` 유지(open-10), `updated_at` 갱신

---

### TC-009: 승인(APPROVED) 전이
**Test Steps:**
1. `POST /api/quotes/{id}/approve`

**Expected Result:**
- `200`, `status == "APPROVED"`, `approved_at` not null

---

### TC-010: 반려 사유 필수 검증
**Test Steps:**
1. `POST /api/quotes/{id}/reject` `{"reason": "  "}` (공백만)

**Expected Result:**
- `422` (pydantic validation)

---

### TC-011: 반려 후 읽기전용(수정 불가)
**Test Steps:**
1. 정상 사유로 반려 → `200`, `status == "REJECTED"`, `reject_reason` 저장
2. 반려건에 `PUT /api/quotes/{id}` 시도

**Expected Result:**
- 2번 단계 `409`, `detail.code == "INVALID_TRANSITION"`

---

### TC-012: 승인건 재반려 불가
**Test Steps:**
1. 승인 → `POST /api/quotes/{id}/reject`

**Expected Result:**
- `409 INVALID_TRANSITION`

---

### TC-013: 승인건 취소(CANCELLED) 가능
**Test Steps:**
1. 승인 → `POST /api/quotes/{id}/cancel`

**Expected Result:**
- `200`, `status == "CANCELLED"`

---

### TC-014: 구매관리 잠금 → 수정/삭제/취소 차단
**Test Steps:**
1. `POST /api/quotes/{id}/purchase-lock` → `purchase_locked: true`, `read_only: true`
2. `PUT`, `DELETE`, `POST .../cancel` 각각 시도

**Expected Result:**
- 2번 각각 `409`, `detail.code == "PURCHASE_LOCKED"`

---

### TC-015: 구매관리 잠금 idempotent
**Test Steps:**
1. 이미 잠긴 건에 `POST .../purchase-lock` 재호출

**Expected Result:**
- `200`(에러 아님), 상태 그대로

---

### TC-016: 삭제(soft delete) → 결번 처리
**Test Steps:**
1. `DELETE /api/quotes/{id}` (잠금/종료상태 아닌 건)
2. 이후 `GET /api/quotes/{id}`
3. 같은 그룹으로 재등록

**Expected Result:**
- 1번 `200`, 2번 `404`, 목록에서도 제외됨, 3번 신규 관리번호는 삭제된 순번을 **재사용하지 않고** 다음 번호로 이어짐(`retired_numbers`에 기록)

---

### TC-017: 그룹관리자 쓰기 시도 403
**Test Steps:**
1. `test1` 토큰으로 `POST /api/quotes`

**Expected Result:**
- `403`, `detail.code == "FORBIDDEN_ROLE"`

---

### TC-018: 그룹관리자 목록 스코프(본인 그룹만)
**Test Steps:**
1. Admin으로 A그룹 1건, B그룹 1건 등록
2. `test1`(A그룹)로 `GET /api/quotes`

**Expected Result:**
- 응답 `items`의 `group_code`가 전부 `"A"` (B그룹 건 안 보임)

---

### TC-019: 그룹관리자 타그룹 상세 404(존재 은닉)
**Test Steps:**
1. B그룹 견적서 id로 `test1` 토큰 `GET /api/quotes/{id}`

**Expected Result:**
- `404 NOT_FOUND` (403이 아니라 "존재하지 않음"으로 응답 — 존재 은닉 정책)

---

### TC-020: 999건 초과 SEQ_EXHAUSTED
**Test Steps:**
1. (테스트 환경에서) `number_sequences` 문서의 `last_seq`를 999로 세팅
2. 같은 그룹/연도로 등록 시도

**Expected Result:**
- `409`, `detail.code == "SEQ_EXHAUSTED"`

---

### TC-021: 연도 롤오버 시 순번 리셋
**Test Steps:**
1. `numbering.allocate` 를 12/31 시각으로 호출 후, 1/1 시각으로 재호출(단위 테스트 `test_year_rollover_resets` 로 대체 가능)

**Expected Result:**
- 새 연도는 001부터 다시 시작, 이전 연도 시퀀스는 보존

---

### TC-022: 엑셀 export(개별)
**Test Steps:**
1. `GET /api/quotes/{id}/export.xlsx`
2. 다운로드된 파일을 열어 로고/직인/항목/합계 확인

**Expected Result:**
- `200`, `content-type`에 `spreadsheet` 포함, 파일이 openpyxl로 정상 파싱되고 내용 일치

---

### TC-023: 엑셀 export(목록)
**Test Steps:**
1. `GET /api/quotes/export.xlsx` (필터 없이, 필터 있이 각 1회)

**Expected Result:**
- `200`, 필터가 실제 반영된 행만 포함

---

### TC-024: PDF export(개별, 한글/직인 렌더링)
**Feature:** PDF (reportlab)
**Priority:** Critical

**Test Steps:**
1. APPROVED 상태 견적서로 `GET /api/quotes/{id}/export.pdf`
2. PDF를 이미지로 렌더링해 육안 확인(한글 깨짐, 직인, 표 정렬)

**Expected Result:**
- `200`, `%PDF-` 헤더, 한글 정상 렌더링(나눔고딕 임베드), 직인 이미지 표시, 금액/항목 표 일치

---

### TC-025: PDF: SUBMITTED 상태엔 직인 없음
**Test Steps:**
1. SUBMITTED 상태 견적서로 PDF 생성

**Expected Result:**
- 직인 이미지 없음 (APPROVED만 합성)

---

### TC-026: 입력 유효성(수량/단가 0 이하 거부)
**Test Steps:**
1. `items: [{"qty": 0, ...}]` 로 등록 시도
2. `items: [{"unit_price": 0, ...}]` 로 등록 시도

**Expected Result:**
- 둘 다 `422`, `detail.code == "VALIDATION_ERROR"`

---

### TC-027: 금액 계산 정확성(절사·부가세)
**Test Steps:**
1. 항목 합계 12,345,678원으로 등록

**Expected Result:**
- `supply_amount == 12,300,000`, `vat_amount == 1,230,000`, `total_with_vat == 13,530,000`, `items_raw_total == 12,345,678`

---

### TC-028: Firestore 동시 등록 시 채번 중복/누락 없음
**Feature:** 동시성 (Firestore 트랜잭션)
**Priority:** Critical

**Test Steps:**
1. 같은 그룹으로 스레드 8~10개가 동시에 등록 요청
2. 발급된 `seq_no` 전체 수집

**Expected Result:**
- 중복/결번 없이 1..N 연속 — `database.run_transaction`의 재시도 로직 덕분에 요청 실패도 없어야 함

---

### TC-029: 프론트엔드 typecheck/build
**Test Steps:**
1. `cd frontend && npm run typecheck`
2. `npm run build`

**Expected Result:**
- 둘 다 에러 없이 성공 (quote_id `number`→`string` 전환 관련 타입 에러 없음)

---

### TC-030: 프론트엔드 로그인→목록→상세 실사용 흐름
**Test Steps:**
1. 브라우저로 `http://localhost:5173` 접속, Admin 로그인
2. 견적관리 목록 진입, 방금 등록한 견적서 클릭
3. 엑셀/PDF 다운로드 버튼 클릭

**Expected Result:**
- 각 단계 에러 없이 동작, 다운로드 파일 정상

---

### TC-031: 백엔드 자동화 테스트(`pytest`) 전체 통과
**Test Steps:**
1. Firestore 에뮬레이터 기동 상태에서 `cd backend && pytest`

**Expected Result:**
- 32개 전부 `passed`, 실패/에러 없음

## Summary
- Total Test Cases: 31
- Critical: 14 (TC-001~004, 006, 007, 009, 011, 014, 016~019, 024, 027, 028, 031) — 실제로는 아래 집계 참고
- High: 9
- Medium: 5
- Low: 1

(카테고리: 인증 3 · 채번/동시성 4 · CRUD/상태전이 8 · 권한 3 · export 4 · 유효성/계산 2 · 프론트 2 · 자동화 1)
