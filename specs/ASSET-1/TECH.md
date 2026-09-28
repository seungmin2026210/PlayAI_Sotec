# ASSET-1 · 기술 스펙 (Tech Spec)

> 사용자 대면 동작: [`PRODUCT.md`](./PRODUCT.md). 데이터 모델: [`tech/01-data-model.md`](./tech/01-data-model.md).
> 결정 로그: [`DECISIONS.md`](./DECISIONS.md). **구매관리 조율: [`COORDINATION.md`](./COORDINATION.md) — 합의 전 구현 착수 금지.**
>
> 상태: **설계 완료, 미구현** (2026-09-28).

## 스택

QUOTE-1/PURCHASE-1과 동일(FastAPI + Firestore, React 18 + TS + Vite). 신규 의존성은 비밀번호 암호화용
`cryptography`(Fernet) 하나 — `requirements.txt`에 명시 추가(구글 SDK 경유로 이미 설치돼 있을 수 있으나 직접 의존 명시).

## 백엔드 구조(예정)

| 파일 | 역할 |
|---|---|
| `config.py` | "자산관리(ASSET-1)" 섹션 신설: `ASSET_STATUS_*`(IDLE/IN_USE/DISPOSED)+라벨, `ASSET_SUBCATEGORIES`(유형별 소분류, P7), `ASSET_NO_SEQ_MAX=999`, `ASSET_EXPIRING_DAYS=30`, `ASSET_SECRET_KEY` 환경변수 이름. `ASSET_CATEGORIES`는 기존 것 재사용 |
| `models.py` | `Asset`, `AssetAssignment`, `Member` dataclass(`to_dict`/`from_doc`). `AssetUnit`에 `asset_no` 추가(C3) |
| `schemas.py` | 입력/응답 스키마. **응답엔 `password_enc` 없음**, `has_password: bool`만. 입력의 `password`는 write-only |
| `errors.py` | `ALREADY_IMPORTED`, `ASSET_NOT_IDLE`, `ASSET_IN_USE`, `ASSET_DISPOSED`, `MEMBER_INACTIVE`, `SECRET_KEY_MISSING` 추가(기존 `SEQ_EXHAUSTED`·`ALREADY_RETIRED`·`VALIDATION_ERROR` 재사용) |
| `deps.py` | `assert_can_view_asset(asset, user)` — `scope_group_code` 기준, 타 그룹 404. **`can_reveal_password(asset, user)` — 비밀번호 열람 판정 격리 지점(D16)**: 지금은 `role == SUPER_ADMIN`만 True. 팀원 로그인 도입 시 `asset.current_member_id == user.employee_no` 조건만 추가 |
| `services/asset_numbering.py`(확장) 또는 `services/asset_no.py` | `allocate_asset_no_in(txn, category, purchase_date)` — `asset_seq/{cat}-{YY}` |
| `services/asset_secret.py` | `encrypt(plain)`/`decrypt(token)` — Fernet, 키는 `ASSET_SECRET_KEY` 환경변수. 키 없으면 `501 SECRET_KEY_MISSING`(PDF_UNAVAILABLE처럼 해당 기능만 실패) |
| `services/asset_assignment.py` | 배정/회수/이관/이력수정 트랜잭션(data-model §6-3~6-6) |
| `services/asset_status.py` | 상태 가드: 폐기 자산 수정 불가, 사용 중 폐기 불가(P1) — `services/status.py` 스타일 순수 함수 |
| `services/asset_query.py`(확장) | `list_assets`, `renewals(from, to)` 묶음 집계, 사용자별 집계 |
| `services/export_excel.py`(확장) | `export_asset_list` — 비밀번호 컬럼 없음 |
| `routers/assets.py` | 자산 CRUD·가져오기·배정·이력·비밀번호 열람·엑셀 |
| `routers/members.py` | 팀원 명단 |
| `routers/dashboard.py` | 갱신 캘린더/일정/KPI |
| `presenter.py` | 라벨, `expiry_badge`(EXPIRED/EXPIRING/null), `read_only`(폐기) 파생 |

**권한**: 모든 쓰기 엔드포인트 `Depends(require_super_admin)`. 서버가 최종 방어선.

## API 엔드포인트(예정)

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| GET | `/api/assets` | 로그인(스코프) | 목록. `category`(필수), `subcategory`, `member_id`, `group`, `status`, `expiry`(expired/expiring/ok), `year`, `q`, `page` |
| GET | `/api/assets/export.xlsx` | 로그인(스코프) | 목록과 같은 필터. **`/{asset_no}`보다 먼저 선언** |
| GET | `/api/assets/importable` | 전체관리자 | 가져올 수 있는 구매 유닛(`asset_no` 없음·미폐기, `category` 필터) |
| POST | `/api/assets/import` | 전체관리자 | `{unit_no, ...폼값}` → 가져오기(§6-1) |
| POST | `/api/assets` | 전체관리자 | 직접 등록 |
| GET | `/api/assets/{asset_no}` | 로그인(스코프) | 상세 + 사용 이력 |
| PATCH | `/api/assets/{asset_no}` | 전체관리자 | 수정(번호·상태·현재사용자 제외). `password` 주면 재암호화, `""`면 삭제 |
| POST | `/api/assets/{asset_no}/dispose` | 전체관리자 | 폐기 |
| POST | `/api/assets/{asset_no}/assign` | 전체관리자 | `{member_id, start_date, note}` |
| POST | `/api/assets/{asset_no}/return` | 전체관리자 | `{end_date, note}` |
| POST | `/api/assets/{asset_no}/transfer` | 전체관리자 | `{member_id, date, note}` |
| PATCH | `/api/asset-assignments/{id}` | 전체관리자 | 날짜·비고 수정 |
| POST | `/api/assets/{asset_no}/password/reveal` | `can_reveal_password` | 평문 반환. GET 아닌 POST(캐시·접근로그에 남지 않게), `Cache-Control: no-store` |
| GET | `/api/members` | 로그인(스코프) | 명단 + 유형별 사용 개수 |
| POST | `/api/members` | 전체관리자 | 등록 |
| PATCH | `/api/members/{employee_no}` | 전체관리자 | 이름·그룹·재직여부(그룹 변경 시 §6-7, 퇴사 시 사용 중 자산 수 경고 반환) |
| GET | `/api/members/{employee_no}` | 로그인(스코프) | 현재 자산 + 과거 이력 |
| GET | `/api/dashboard/renewals` | 로그인(스코프) | `from`,`to` → `[{date, name, category, count, asset_nos}]` + `kpi{d30, d90}` |
| GET | `/api/meta` | 로그인 | 기존 응답에 `asset_subcategories`, `asset_statuses` 추가 |

