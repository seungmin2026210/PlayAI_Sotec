# 1. Firestore 데이터 모델 (자산관리)

배경: [`../DECISIONS.md`](../DECISIONS.md), [`../TECH.md`](../TECH.md). 컨벤션은 QUOTE-1/PURCHASE-1과 동일 —
의미 있는 문서 ID 우선, 비즈니스 날짜는 `YYYY-MM-DD` 문자열, 시스템 시각은 Timestamp, soft delete는 상태값.

> **설계 단계(미구현).** [`../COORDINATION.md`](../COORDINATION.md) 합의 후 구현.
> PURCHASE-1 `tech/01-data-model.md` §4·§6·§7(`asset_units` 기반 배정 스케치)을 **대체**한다(COORDINATION C1).

## 컬렉션 개요

| 컬렉션 | 문서 ID | 용도 |
|---|---|---|
| `assets/{asset_no}` | `SW-26-001` | 자산 본체 |
| `asset_seq/{category}-{YY}` | `SW-26` | 유형·연도별 채번 카운터 |
| `asset_assignments/{auto-id}` | auto | 사용 이력(배정 1건 = 1문서) |
| `members/{employee_no}` | 사번 | 팀원 명단 |
| `asset_units/{unit_no}` | (기존) | **`asset_no` 필드만 추가**(COORDINATION C3) |

## 1. `assets/{asset_no}`

문서 ID = `asset_no` — 채번 트랜잭션이 유일성을 보장하므로 auto-id 불필요(`quotes/{mgmt_no}`와 동일 이유).

```jsonc
{
  "asset_no": "SW-26-001",
  "category": "SW",                  // SW | HW | EDU (config.ASSET_CATEGORIES 재사용)
  "subcategory": "AI_SUB",           // config.ASSET_SUBCATEGORIES[category] 키. EDU는 null
  "name": "GitHub Copilot Business",
  "status": "IN_USE",                // IDLE | IN_USE | DISPOSED — 트랜잭션으로만 갱신

  // 그룹
  "group_code": "A",                 // 등록 그룹(미사용일 때 소속)
  "scope_group_code": "B",           // 조회 스코프용 파생값: 사용 중이면 현재 사용자 그룹, 아니면 group_code (D24)

  // 현재 사용자(비정규화 — 목록/사용자 필터를 조인 없이)
  "current_member_id": "Z2300115",   // null = 미사용
  "current_member_name": "김철수",
  "current_assignment_id": "abc...", // 트랜잭션에서 쿼리 없이 활성 이력 get() 하기 위함
  "current_start_date": "2026-03-02",

  // 구매·계약
  "purchase_date": "2026-01-10",     // null 허용. 번호 연도 기준(채번 후 수정해도 번호 불변 — D7)
  "price": 1200000,                  // 정수(원), null 허용
  "purchased_from": "OO리셀러",
  "quote_no": "26-A-003",            // quotes 문서 ID(= mgmt_no). null 허용
  "contract_no": "C-2026-11",        // 임시 자유입력(D11). 계약관리 생기면 참조로 교체
  "source_unit_no": "인텔리제이-001", // 가져오기로 만든 경우 asset_units 문서 ID, 직접 등록은 null

  // 유효기간
  "valid_from": "2026-01-10",
  "valid_to": "2027-01-09",          // null = 무기한. 대시보드 캘린더 기준

  // SW 전용 (다른 유형은 null)
  "version": "1.93",
  "license_key": "XXXX-....",
  // SW / EDU 공통
  "account_id": "sotec_dev01",
  "password_enc": "gAAAA...",        // Fernet 암호문. 응답 스키마엔 절대 포함 안 함 → has_password: bool 로만 노출
  // HW 전용
  "manufacturer": "LG",
  "model": "16Z90S",
  "serial_no": "SN123...",
  "mac_address": null,
  // EDU 전용
  "course_title": "스프링 핵심 원리",
  "course_url": "https://www.inflearn.com/course/...",

  "note": "",
  "disposed_at": null,
  "created_at": <Timestamp>, "created_by": "Admin",
  "updated_at": <Timestamp>, "updated_by": "Admin"
}
```

유형별 필드는 서브맵이 아니라 **평평하게** 둔다 — 키워드 검색·엑셀 컬럼 매핑이 단순해지고, 문서 크기 영향 없음.

## 2. `asset_seq/{category}-{YY}`

```jsonc
{ "last_seq": 12 }
```

`services/numbering.py`의 `number_sequences/{year}-{group}` 패턴 그대로. `YY` = `purchase_date` 연도,
없으면 등록 시점 서버 연도(D7). `last_seq > 999` → `409 SEQ_EXHAUSTED`. 되돌리지 않음(영구 결번).

