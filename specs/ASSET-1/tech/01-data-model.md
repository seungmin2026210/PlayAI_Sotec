# 1. Firestore 데이터 모델 (자산관리)

배경: [`../DECISIONS.md`](../DECISIONS.md), [`../TECH.md`](../TECH.md). 컨벤션은 QUOTE-1/PURCHASE-1과 동일 —
의미 있는 문서 ID 우선, 비즈니스 날짜는 `YYYY-MM-DD` 문자열, 시스템 시각은 Timestamp, soft delete는 상태값.

> **구현됨**(2026-09-28). [`../COORDINATION.md`](../COORDINATION.md) 는 제안안대로 임시 확정.
> 설계 대비 달라진 점은 [`../TECH.md`](../TECH.md) "구현 메모".
> PURCHASE-1 `tech/01-data-model.md` §4·§6·§7(`asset_units` 기반 배정 스케치)을 **대체**한다(COORDINATION C1).

**날짜 기준(D45)**: "오늘"·"올해"는 전부 KST. `services/asset_dates.py: today_kst()` 한 곳에서만 계산하고
(`datetime.now(ZoneInfo("Asia/Seoul")).date()`), 채번 연도·만료 배지·기본 날짜·미래 날짜 검사가 모두 이걸 쓴다.

## 컬렉션 개요

| 컬렉션 | 문서 ID | 용도 |
|---|---|---|
| `assets/{asset_no}` | `SW-26-001` | 자산 본체 |
| `asset_seq/{category}-{YY}` | `SW-26` | 유형·연도별 채번 카운터 |
| `asset_assignments/{auto-id}` | auto | 사용 이력(배정 1건 = 1문서) |
| `asset_renewals/{auto-id}` | auto | 갱신 기록(갱신 1회 = 1문서, 여러 자산 묶음 — D32) |
| `password_reveal_logs/{auto-id}` | auto | 비밀번호 열람 기록(D44) |
| `members/{employee_no}` | 사번 | 팀원 명단 |
| `asset_units/{unit_no}` | (기존) | **`asset_link_kind`·`asset_nos` 필드만 추가**(COORDINATION C3) |

## 1. `assets/{asset_no}`

문서 ID = `asset_no` — 채번 트랜잭션이 유일성을 보장하므로 auto-id 불필요(`quotes/{mgmt_no}`와 동일 이유).

