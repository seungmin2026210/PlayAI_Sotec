# ASSET-1 · 기술 스펙 (Tech Spec)

> 사용자 대면 동작: [`PRODUCT.md`](./PRODUCT.md). 데이터 모델: [`tech/01-data-model.md`](./tech/01-data-model.md).
> 결정 로그: [`DECISIONS.md`](./DECISIONS.md). 구매관리 조율: [`COORDINATION.md`](./COORDINATION.md) — C1~C11 을
> 자산관리 쪽 제안안대로 **임시 확정**해 구현했다(구매관리 담당자 확인 대기).
>
> 상태: **구현 완료** (2026-09-28, 브랜치 `feature/asset-1`). 백엔드 `tests/test_assets.py` 41건 +
> `tests/unit/test_asset_rules.py` 10건 통과. 아래 "구현 메모"가 설계와 달라진 점.

## 구현 메모 (설계 대비)

- `services/asset_registration.py` 신설 — 직접 등록(§8-2)·가져오기(§8-1)·가져오기 취소(§8-9) 트랜잭션.
  `asset_bulk.py`는 순수 함수(입력 정리·금액 분할·수량 검사)만. `asset_renewal.py`는 갱신(§8-10)만.
- 목록·대시보드·사용자별 집계는 **등호 필터만** Firestore 에 걸고 나머지(폐기 제외 포함)는 앱 레벨 —
  등호만 쓰면 복합 인덱스가 필요 없어서 `firestore.indexes.json` 추가 없음.
- 날짜 규칙의 "겹침"은 경계가 맞닿는 것(앞 이력 종료일 == 새 시작일)을 허용 — 이관은 같은 날 인계라서.
- KST 는 `zoneinfo` 대신 고정 오프셋(UTC+9, `config.ASSET_TZ_OFFSET_HOURS`) — 서버리스 환경 tzdata 의존 제거.
- 도메인 규칙 위반은 `400 VALIDATION_ERROR`(PRODUCT 예외표), Pydantic 스키마 형식 오류는 기존대로 `422`.
- 팀원 중복 사번 등록은 `409 MEMBER_EXISTS`(신규 코드).
- 복호화 실패(키가 저장 당시와 다름)도 `501 SECRET_KEY_MISSING` 으로 응답(메시지로 구분).
- `PATCH /api/asset-assignments/{id}`, 배정/회수/이관/취소는 갱신된 **자산 상세**를 반환(화면 즉시 갱신용).
- 대시보드 "만료됨 N건" 클릭은 SW 탭 만료 필터로 이동(탭 전환 시 필터는 유지되지 않음).

## 스택

QUOTE-1/PURCHASE-1과 동일(FastAPI + Firestore, React 18 + TS + Vite). 신규 의존성은 비밀번호 암호화용
`cryptography`(Fernet) 하나 — `requirements.txt`에 명시 추가(구글 SDK 경유로 이미 설치돼 있을 수 있으나 직접 의존 명시).

## 백엔드 구조(예정)

