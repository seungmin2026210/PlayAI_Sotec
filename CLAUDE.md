# CLAUDE.md

SW 자산 견적서 관리 시스템 (QUOTE-1). 바탕화면 `기획서.md.md` v1.1 의 **1단계: 견적서 관리** 구현체.

## 이 저장소를 다룰 때 먼저 읽을 것

- 제품 스펙(사용자 대면 동작의 source of truth): `specs/QUOTE-1/PRODUCT.md` + `specs/QUOTE-1/product/01~10-*.md`
- 기술 스펙(아키텍처·구현): `specs/QUOTE-1/TECH.md` + `specs/QUOTE-1/tech/01~11-*.md`
- 결정 로그: `specs/QUOTE-1/DECISIONS.md`
- **배포**: Vercel(프론트+백엔드) + Firebase(Firestore, DB) 로 확정 — `backend/app` 은 Firestore 기준으로 마이그레이션 완료(SQLAlchemy/PostgreSQL 제거). 설계·경합 실측 결과는 `specs/QUOTE-1/tech/12-firestore-migration.md` 참고. 남은 것: Vercel 배포 파이프라인 자체 구성(§9), `firestore.indexes.json` 확정.
- **미정(❓) 항목 처리**: `specs/QUOTE-1/tech/10-provisional-decisions.md` — 기획서에서 협의가 안 끝난 항목을 "임시 결정 + 격리 위치"로 구현했다. 협의 결과가 나오면 그 표의 **격리 위치만** 수정한다.

스펙과 코드는 같은 PR 로 함께 진화시킨다. 동작/설계가 바뀌면 코드와 함께 해당 섹션 MD 도 갱신한다.

## 구조

```
backend/    FastAPI + google-cloud-firestore (DB: Firestore)
frontend/   React 18 + TypeScript + Vite
specs/QUOTE-1/   섹션별로 분할된 제품/기술 스펙
firebase.json, firestore.rules, firestore.indexes.json   Firestore 에뮬레이터/배포 설정
```

### backend/app

| 파일 | 역할 |
|---|---|
| `config.py` | **유일한 상수 정의처**: `ACCOUNTS`(계정), `GROUPS`, `COMPANY`(자사정보), `VAT_RATE`, `TRUNCATE_UNIT`, `SEQ_MAX`, 상태값, 견적서 export 양식 문구(`MGMT_NO_DISPLAY_PREFIX`, `QUOTE_*`), 직인(`SEAL_PATH`/`SEAL_MM`), Firestore 프로젝트/에뮬레이터 설정 |
| `models.py` | `Quote`/`QuoteItem` dataclass — Firestore 문서 ↔ 객체 변환(`to_dict`/`from_doc`). SQLAlchemy ORM 아님(12-firestore-migration.md) |
| `schemas.py` | Pydantic 전송 스키마 + 입력 유효성(음수/0, 필수). `id`는 문자열(Firestore 문서ID == mgmt_no) |
| `auth.py` | 로그인 시뮬레이션(범위 외). 토큰엔 username 만, role/group 은 매 요청 `ACCOUNTS` 재조회 |
| `database.py` | Firestore `Client` 싱글턴(`get_client`) + `run_transaction`(SDK 재시도 소진 시 대비한 애플리케이션 레벨 재시도 — 12-firestore-migration.md § 5) |
| `deps.py` | `get_db`, `get_current_user`, `require_super_admin`, `scope_group`, `assert_can_view` — **권한 판정 격리 지점(open-1/open-3)** |
| `errors.py` | `AppError(code, status, message)` + 코드 상수 |
| `presenter.py` | 모델 → 응답 스키마 변환(파생 필드: `group_name`, `status_label`, `read_only`, `company`) |
| `services/numbering.py` | 채번 `YY-그룹코드-순번`. `number_sequences/{year}-{group}` 문서를 Firestore 트랜잭션으로 +1(`allocate_in`은 호출자 트랜잭션에 이어붙임 — `routers/quotes.py:create_quote`가 채번+quote 생성을 원자적으로 묶는다), 999 초과 `409`, `retire_in`/`retire()` 결번 대장 |
| `services/query.py` | 목록 조회 — Firestore 등호 필터(그룹/상태/active) + 텍스트 부분일치·날짜range·페이지네이션은 애플리케이션 레벨(12-firestore-migration.md § 3) |
| `services/calculation.py` | 십만단위 절사 → 부가세 10% → 포함가. `format_won`(**open-6 표기 격리**) |
| `services/status.py` | 상태 전이표 `ALLOWED`, `guard_mutable`, `apply_transition`, `apply_purchase_lock`, `apply_edit_policy`(**open-10 수정정책 격리**). Firestore 전환 후에도 무변경(속성 mutation 만 하는 순수 함수) |
| `services/export_excel.py` | openpyxl: 개별 견적서(실제 견적서.jpg 양식) / 목록. APPROVED 는 대표자명 옆 직인 합성 |
| `services/export_pdf.py` | reportlab(순수 파이썬), 엑셀과 동일 양식. 한글 폰트는 `app/assets/fonts/`에 임베드해 시스템 의존성 없음(Vercel Serverless 등에서도 동작). import/렌더 실패 시 `501 PDF_UNAVAILABLE`, 서버는 계속 동작 |
| `routers/` | `auth.py`, `meta.py`, `quotes.py` — HTTP·권한·직렬화만, 로직은 services |