응답 에러 형식은 기존과 동일 `{"detail":{"code","message"}}`. 새 코드는 구현 시 `specs/QUOTE-1/tech/04-api-endpoints.md` 표에도 추가.

## 프론트엔드(예정)

| 경로 | 역할 |
|---|---|
| `design/Sidebar.tsx` | `CONTRACT_CHILDREN`에 자산관리 추가(C7) |
| `App.tsx` | `/assets`(→`/assets/sw` 리다이렉트), `/assets/:category`, `/assets/:category/new`, `/assets/:category/import`, `/assets/item/:assetNo`, `/assets/members`, `/assets/members/:employeeNo` |
| `pages/AssetList.tsx` | SW/HW/교육 탭 공용 목록(유형별 컬럼만 다름) + 필터 바 + 엑셀 |
| `pages/AssetForm.tsx` | 등록/수정 공용. 유형별 필드 섹션. 가져오기 모드는 구매 값 프리필 |
| `pages/AssetImport.tsx` | 가져올 구매 유닛 선택 |
| `pages/AssetDetail.tsx` | 상세 + 사용 이력 + 배정/회수/이관 모달 + 비밀번호 보기/복사(`SuperAdminOnly`) |
| `pages/MemberList.tsx` / `MemberDetail.tsx` | 사용자별 탭 |
| `pages/Dashboard.tsx` | 갱신 캘린더·일정·D-30 KPI를 `/api/dashboard/renewals`로 교체, 나머지 2개 위젯 목업 유지(P6) |
| `api/assets.ts`, `api/members.ts`, `api/dashboard.ts` | 엔드포인트 래퍼 |

## 보안 — 비밀번호

- 암호화: Fernet(AES-128-CBC + HMAC). 키는 `ASSET_SECRET_KEY` 환경변수(로컬 `.env`, 배포는 Vercel 환경변수). **키를 코드·저장소에 두지 않음.** `.env.example`엔 생성 방법만 주석(`python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`).
- 키 분실 = 저장된 비밀번호 복구 불가 → 배포 문서에 키 백업 절차 명시.
- `password_enc`는 목록·상세·검색·엑셀 어디에도 직렬화하지 않는다(스키마 레벨에서 필드 부재로 보장). 테스트로 검증.
- 확장(D16): 팀원 로그인 도입 시 `deps.can_reveal_password`만 수정.

## 테스트 계획

`backend/tests/test_assets.py`(에뮬레이터), `conftest.py` `_COLLECTIONS`에 `assets`/`asset_seq`/`asset_assignments`/`members` 추가.

- 채번: 유형·연도별 독립, 구매일 연도 사용, 구매일 없으면 서버 연도, 구매일 수정 후 번호 불변, 999 초과 409
- 가져오기: 값 매핑, `asset_units.asset_no` 기록, 재가져오기 409, 폐기 유닛 409
- 배정/회수/이관: 상태·`current_*`·`scope_group_code` 동기화, 동시 배정 409, 퇴사자 409, 이관 원자성
- 이력 수정: 기간 역전·겹침 400, 수정자 기록, 사람 변경 불가
- 폐기: 사용 중 409, 폐기 후 수정/배정 409
- 권한: 그룹관리자 쓰기 403, 타 그룹 상세 404, 스코프가 현재 사용자 그룹을 따라감, 팀원 그룹 변경 시 스코프 갱신
- 비밀번호: 목록/상세/엑셀 응답에 평문·암호문 부재, 전체관리자 reveal 성공, 그룹관리자 403, 키 없음 501
- 대시보드: 같은 날·같은 품명 묶음, 폐기 제외, 스코프
- `tests/unit/`: 만료 배지 계산, 소분류 검증, 번호 포맷

## 구현 순서(제안)

1. COORDINATION 합의 → PURCHASE-1 문서 갱신
2. `members` + 채번 + 직접 등록/조회(백엔드→프론트)
3. 배정/회수/이관/이력
4. 구매에서 가져오기(구매 목록 "자산 등록됨" 배지 포함)
5. 비밀번호 암호화
6. 검색·엑셀
7. 대시보드 갱신 3종
8. CLAUDE.md 범위·구조 표 갱신(C8)