| 파일 | 역할 |
|---|---|
| `config.py` | "자산관리(ASSET-1)" 섹션 신설: `ASSET_STATUS_*`(IDLE/IN_USE/DISPOSED/DELETED)+라벨, `ASSET_HIDDEN_STATUSES`(기본 목록·대시보드 제외, D47), `ASSET_SUBCATEGORIES`(유형별 소분류, P7), `ASSET_NO_SEQ_MAX=999`, `ASSET_EXPIRING_DAYS=30`, `ASSET_BULK_MAX=100`(P8), `ASSET_TZ="Asia/Seoul"`(D45), `ASSET_SECRET_KEY` 환경변수 이름. `ASSET_CATEGORIES`는 기존 것 재사용 |
| `models.py` | `Asset`, `AssetAssignment`, `AssetRenewal`, `Member` dataclass(`to_dict`/`from_doc`). `AssetUnit`에 `asset_link_kind`·`asset_nos` 추가(C3) |
| `schemas.py` | 입력/응답 스키마. **응답엔 `password_enc` 없음**, `has_password: bool`만. 입력의 `password`는 write-only — **없음/`null`/`""` = 변경 없음**(D42), 삭제는 별도 엔드포인트. 수정 스키마엔 `category` 필드 자체가 없음(D41). 등록 스키마 `quantity: int = 1`(1~`ASSET_BULK_MAX`). 배정/이관 입력은 `member_id`와 `shared_label` 중 정확히 하나 |
| `errors.py` | `ALREADY_IMPORTED`, `ASSET_NOT_IDLE`, `ASSET_IN_USE`, `ASSET_NOT_IN_USE`, `ASSET_DISPOSED`, `ASSET_DELETED`, `ASSET_IMPORTED`, `ASSET_HAS_HISTORY`, `MEMBER_INACTIVE`, `SECRET_KEY_MISSING` 추가(기존 `SEQ_EXHAUSTED`·`ALREADY_RETIRED`·`VALIDATION_ERROR` 재사용) |
| `deps.py` | `assert_can_view_asset(asset, user)` — `scope_group_code` 기준, 타 그룹 404. **`can_reveal_password(asset, user)` — 비밀번호 열람 판정 격리 지점(D16)**: 지금은 `role == SUPER_ADMIN`만 True. 팀원 로그인 도입 시 `asset.current_member_id == user.employee_no` 조건만 추가 |
| `services/asset_no.py`(신규) | `allocate_asset_nos_in(txn, category, purchase_date, count)` — `asset_seq/{cat}-{YY}`에서 연속 N개 확보. 기존 `services/asset_numbering.py`는 구매 유닛 채번 전용이라 건드리지 않음 |
| `services/asset_dates.py` | `today_kst()`(D45 — 날짜 기준 유일 계산처), 날짜 규칙 검사 순수 함수 `validate_period(...)`(D36) |
| `services/asset_bulk.py` | 수량 N 등록 시 자산 dict N개 생성, 금액 분할(P9 — 나머지 첫 자산) — 순수 함수 |
| `services/asset_secret.py` | `encrypt(plain)`/`decrypt(token)` — Fernet, 키는 `ASSET_SECRET_KEY` 환경변수. 키 없으면 `501 SECRET_KEY_MISSING` — 비밀번호가 포함된 요청은 **통째로 실패**(D43), 비밀번호 없는 요청은 키를 건드리지 않으므로 정상 |
| `services/asset_assignment.py` | 배정/회수/이관/이력수정/배정 취소 트랜잭션(data-model §8-3~8-6, §8-8) |
| `services/asset_registration.py` | 직접 등록(§8-2)·가져오기(§8-1)·가져오기 취소(§8-9), 구매 유닛 → 자산 매핑(C5) |
| `services/asset_renewal.py` | 갱신 트랜잭션(§8-10) |
| `services/asset_status.py` | 상태 가드: 폐기 자산 수정 불가, 사용 중 폐기 불가(P1) — `services/status.py` 스타일 순수 함수 |
| `services/asset_query.py`(확장) | `list_assets`, `renewals(from, to)` 묶음 집계 + KPI(`expired`/`d30`/`d90`), 사용자별 집계, 팀원 상세 `linkable` 판정(D37) |
| `services/members.py` | 팀원 수정 시 그룹·이름 전파(§8-7) |
| `services/export_excel.py`(확장) | `export_asset_list` — 비밀번호 컬럼 없음, 그룹관리자면 라이선스키 마스킹(presenter와 같은 함수) |
| `routers/assets.py` | 자산 CRUD·가져오기(+취소)·갱신·배정(+취소)·이력·비밀번호 열람/삭제·엑셀 |
| `routers/members.py` | 팀원 명단 |
| `routers/dashboard.py` | 갱신 캘린더/일정/KPI |
| `presenter.py` | 라벨, `expiry_badge`(EXPIRED/EXPIRING/null, `today_kst()` 기준), `read_only`(폐기) 파생, **`mask_license_key(value, user)` — 그룹관리자면 앞 4자리 + `****`(D38 격리 지점)** |

**권한**: 모든 쓰기 엔드포인트 `Depends(require_super_admin)`. 서버가 최종 방어선.