라우트 등록 순서 주의: `GET /api/quotes/export.xlsx` 는 `GET /api/quotes/{quote_id}` **보다 먼저** 선언해야 한다.

### frontend/src

| 경로 | 역할 |
|---|---|
| `api/client.ts` | fetch 래퍼, 토큰(localStorage), 401 로그아웃, `ApiError`(detail.code/message), `apiDownload`(blob) |
| `api/{auth,meta,quotes}.ts` | 엔드포인트별 함수 |
| `auth.tsx` | `AuthProvider` / `useAuth` |
| `hooks/useMeta.ts` | 그룹/상태/자사정보 (모듈 캐시) |
| `lib/money.ts` | `formatWon` — **open-6 표기 격리(프론트)** |
| `lib/vat.ts` | `computePreview` — 등록/수정 폼 실시간 계산(서버 규칙과 동일) |
| `components/RoleGate.tsx` | `SuperAdminOnly` — **open-3 역할별 화면 격리** |
| `components/{Toast,StatusBadge,ItemsEditor}.tsx` | |
| `design/` | Claude Design 프로젝트("로그인 및 대시보드 시스템 구축", kanban-design-system) 에서 이식한 대시보드 셸. `tokens.css`(디자인 토큰) · `Icon.tsx`(아이콘 10종) · `Sidebar.tsx`/`TopBar.tsx`/`AppShell.tsx`(사이드바+상단바 레이아웃, `/login` 제외 전체 라우트를 감쌈) |
| `pages/{Login,QuoteList,QuoteDetail,QuoteForm}.tsx` | |
| `pages/Dashboard.tsx` | 로그인 후 첫 화면(`/dashboard`). 통계·갱신 캘린더·예산 집행은 **범위 밖(향후 단계) 목업 데이터** — 실제 데이터가 연동된 화면은 계약관리 › 견적관리(`/quotes`, 기존 QuoteList) 뿐 |
| `pages/Placeholder.tsx` | 구매관리(`/purchase`)·계약관리(`/contract`) 등 아직 백엔드가 없는 사이드바 메뉴용 "준비 중" 화면 |

사이드바 메뉴 구조(계약관리 그룹 하위 견적관리/구매관리/계약관리)와 라우팅은 `design/Sidebar.tsx` 에서 관리 — 새 메뉴 추가 시 `CONTRACT_CHILDREN` 과 `App.tsx` 라우트를 함께 수정한다.

권한은 프론트 버튼 숨김이 아니라 **서버가 최종 방어선**. 새 쓰기 엔드포인트엔 `Depends(require_super_admin)` 필수.

## 명령

### DB (Firestore 에뮬레이터)
```bash
npx firebase-tools emulators:start --only firestore --project demo-quote   # :8090
```
Java 런타임 필요(`brew install openjdk`, macOS는 `/opt/homebrew/opt/openjdk/bin`을 PATH에 추가). 첫 실행은 에뮬레이터 jar 다운로드로 조금 느림. 포트/프로젝트는 `firebase.json` 참고.