```jsonc
{
  "asset_no": "SW-26-001",
  "category": "SW",                  // SW | HW | EDU (config.ASSET_CATEGORIES 재사용). 등록 후 불변(D41)
  "subcategory": "AI_SUB",           // config.ASSET_SUBCATEGORIES[category] 키. EDU는 null
  "name": "GitHub Copilot Business",
  "status": "IN_USE",                // IDLE | IN_USE | DISPOSED | DELETED(D47) — 트랜잭션으로만 갱신

  // 그룹
  "group_code": "A",                 // 등록 그룹(미사용·공용일 때 소속)
  "scope_group_code": "B",           // 조회 스코프용 파생값: 팀원 사용 중이면 그 팀원 그룹, 아니면 group_code (D24, D33)

  // 현재 사용자(비정규화 — 목록/사용자 필터를 조인 없이)
  "current_member_id": "Z2300115",   // 팀원 배정일 때만. 공용·미사용이면 null
  "current_member_name": "김철수",    // 팀원 이름 변경 시 갱신(D40, §8-7)
  "current_shared_label": null,      // 공용 배정일 때 장소/용도(예: "3층 회의실"). 팀원 배정·미사용이면 null (D33)
  "current_assignment_id": "abc...", // 트랜잭션에서 쿼리 없이 활성 이력 get() 하기 위함
  "current_start_date": "2026-03-02",

  // 구매·계약
  "purchase_date": "2026-01-10",     // null 허용. 번호 연도 기준(채번 후 수정해도 번호 불변 — D7)
  "price": 120000,                   // 정수(원), null 허용. 수량 N 가져오기는 구매금액 ÷ N(나머지는 첫 자산 — P9)
  "purchased_from": "OO리셀러",
  "quote_no": "26-A-003",            // quotes 문서 ID(= mgmt_no). null 허용
  "contract_no": "C-2026-11",        // 임시 자유입력(D11). 계약관리 생기면 참조로 교체
  "source_unit_no": "인텔리제이-001", // 가져오기로 만든 경우 asset_units 문서 ID(N건 모두 같은 값), 직접 등록은 null

  // 유효기간
  "valid_from": "2026-01-10",
  "valid_to": "2027-01-09",          // null = 무기한. 대시보드 캘린더 기준. 갱신(§8-10)으로 연장

  // SW 전용 (다른 유형은 null)
  "version": "1.93",
  "license_key": "XXXX-....",        // 그룹관리자 응답에선 presenter가 앞 4자리만 남기고 마스킹(D38)
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
  "disposed_reason": null,           // DISPOSED | IMPORT_CANCELLED (D35). 폐기 아닐 땐 null
  "deleted_at": null,                // 삭제(D47) 시각·처리자·사유(필수). 삭제 아닐 땐 null
  "deleted_by": null,
  "deleted_reason": null,
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
없으면 `today_kst()` 연도(D7, D45). **수량 N(D31)이면 `last_seq+1 ~ last_seq+N`을 한 번에 확보**하고
`last_seq += N`. `last_seq + N > 999` → `409 SEQ_EXHAUSTED`(한 건도 만들지 않음). 되돌리지 않음(영구 결번).

## 3. `asset_assignments/{auto-id}`

배정 1건마다 새 문서(PURCHASE-1 원칙 "배정/반납은 이력이 되는 구조" 유지).

```jsonc
{
  "asset_no": "SW-26-001",
  "category": "SW",                  // 사용자별 탭에서 유형별 개수 집계용 비정규화
  "asset_name": "GitHub Copilot Business",
  "member_id": "Z2300115",           // 공용 배정이면 null
  "member_name": "김철수",            // 배정 시점 이름(스냅샷 — 이름이 바뀌어도 유지, D40). 공용이면 null
  "shared_label": null,              // 공용 배정일 때 장소/용도 (D33)
  "start_date": "2026-03-02",        // 관리자 입력(D18), 규칙은 D36
  "end_date": null,                  // null = 사용 중
  "prev_assignment_id": null,        // 이관(§8-5)으로 생긴 경우 직전 배정 문서 ID — 배정 취소(§8-8) 시 복구용
  "note": "",
  "created_at": <Timestamp>, "created_by": "Admin",
  "updated_at": <Timestamp>, "updated_by": "Admin"   // 이력 수정(D20) 추적
}
```

## 4. `asset_renewals/{auto-id}` (D32)

```jsonc
{
  "asset_nos": ["SW-26-001", "SW-26-002", ...], // 이번 갱신에 포함된 자산. 상세 화면은 array_contains 로 조회
  "name": "GitHub Copilot Business",
  "prev_valid_to": "2026-12-31",
  "new_valid_from": "2027-01-01",
  "new_valid_to": "2027-12-31",
  "unit_no": "Copilot-011",          // 연결한 갱신 구매 유닛. 없으면 null
  "created_at": <Timestamp>, "created_by": "Admin"
}
```

## 5. `password_reveal_logs/{auto-id}` (D44)

```jsonc
{ "asset_no": "SW-26-001", "username": "Admin", "action": "REVEAL", "at": <Timestamp> }
// action: REVEAL | COPY (프론트가 어떤 버튼인지 보냄. 서버 입장에선 둘 다 평문 반환)
```

쓰기만 한다. 조회 화면은 범위 밖.

## 6. `members/{employee_no}`

```jsonc
{
  "employee_no": "Z2300115",         // 문서 ID와 동일(임시 결정 P5)
  "name": "김철수",
  "group_code": "B",
  "active": true,                    // false = 퇴사. 삭제 없음
  "created_at": <Timestamp>, "updated_at": <Timestamp>
}
```

## 7. `asset_units/{unit_no}` 추가 필드 (COORDINATION C3)

```jsonc
{
  "asset_link_kind": null,           // null | "IMPORTED"(자산으로 가져옴) | "RENEWED"(갱신에 연결됨)
  "asset_nos": []                    // 연결된 자산번호들. 기존 문서엔 두 필드 없음 = null/[] 취급
}
```

자산관리 트랜잭션만 쓴다. 가져오기 목록 = `asset_link_kind == null` && `retired_at == null` && 해당 유형.

## 8. 트랜잭션

모두 `database.run_transaction`(재시도 래퍼) 사용. **read가 write보다 먼저**(Firestore 제약).
날짜 검사(D36)는 `services/asset_dates.py`의 순수 함수로 두고 §8-3~8-6이 공유한다 —
입력: 대상 기간 + 같은 자산의 다른 이력들(트랜잭션 안에서 `asset_assignments where asset_no == X` 쿼리 read).

### 8-1. 구매에서 가져오기 (수량 N)
1. read `asset_units/{unit_no}` → 없음 404, `retired_at` 있음 409 `ALREADY_RETIRED`, `asset_link_kind` 있음 409 `ALREADY_IMPORTED`
2. read `asset_seq/{cat}-{YY}` → N개 번호 확보(§2)
3. write seq, write `assets/{asset_no}` × N(COORDINATION C5 매핑 + 폼 입력 병합, 금액 분할 P9),
   update unit `asset_link_kind = "IMPORTED"`, `asset_nos = [...]`

N 상한 100(P8) — 한 트랜잭션 write 수 N+2, Firestore 500 한도 내.

### 8-2. 직접 등록 (수량 N)
8-1에서 1단계 없이 2~3단계(unit update 없음, 금액은 입력값을 자산마다 그대로).

### 8-3. 배정
read asset(`DISPOSED`면 409 `ASSET_DISPOSED`, `IDLE` 아니면 409 `ASSET_NOT_IDLE`), 팀원이면 read member
(`active=false`면 409 `MEMBER_INACTIVE`), 공용이면 EDU 여부 확인(400), 다른 이력 read → 날짜 검사 →
create assignment, update asset(`IN_USE`, `current_*`, `scope_group_code` = 팀원 그룹 또는 `group_code`).

### 8-4. 회수
read asset → read `asset_assignments/{current_assignment_id}` → 날짜 검사 → `end_date` 설정,
asset(`IDLE`, `current_* = null`, `scope_group_code = group_code`).

### 8-5. 사용자 변경(이관)
read asset, 현재 assignment, 새 member(팀원일 때), 다른 이력 → 날짜 검사(변경일 ≥ 현재 `start_date`, 미래 불가) →
현재 assignment `end_date = 변경일`, 새 assignment(`start_date = 변경일`, `prev_assignment_id = 현재 ID`),
asset `current_*`·`scope_group_code` 교체. 한 트랜잭션(D17).

### 8-6. 이력 수정(D20)
read assignment + 같은 `asset_no`의 다른 이력 → 날짜 검사(D36, 활성 이력의 `end_date` 채우기 금지) →
update 날짜·비고·`updated_*`. 활성 이력의 `start_date`를 고치면 asset `current_start_date`도 갱신.

### 8-7. 팀원 수정(그룹 변경 P3 · 이름 변경 D40)
member update + 그 사람이 쓰는 `assets`(`current_member_id == X`)의 `scope_group_code`(그룹 변경 시)·
`current_member_name`(이름 변경 시) 일괄 갱신. `asset_assignments.member_name`은 스냅샷이라 건드리지 않는다.
(개인당 자산 수십 건 수준 — 한 트랜잭션 500 write 한도 내)

### 8-8. 배정 취소(D34)
read asset(`IN_USE` 아니면 409 `ASSET_NOT_IN_USE`) → read 현재 assignment →
- `prev_assignment_id` 없음(배정으로 생김): assignment 삭제, asset `IDLE`·`current_* = null`·`scope_group_code = group_code`
- `prev_assignment_id` 있음(이관으로 생김): read 직전 assignment → 삭제 + 직전 assignment `end_date = null`,
  asset `current_*`·`scope_group_code`를 직전 사용자로 복구(팀원이면 member read 해서 현재 그룹 사용)

이력 문서의 물리 삭제는 이 경우뿐이다.

### 8-9. 가져오기 취소(D35)
read unit → `assets where source_unit_no == unit_no` → 하나라도 `status == IN_USE`이거나 `asset_assignments`에
이력이 있으면 409 `ASSET_HAS_HISTORY` → assets 전부 `DISPOSED`(`disposed_reason = IMPORT_CANCELLED`,
`disposed_at`), unit `asset_link_kind = null`, `asset_nos = []`. 번호는 결번(seq 되돌리지 않음).

### 8-9a. 삭제(D47)
read asset → `DELETED`면 409 `ASSET_DELETED`, `DISPOSED`면 409 `ASSET_DISPOSED`, `source_unit_no`가 있으면 409
`ASSET_IMPORTED`, `IDLE`이 아니거나 `asset_assignments`/`asset_renewals`에 이 자산이 있으면 409 `ASSET_HAS_HISTORY`
→ `status = DELETED`, `deleted_at`·`deleted_by`·`deleted_reason`. 번호는 결번(seq 되돌리지 않음). 이후 모든 쓰기는
`ASSET_DELETED`(`services/asset_status.guard_not_disposed`).

### 8-10. 갱신(D32)
입력: `asset_nos[]`, `new_valid_to`(필수), `new_valid_from`(선택, 기본 이전 `valid_to` + 1일), `unit_no`(선택).
read assets 전부(폐기면 409 `ASSET_DISPOSED`, `valid_to == null` 또는 `new_valid_to <= valid_to`면 400),
`unit_no` 있으면 read unit(§8-1의 1단계와 같은 검사) →
assets `valid_from`/`valid_to` 갱신, create `asset_renewals`, unit 있으면 `asset_link_kind = "RENEWED"`, `asset_nos`.
선택한 자산들의 `valid_to`가 서로 다르면 400(같은 품명·같은 종료일 묶음 단위 — 화면도 그렇게 고르게 함).

### 8-11. 비밀번호 열람(D44)
트랜잭션 불필요. `can_reveal_password` 통과 → decrypt → `password_reveal_logs` add → 평문 반환.
로그 쓰기가 실패하면 평문도 반환하지 않는다(기록 없는 열람 방지).

## 9. 조회

`services/query.py` 원칙 그대로: **등호 필터만 Firestore**, 나머지는 애플리케이션 레벨.

- Firestore: `category ==`, `scope_group_code ==`(그룹관리자), `status ==`/`not in (DISPOSED, DELETED)`, `current_member_id ==`
- 앱 레벨: 키워드 부분일치(그룹관리자는 `license_key` 제외 — D38), 만료여부(`valid_to` vs `today_kst()`),
  구매연도(`purchase_date[:4]`), 소분류, 사용자 "공용"(`status == IN_USE && current_shared_label != null`), 정렬, 페이지네이션
- 사용자별 탭: `members`(그룹관리자는 `group_code ==` 본인 그룹 — D46) + `assets where status == IN_USE`를 한 번 읽어
  `current_member_id`·`category`로 집계(공용은 집계 제외).
  한 사람 상세: `asset_assignments where member_id == X`(현재+과거 모두, `end_date` null 여부로 구분).
  그룹관리자면 각 이력의 자산을 읽어 `scope_group_code != 본인 그룹`이면 `linkable: false`(D37)
- 대시보드 갱신: `assets where status not in (DISPOSED, DELETED)`(+스코프) → `valid_to` 기간 필터 → `(valid_to, name)`으로 묶음.
  KPI `expired` = `valid_to < today_kst()` 건수(D39)
- 자산 상세: 자산 + `asset_assignments where asset_no == X` + `asset_renewals where asset_nos array_contains X`
- 복합 인덱스(`category`+`scope_group_code`+`status` 등)는 쿼리 작성 시 에러 보고 `firestore.indexes.json`에 추가(QUOTE-1과 동일 절차)