## API 엔드포인트(예정)

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| GET | `/api/assets` | 로그인(스코프) | 목록. `category`(필수), `subcategory`, `member_id`(`SHARED` = 공용), `group`, `status`, `expiry`(expired/expiring/ok), `year`, `name`, `valid_to`, `q`, `page` |
| GET | `/api/assets/export.xlsx` | 로그인(스코프) | 목록과 같은 필터 |
| GET | `/api/assets/importable` | 전체관리자 | 가져올/갱신에 연결할 수 있는 구매 유닛(`asset_link_kind` 없음·미폐기, `category` 필터) |
| POST | `/api/assets/import` | 전체관리자 | `{unit_no, quantity, ...폼값}` → 자산 N건(§8-1). 응답: 생성된 자산 목록 |
| POST | `/api/assets/import/cancel` | 전체관리자 | `{unit_no}` → 가져오기 취소(§8-9) |
| POST | `/api/assets/renew` | 전체관리자 | `{asset_nos, new_valid_to, new_valid_from?, unit_no?}` → 갱신(§8-10) |
| POST | `/api/assets` | 전체관리자 | 직접 등록 `{quantity, ...폼값}`(§8-2) |
| GET | `/api/assets/{asset_no}` | 로그인(스코프) | 상세 + 사용 이력 + 갱신 기록 |
| PATCH | `/api/assets/{asset_no}` | 전체관리자 | 수정(번호·유형·상태·현재사용자 제외). `password`에 값이 있을 때만 재암호화(D42) |
| DELETE | `/api/assets/{asset_no}/password` | 전체관리자 | 비밀번호 삭제(D42) |
| POST | `/api/assets/{asset_no}/dispose` | 전체관리자 | 폐기 |
| POST | `/api/assets/{asset_no}/delete` | 전체관리자 | 삭제 `{reason}`(필수, §8-9a, D47). 목록 `status=DELETED`는 전체관리자만(그 외 빈 목록) |
| POST | `/api/assets/{asset_no}/assign` | 전체관리자 | `{member_id \| shared_label, start_date, note}` |
| POST | `/api/assets/{asset_no}/return` | 전체관리자 | `{end_date, note}` |
| POST | `/api/assets/{asset_no}/transfer` | 전체관리자 | `{member_id \| shared_label, date, note}` |
| POST | `/api/assets/{asset_no}/assignment/cancel` | 전체관리자 | 현재 배정 취소(§8-8) |
| PATCH | `/api/asset-assignments/{id}` | 전체관리자 | 날짜·비고 수정 |
| POST | `/api/assets/{asset_no}/password/reveal` | `can_reveal_password` | `{action: REVEAL \| COPY}` → 평문 반환 + 열람 기록(§8-11). GET 아닌 POST(캐시·접근로그에 남지 않게), `Cache-Control: no-store` |
| GET | `/api/members` | 로그인(스코프) | 명단 + 유형별 사용 개수. 그룹관리자는 본인 그룹 팀원만(D46) |
| POST | `/api/members` | 전체관리자 | 등록 |
| PATCH | `/api/members/{employee_no}` | 전체관리자 | 이름·그룹·재직여부(그룹·이름 변경 시 §8-7, 퇴사 시 사용 중 자산 수 경고 반환) |
| GET | `/api/members/{employee_no}` | 로그인(스코프) | 현재 자산 + 과거 이력(각 줄에 `linkable` — D37) |
| GET | `/api/dashboard/renewals` | 로그인(스코프) | `from`,`to` → `[{date, name, category, count, asset_nos}]` + `kpi{expired, d30, d90}` |
| GET | `/api/meta` | 로그인 | 기존 응답에 `asset_subcategories`, `asset_statuses` 추가 |

**라우트 선언 순서**: `/api/assets/` 아래 고정 경로(`export.xlsx`, `importable`, `import`, `import/cancel`, `renew`)를 전부
`/{asset_no}` 계열보다 **먼저** 선언한다(QUOTE-1 `export.xlsx`와 같은 이유).

응답 에러 형식은 기존과 동일 `{"detail":{"code","message"}}`. 새 코드는 구현 시 `specs/QUOTE-1/tech/04-api-endpoints.md` 표에도 추가.

## 프론트엔드(예정)

| 경로 | 역할 |
|---|---|
| `design/Sidebar.tsx` | `CONTRACT_CHILDREN`에 자산관리 추가(C7) |
| `App.tsx` | `/assets`(→`/assets/sw` 리다이렉트), `/assets/:category`, `/assets/:category/new`, `/assets/:category/import`, `/assets/item/:assetNo`, `/assets/members`, `/assets/members/:employeeNo` |
| `pages/AssetList.tsx` | SW/HW/교육 탭 공용 목록(유형별 컬럼만 다름) + 필터 바 + 엑셀 + 같은 품명·종료일 선택 시 [갱신] 모달 |
| `pages/AssetForm.tsx` | 등록/수정 공용. 유형별 필드 섹션. 등록 모드엔 수량 칸, 수정 모드엔 유형 고정·비밀번호 빈 칸 = 유지 + [비밀번호 삭제]. 가져오기 모드는 구매 값 프리필 |
| `pages/AssetImport.tsx` | 가져올 구매 유닛 선택 |
| `pages/AssetDetail.tsx` | 상세 + 사용 이력 + 갱신 기록 + 배정(팀원/공용)/회수/이관/배정 취소 모달 + 가져오기 취소 + 비밀번호 보기/복사(`SuperAdminOnly`). 날짜 입력은 오늘(KST) 이후 선택 불가 |
| `pages/MemberList.tsx` / `MemberDetail.tsx` | 사용자별 탭 |
| `pages/Dashboard.tsx` | 갱신 캘린더·일정·D-30 KPI(+만료됨 건수)를 `/api/dashboard/renewals`로 교체, 나머지 2개 위젯 목업 유지(P6) |
| `api/assets.ts`, `api/members.ts`, `api/dashboard.ts` | 엔드포인트 래퍼 |

## 보안 — 비밀번호