## 3. `asset_assignments/{auto-id}`

배정 1건마다 새 문서(PURCHASE-1 원칙 "배정/반납은 이력이 되는 구조" 유지).

```jsonc
{
  "asset_no": "SW-26-001",
  "category": "SW",                  // 사용자별 탭에서 유형별 개수 집계용 비정규화
  "asset_name": "GitHub Copilot Business",
  "member_id": "Z2300115",
  "member_name": "김철수",            // 배정 시점 이름(스냅샷)
  "start_date": "2026-03-02",        // 관리자 입력(D18)
  "end_date": null,                  // null = 사용 중
  "note": "",
  "created_at": <Timestamp>, "created_by": "Admin",
  "updated_at": <Timestamp>, "updated_by": "Admin"   // 이력 수정(D20) 추적
}
```

## 4. `members/{employee_no}`

```jsonc
{
  "employee_no": "Z2300115",         // 문서 ID와 동일(임시 결정 P5)
  "name": "김철수",
  "group_code": "B",
  "active": true,                    // false = 퇴사. 삭제 없음
  "created_at": <Timestamp>, "updated_at": <Timestamp>
}
```

## 5. `asset_units/{unit_no}` 추가 필드 (COORDINATION C3)

```jsonc
{ "asset_no": null }                 // 가져오기 트랜잭션만 씀. 기존 문서엔 필드 없음 = null 취급
```

## 6. 트랜잭션

모두 `database.run_transaction`(재시도 래퍼) 사용. **read가 write보다 먼저**(Firestore 제약).

### 6-1. 구매에서 가져오기
1. read `asset_units/{unit_no}` → 없음 404, `retired_at` 있음 409 `ALREADY_RETIRED`, `asset_no` 있음 409 `ALREADY_IMPORTED`
2. read `asset_seq/{cat}-{YY}` → 번호 계산
3. write seq, write `assets/{asset_no}`(COORDINATION C5 매핑 + 폼 입력 병합), update unit `asset_no`

### 6-2. 직접 등록
6-1에서 1단계 없이 2~3단계(unit update 없음).

### 6-3. 배정
read asset(`IDLE` 아니면 409 `ASSET_NOT_IDLE`/`ASSET_DISPOSED`), read member(`active=false`면 409) →
create assignment, update asset(`IN_USE`, `current_*`, `scope_group_code = member.group_code`).

### 6-4. 회수
read asset → read `asset_assignments/{current_assignment_id}` → `end_date` 설정,
asset(`IDLE`, `current_* = null`, `scope_group_code = group_code`).

### 6-5. 사용자 변경(이관)
read asset, 현재 assignment, 새 member → 현재 assignment `end_date = 변경일`, 새 assignment(`start_date = 변경일`),
asset `current_*`·`scope_group_code` 교체. 한 트랜잭션(D17).

### 6-6. 이력 수정(D20)
read assignment + 같은 `asset_no`의 다른 이력(쿼리) → `start_date <= end_date`, 기간 겹침 없음(P4) 확인 →
update 날짜·비고·`updated_*`. 활성 이력의 `start_date`를 고치면 asset `current_start_date`도 갱신.

### 6-7. 팀원 그룹 변경(P3)
member update + 그 사람이 쓰는 `assets`(`current_member_id == X`)의 `scope_group_code` 일괄 갱신.
(개인당 자산 수십 건 수준 — 한 트랜잭션 500 write 한도 내)

## 7. 조회

`services/query.py` 원칙 그대로: **등호 필터만 Firestore**, 나머지는 애플리케이션 레벨.

- Firestore: `category ==`, `scope_group_code ==`(그룹관리자), `status ==`/`!= DISPOSED`, `current_member_id ==`
- 앱 레벨: 키워드 부분일치, 만료여부(`valid_to` vs 오늘), 구매연도(`purchase_date[:4]`), 소분류, 정렬, 페이지네이션
- 사용자별 탭: `members` 목록 + `assets where status == IN_USE`를 한 번 읽어 `current_member_id`·`category`로 집계.
  한 사람 상세: `asset_assignments where member_id == X`(현재+과거 모두, `end_date` null 여부로 구분)
- 대시보드 갱신: `assets where status != DISPOSED`(+스코프) → `valid_to` 기간 필터 → `(valid_to, name)`으로 묶음
- 복합 인덱스(`category`+`scope_group_code`+`status` 등)는 쿼리 작성 시 에러 보고 `firestore.indexes.json`에 추가(QUOTE-1과 동일 절차)