### 백엔드
```bash
cd backend
py -3 -m venv .venv && .venv\Scripts\activate      # bash: source .venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env    # FIRESTORE_EMULATOR_HOST=127.0.0.1:8090 주석 해제(로컬 개발)
python seed.py                    # 데모 견적서 3건 (--reset 로 초기화)
uvicorn app.main:app --reload --port 8000          # /docs 에 API 문서
```
- PDF export: reportlab(순수 파이썬) + `app/assets/fonts/` 임베드 폰트라 OS/시스템 라이브러리 무관하게 동작(Vercel Serverless 포함). 실패 시에만 `501 PDF_UNAVAILABLE`.
- 임시 직인 재생성(문구/크기 변경 시): `py -3 ../scripts/make_seal.py`. 실제 직인은 `backend/app/assets/sotec-seal.png` 교체.
- 실제 Firestore(배포)에 붙일 땐 `.env`의 `FIRESTORE_EMULATOR_HOST` 를 지우고 `GOOGLE_APPLICATION_CREDENTIALS`(서비스 계정 키 경로)를 설정(12-firestore-migration.md § 9).

### 프론트엔드
```bash
cd frontend
npm install
npm run dev                       # :5173, /api → :8000 프록시
npm run typecheck                 # tsc --noEmit
npm run build                     # tsc && vite build
```

### 테스트
```bash
npx firebase-tools emulators:start --only firestore --project demo-quote &   # 미기동 시 DB 테스트는 skip
cd backend && .venv\Scripts\activate
pytest                            # 30 tests.
```
- `conftest.py` 가 `FIRESTORE_EMULATOR_HOST`(기본 `127.0.0.1:8090`) 로 접속, 매 테스트 전 `quotes`/`number_sequences`/`retired_numbers` 문서를 전부 지운다(TRUNCATE 대응). 에뮬레이터 미기동 시 연결 실패로 DB 테스트는 skip, `tests/unit/` 만 실행.
- 계산/채번 로직만 빠르게 확인: `python -c "from app.services.calculation import compute; ..."` (DB 불필요, 순수 함수)

## 규칙 / 관례

- **상수는 `backend/app/config.py` 한 곳.** 계정이 개별 ID 로 늘어나도 여기에만 추가한다(기획서 3.3, 계정 공유 금지).
- 미정 항목은 "빈칸"이 아니라 **눈에 띄고 바꾸기 쉬운 임시값**으로 두고, 격리 위치를 `tech/10-provisional-decisions.md` 에 기록한다.
- 금액은 **정수(원)** 로만 다룬다. 부동소수 금지. 절사는 총합계 기준 내림.
- 채번 연도는 발행일자가 아니라 **등록 시각 서버 연도**.
- 삭제는 물리 삭제가 아니라 soft delete(`active=False` + `deleted_at` 기록) + `retired_numbers` 기록. `number_sequences.last_seq` 는 되돌리지 않는다(결번 유지). `active`는 Firestore 목록 쿼리용, 존재/읽기전용 판정은 여전히 `deleted_at`(`services/status.py`, 무변경) 기준.
- 상태 `APPROVED`/`REJECTED`/`CANCELLED`(`services/status.py: TERMINAL_STATUSES`) 및 `purchase_locked` 는 읽기전용 — 수정/삭제/취소 불가. 승인은 되돌릴 수 없다(승인됨 → 취소 불가).
- 에러 응답은 항상 `{"detail": {"code": "...", "message": "..."}}`. 새 에러는 `errors.py` 코드 상수 + `tech/04-api-endpoints.md` 표에 추가.
- 커밋: 스펙 변경 + 코드 + 테스트를 하나의 일관된 PR 로.

## 범위 밖 (건드리지 말 것 — 향후 단계)

실제 인증 연동, SMTP 발송, 구매관리 실연동, 예산 관리, 갱신 캘린더, 자산 배정 이력, 감사로그 UI, 반려↔재제출 참조 필드. 발송·구매관리 잠금은 **자리표시만** 구현돼 있다.