- 암호화: Fernet(AES-128-CBC + HMAC). 키는 `ASSET_SECRET_KEY` 환경변수(로컬 `.env`, 배포는 Vercel 환경변수). **키를 코드·저장소에 두지 않음.** `.env.example`엔 생성 방법만 주석(`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
- 키 분실 = 저장된 비밀번호 복구 불가 → 배포 문서에 키 백업 절차 명시.
- `password_enc`는 목록·상세·검색·엑셀 어디에도 직렬화하지 않는다(스키마 레벨에서 필드 부재로 보장). 테스트로 검증.
- 열람 기록(D44): reveal마다 `password_reveal_logs`에 기록. 기록 실패 시 평문 반환 안 함.
- 확장(D16): 팀원 로그인 도입 시 `deps.can_reveal_password`만 수정.

## 테스트 계획

`backend/tests/test_assets.py`(에뮬레이터), `conftest.py` `_COLLECTIONS`에 `assets`/`asset_seq`/`asset_assignments`/`asset_renewals`/`password_reveal_logs`/`members` 추가.

- 채번: 유형·연도별 독립, 구매일 연도 사용, 구매일 없으면 KST 연도(UTC 12/31 15시 이후 = KST 새해 경계), 구매일 수정 후 번호 불변, 999 초과 409, 수량 N 연속 번호, N건 중 하나라도 999 초과 시 전체 409·0건 생성
- 가져오기: 값 매핑, 금액 분할(나머지 첫 자산, 합계 일치), `asset_units.asset_link_kind`/`asset_nos` 기록, 재가져오기 409, 폐기 유닛 409, 수량 0/101 400
- 가져오기 취소: N건 전체 폐기(`IMPORT_CANCELLED`)·유닛 연결 해제·재가져오기 가능, 이력 있는 자산 섞이면 409
- 갱신: 여러 자산 일괄 연장, 갱신 기록 생성, 유닛 `RENEWED` 표시 후 가져오기 목록에서 제외, 종료일 없는 자산·새 종료일 ≤ 기존 400, 종료일 서로 다른 묶음 400, 폐기 자산 409
- 배정/회수/이관: 상태·`current_*`·`scope_group_code` 동기화, 동시 배정 409, 퇴사자 409, 이관 원자성, 공용 배정(스코프 = 등록 그룹), 교육 공용 400
- 날짜 규칙(D36): 미래 날짜 400, 종료일 < 시작일 400, 기간 겹침 400, 이관일 < 사용 시작일 400, 활성 이력 종료일 수정 400 — 배정·회수·이관·이력수정 각각
- 배정 취소: 배정으로 생긴 건 → 미사용, 이관으로 생긴 건 → 이전 사용자 복구(이전 이력 `end_date` null), 미사용 자산 409
- 이력 수정: 수정자 기록, 사람 변경 불가
- 팀원 수정: 이름 변경 시 `current_member_name` 갱신·이력 스냅샷 유지
- 폐기: 사용 중 409, 폐기 후 수정/배정/갱신 409
- 수정: `category` 변경 불가, 비밀번호 빈 값 = 유지, DELETE로만 삭제
- 권한: 그룹관리자 쓰기 403, 타 그룹 상세 404, 스코프가 현재 사용자 그룹을 따라감, 팀원 그룹 변경 시 스코프 갱신, 명단은 본인 그룹만, 타 그룹 스코프 과거 이력 `linkable: false`, 라이선스키 마스킹(상세·목록·엑셀)·키 검색 무효
- 비밀번호: 목록/상세/엑셀 응답에 평문·암호문 부재, 전체관리자 reveal 성공 + 열람 기록 생성, 그룹관리자 403, 키 없음 501(비밀번호 포함 등록·수정은 전체 실패, 미포함은 성공)
- 대시보드: 같은 날·같은 품명 묶음, 폐기 제외, 스코프, `expired` 건수
- `tests/unit/`: 만료 배지 계산(KST), 소분류 검증, 번호 포맷, 금액 분할, 날짜 규칙 `validate_period`, 라이선스키 마스킹

## 구현 순서(제안)

1. COORDINATION 합의 → PURCHASE-1 문서 갱신
2. `members` + 채번(수량 N) + 직접 등록/조회 + `today_kst`(백엔드→프론트)
3. 배정(팀원/공용)/회수/이관/이력 + 날짜 규칙 + 배정 취소
4. 구매에서 가져오기(수량·금액 분할, 구매 목록 "자산 등록됨" 배지 포함) + 가져오기 취소
5. 갱신(일괄 연장, 갱신 구매 연결)
6. 비밀번호 암호화 + 열람 기록
7. 검색·엑셀(라이선스키 마스킹)
8. 대시보드 갱신 3종(+만료됨 KPI)
9. CLAUDE.md 범위·구조 표 갱신(C8)
