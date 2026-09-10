# 12. Firestore 마이그레이션 설계 (Vercel + Firebase 배포)

배경/결정: [`DECISIONS.md` § 배포 아키텍처 전환](../DECISIONS.md). 배포를 **Vercel(프론트+백엔드) + Firebase(Firestore, DB)** 로 확정하면서, PostgreSQL + SQLAlchemy 2 를 전제로 설계됐던 `backend/app` 전반을 다시 짰다. **마이그레이션 구현 완료**(§10 실행 순서 1~8, pytest 30개 전부 통과 · 에뮬레이터로 동시성 실측 완료) — 남은 건 §10의 9~10(Vercel 배포 파이프라인 자체, 실제 Firestore 프로젝트 배포)뿐이다.

이 문서에 없는 세부 구현 방식이 코드 작업 중 바뀌면, 이 문서도 같은 PR 로 갱신한다(CLAUDE.md 원칙).

## 0. 왜 "설정 변경"이 아닌가

PostgreSQL(관계형) → Firestore(문서형)는 저장 모델의 패러다임이 다르다. 특히 이 프로젝트가 의존하는 세 가지가 Firestore 에 기본 제공되지 않는다:

| PostgreSQL 이 공짜로 주는 것 | Firestore 대응 |
|---|---|
| `SELECT ... FOR UPDATE` 행 잠금 | 트랜잭션(낙관적, 충돌 시 자동 재시도)으로 재구현 필요 |
| `UNIQUE` 제약(`mgmt_no`) | 없음 — 문서 ID 로 구조적으로 보장하거나 트랜잭션으로 보장 |
| `WHERE col ILIKE '%x%'` 부분 일치 검색 | 없음 — 별도 전략 필요(§3) |
| `COUNT(*) WHERE ...` | `count()` 애그리게이션 쿼리로 가능하나 복합 필터 제약 있음 |
| 스키마 마이그레이션(Alembic) | 없음(스키마리스) — 대신 복합 인덱스를 `firestore.indexes.json` 로 관리 |

## 1. 컬렉션 스키마

### `quotes/{mgmtNo}`

**문서 ID = `mgmt_no` 그대로 사용** (예: `26-B-008`). 이유:
- 채번 트랜잭션이 끝나는 시점에 이미 유일성이 보장된 값이라, 별도 auto-id 를 또 만들 필요가 없다.
- `mgmt_no` 로 직접 `get()` 가능(조회 1회, 인덱스 불필요).
- **Breaking change**: 지금은 `id`가 `bigserial`(숫자)이고 프론트가 `Number(id)`로 다룬다(`QuoteDetail.tsx`, `QuoteForm.tsx`). Firestore 전환 후 `id`는 **문자열**(`"26-B-008"`)이 된다. §7 영향 범위에 정리.

```jsonc
{
  // mgmt_no 는 문서 ID 와 동일 값을 필드로도 중복 저장(쿼리·export 편의, 값 자체는 문서ID가 정본)
  "mgmt_no": "26-B-008",
  "seq_year": 2026,
  "group_code": "B",
  "seq_no": 8,

  "title": "...",
  "issue_date": "2026-09-10",        // string(YYYY-MM-DD). Timestamp 대신 문자열로 저장(§3 날짜 필터 참고)
  "issuer_name": "...",

  "customer_name": "...",
  "customer_contact_name": "...",     // null 허용
  "customer_contact_phone": "...",    // null 허용

  "vat_included": true,
  "supply_amount": 12000000,
  "vat_amount": 1200000,
  "total_with_vat": 13200000,
  "items_raw_total": 12345678,

  "items": [                          // 서브컬렉션 아닌 배열 필드(§2)
    { "line_no": 1, "name": "...", "qty": 1, "unit_price": 5000000, "line_amount": 5000000 }
  ],

  "status": "SUBMITTED",
  "reject_reason": null,
  "purchase_locked": false,
  "active": true,                     // soft delete 플래그(§4) — deleted_at 대신 이걸로 쿼리

  "created_by": "Admin",
  "created_at": <Timestamp>,
  "updated_at": <Timestamp|null>,
  "approved_at": <Timestamp|null>,
  "rejected_at": <Timestamp|null>,
  "cancelled_at": <Timestamp|null>,
  "locked_at": <Timestamp|null>,
  "deleted_at": <Timestamp|null>      // 기록은 유지(감사용), 쿼리 필터는 active 사용
}
```

### `number_sequences/{year}-{group_code}`

```jsonc
{ "seq_year": 2026, "group_code": "B", "last_seq": 8 }
```

문서 ID를 `f"{year}-{group_code}"`로 두면 채번 트랜잭션이 `get()` 1회로 바로 접근(쿼리 불필요).

### `retired_numbers/{mgmt_no}`

```jsonc
{ "mgmt_no": "26-B-007", "seq_year": 2026, "group_code": "B", "seq_no": 7,
  "retired_at": <Timestamp>, "retired_by": "Admin", "reason": "DELETED" }
```

문서 ID = `mgmt_no` (중복 결번 방지도 구조적으로 겸함).

## 2. `quote_items` — 서브컬렉션이 아니라 배열 필드로

현재 `selectinload(Quote.items)`로 항상 quote 와 items 를 함께 읽는다. Firestore 서브컬렉션으로 만들면 상세 조회마다 쿼리가 1회 더 필요해진다. 항목 수는 소량(견적서 1건당 몇~수십 줄)이고 문서 크기 한도(1MiB)에 전혀 안 걸리므로, **quote 문서 안의 `items` 배열 필드**로 저장한다.

- 수정(PUT)의 "`items.clear()` 후 재생성" 패턴은 배열 전체를 새 배열로 덮어쓰는 것과 1:1 대응 — 로직 변경 없음.
- 항목 추가/삭제에 트랜잭션이 필요 없다(quote 문서 자체를 통째로 갱신하는 단일 쓰기).

## 3. 목록 조회(`GET /api/quotes`) — 필터·검색·페이지네이션

현재 `_apply_filters`는 `mgmt_no`/`title`/`issuer_name` 에 **`ILIKE '%x%'`**(부분 일치)를 쓴다. Firestore 쿼리는 부분 문자열 매치, OR, 여러 필드의 임의 조합 range 필터를 지원하지 않는다. 이 프로젝트 규모(내부 도구, 그룹 5개, 견적서 수 — 데모 기준 3건, 실사용도 수백~수천 건대로 추정)를 고려해 아래처럼 **단순하게** 간다. 대용량 전문검색이 필요해지면 Algolia/Typesense 같은 외부 검색 인덱스를 얹는 게 정석이지만, 지금 범위에서는 과설계다.

**결정(임시, 실사용 트래픽 보고 재검토 — 이 문단 자체가 격리 지점):**

1. **Firestore 쪽에서는 인덱스 친화적인 필터만**: `active == true`, (있으면) `group_code == ...`, (있으면) `status == ...`. 그룹관리자 스코프(`apply_scope`)도 `group_code` 등호 필터로 자연스럽게 표현됨.
2. **나머지(부분 일치 텍스트: `mgmt_no`/`title`/`issuer_name`, 날짜 range)는 애플리케이션 코드에서 필터링**: 위 1번 쿼리로 후보 문서를 가져온 뒤 Python 에서 `in`/`startswith`/날짜 비교로 걸러낸다.
3. **정렬은 `created_at desc` 로 Firestore 쿼리 자체에서 수행**(인덱스 1개로 충분, `orderBy` + 위 등호 필터 조합).
4. **페이지네이션**: 1차는 `page`/`size` 계약을 유지하기 위해 **애플리케이션 레벨 offset**(1번 쿼리로 스코프 내 전체를 가져와 Python 에서 텍스트 필터 → slice)로 구현. 이 방식은 스코프 내 문서 수가 늘어나면 읽기 비용이 커진다(문서 1건 = Firestore 과금 1 read). 데이터 규모가 커지면 `startAfter` 커서 기반으로 바꾸고 API 계약을 `page` 대신 `cursor` 로 바꿔야 한다 — **이 임계점을 넘는지 운영 중 모니터링 필요**(예: 그룹당 문서가 수천 건을 넘어가면 재검토).
5. **`total`(전체 건수)**: 구현은 텍스트 필터 유무와 무관하게 항상 Python `len()`(스코프 내 후보를 이미 다 읽은 뒤라 추가 비용 없음)으로 계산 — `count()` 애그리게이션은 텍스트 필터가 없을 때만 쓸 수 있는 최적화라 분기 복잡도 대비 이득이 크지 않아 1차 구현에서는 생략(YAGNI). 그룹당 문서가 많아져 "전체를 다 읽는" 비용 자체가 문제가 되면(§4 임계점과 동일 트리거) 그때 도입.

```python
# services/query.py (신규) 개념 스케치
def list_quotes(client, *, scope_group=None, status=None, mgmt_no=None, title=None,
                 issuer_name=None, issue_date_from=None, issue_date_to=None,
                 page=1, size=20):
    q = client.collection("quotes").where("active", "==", True)
    if scope_group:
        q = q.where("group_code", "==", scope_group)
    if status:
        q = q.where("status", "==", status)
    q = q.order_by("created_at", direction="DESCENDING")

    docs = [d.to_dict() | {"id": d.id} for d in q.stream()]  # 스코프 내 전체
    if mgmt_no:
        docs = [d for d in docs if mgmt_no in d["mgmt_no"]]
    if title:
        docs = [d for d in docs if title in d["title"]]
    if issuer_name:
        docs = [d for d in docs if issuer_name in d["issuer_name"]]
    if issue_date_from:
        docs = [d for d in docs if d["issue_date"] >= issue_date_from.isoformat()]
    if issue_date_to:
        docs = [d for d in docs if d["issue_date"] <= issue_date_to.isoformat()]

    total = len(docs)
    start = (page - 1) * size
    return total, docs[start:start + size]
```

## 4. Soft delete — `deleted_at` 대신 `active` 로 쿼리

`deleted_at IS NULL` 동등 쿼리는 Firestore 에서도 가능(`where("deleted_at", "==", None)`)하지만, 다른 등호 필터와 묶일 때 복합 인덱스에 null 필터가 끼면 다루기 번거롭다. 그래서:
- 쓰기: 삭제 시 `active=False`, `deleted_at=now()` 둘 다 기록.
- 읽기: 모든 목록/상세 쿼리는 `active == True` 로 필터(상세 단건 `get()`은 문서를 읽은 뒤 `if not active: 404`로 앱 레벨 처리 — 어차피 지금도 `assert_exists`가 앱 레벨).
- `deleted_at`은 감사/디버깅용 타임스탬프로만 남긴다.

## 5. 채번 동시성 — Firestore 트랜잭션

```python
# services/numbering.py 재작성 방향
from google.cloud import firestore

def allocate(client: firestore.Client, group_code: str) -> Allocation:
    year = datetime.now(timezone.utc).year
    seq_ref = client.collection("number_sequences").document(f"{year}-{group_code}")

    @firestore.transactional
    def _txn(transaction):
        snap = seq_ref.get(transaction=transaction)
        last_seq = snap.get("last_seq") if snap.exists else 0
        if last_seq >= SEQ_MAX:
            raise AppError(SEQ_EXHAUSTED, 409, "...999건을 초과했습니다...")
        next_seq = last_seq + 1
        transaction.set(seq_ref, {"seq_year": year, "group_code": group_code, "last_seq": next_seq})
        return next_seq

    seq_no = _txn(client.transaction())
    mgmt_no = f"{year % 100:02d}-{group_code}-{seq_no:03d}"
    return Allocation(year=year, group_code=group_code, seq_no=seq_no, mgmt_no=mgmt_no)
```

- **등록(`create_quote`)은 채번 트랜잭션과 quote 문서 생성을 같은 Firestore 트랜잭션에 묶는다** — `transaction.set(quotes_ref.document(mgmt_no), {...}, )`. Postgres 에서 "채번 + insert 같은 트랜잭션"이던 것과 동일한 원자성.
- 문서 ID 가 `mgmt_no` 이므로, 같은 번호로 두 번 쓰기가 동시에 들어올 가능성 자체가 없다(트랜잭션이 `number_sequences` 문서를 먼저 읽고 잠그는 방식으로 직렬화됨). Postgres 의 `UNIQUE` 최종 방어선 역할은 "문서 ID 가 곧 유일성"으로 대체.
- Firestore 클라이언트 라이브러리는 트랜잭션 충돌(동시 쓰기 경합) 시 **자동 재시도**(기본 5회, `max_attempts`로 조절 가능)한다 — `SELECT FOR UPDATE`가 경합 시 대기하던 것과 결과적으로 동등한 안전성.
- 999 초과 시 `409 SEQ_EXHAUSTED` 그대로 유지.

**실측(에뮬레이터, 구현 완료 후 검증) — 이 절이 처음 예상보다 중요했다.** 같은 `number_sequences`
문서에 스레드 4~10개가 진짜로 동시에 채번을 시도하면, `max_attempts=15`로 올려도 SDK 자체
재시도만으론 부족해 일부 요청이 `Aborted`("Transaction lock timeout")로 완전히 실패하는 걸
확인했다(중복/결번 없이 "실패"로 끝남 — 안전하지만 사용자에게 에러가 그대로 노출됨). 그래서
`database.run_transaction()`에 **트랜잭션 재시도 위에 한 겹 더** 애플리케이션 레벨 재시도(지수
백오프+지터, 기본 5회)를 추가했고, 이후 2~15 스레드 동시 채번을 반복 실측해 전부 중복·결번·실패
없이 통과했다(15스레드 기준 수십 초 — 에뮬레이터 기준이라 실제 Firestore 프로덕션에서는 더 빠를
가능성이 높지만 별도 재검증 필요). `allocate()`/`retire()`(단독 트랜잭션)와 `create_quote`/
`delete_quote`(라우터 자체 트랜잭션) 양쪽 다 이 헬퍼를 거친다.

### 결번(삭제)

```python
def retire(client, *, mgmt_no, seq_year, group_code, seq_no, retired_by):
    client.collection("retired_numbers").document(mgmt_no).set({...})
    # number_sequences.last_seq 는 되돌리지 않음(기존 규칙 그대로)
```

## 6. 계층별 영향 범위 (완료 상태)

| 파일 | 영향 | 비고 |
|---|---|---|
| `services/calculation.py` | 변경 없음 | 순수 함수, DB 비의존 |
| `services/status.py` | 변경 없음 | 속성 mutation 만 하는 순수 함수 — ORM 객체든 dataclass 든 무관 |
| `services/numbering.py` | 전면 재작성 완료 | §5. `allocate_in`/`retire_in`(트랜잭션 이어붙이기) + `allocate`/`retire`(단독) |
| `services/query.py` | 신규 | §3 목록 쿼리 헬퍼 |
| `models.py` | 전면 재작성 완료 | SQLAlchemy 제거. `Quote`/`QuoteItem` dataclass + `to_dict`/`from_doc` |
| `database.py` | 전면 재작성 완료 | Firestore `Client` 싱글턴(`get_client`) + `run_transaction`(재시도 헬퍼, §5 실측 이후 추가) |
| `deps.py` | 재작성 완료 | `get_db`(Firestore client 반환), `apply_scope`→`scope_group`(그룹 문자열만 반환), `assert_can_view` 무변경 |
| `routers/quotes.py` | 전면 재작성 완료 | `db.execute(select(...))` 전부 §3 쿼리 헬퍼로 교체. `create_quote`/`delete_quote`는 자체 Firestore 트랜잭션(`run_transaction`)으로 채번/결번을 묶음 |
| `schemas.py` | 수정 완료 | `id: int` → `id: str` (`QuoteRead`, `QuoteListItem`) |
| `presenter.py` | 변경 없음 | `id=q.id` 그대로(타입만 문자열로 흐름) |
| `services/export_excel.py` / `export_pdf.py` | 변경 없음 | `Quote` 객체 속성만 읽음(ORM 비의존적으로 이미 작성돼 있었음) |
| `auth.py` / `config.py` (ACCOUNTS) | 변경 없음(Firestore 설정만 추가) | 이 마이그레이션은 DB 교체만. 로그인 시뮬레이션·Firebase Auth 연동은 **범위 밖** |
| `alembic/`, `alembic.ini` | 삭제 완료 | 스키마리스. 대신 `firestore.indexes.json`(§9) |
| `docker-compose.yml`(PostgreSQL), `scripts/init-db.sql` | 삭제 완료 | 로컬 DB는 `npx firebase-tools emulators:start --only firestore` |
| `tests/conftest.py` | 재작성 완료 | 에뮬레이터 접속 + 매 테스트 전 컬렉션 문서 전삭제(TRUNCATE 대응). pytest 30개 전부 통과 |
| `tests/test_numbering.py` | 재작성 완료 | `SessionLocal()` → `db`(Firestore client) 픽스처 |
| `seed.py` | 재작성 완료 | Firestore 트랜잭션으로 데모 3건 생성, 실행 확인됨 |
| `frontend/src/api/quotes.ts`, `types.ts`, `QuoteDetail.tsx`, `QuoteForm.tsx` | 수정 완료 | §7. `npm run typecheck` 통과 |

## 7. 프론트엔드 영향 (Breaking change)

`quote_id`가 숫자(`bigserial`) → 문자열(`mgmt_no`)로 바뀐다.

| 파일 | 변경 |
|---|---|
| `api/quotes.ts` | `id: number` 파라미터 8곳 → `id: string` |
| `pages/QuoteDetail.tsx` | `const quoteId = Number(id)` → `const quoteId = id` (라우트 파라미터 그대로 문자열 사용) |
| `pages/QuoteForm.tsx` | `getQuote(Number(id))`, `updateQuote(Number(id), ...)` → `Number()` 제거 |
| 라우팅(`App.tsx`) | 경로 패턴(`/quotes/:id`) 자체는 변경 없음(문자열 파라미터는 원래도 문자열) |

## 8. 로컬 개발 / 테스트

- **Firestore 에뮬레이터**로 `docker-compose.yml`의 PostgreSQL 대체:
  ```bash
  firebase emulators:start --only firestore   # FIRESTORE_EMULATOR_HOST=localhost:8080
  ```
- `config.py`: `database_url`/`database_url_test` 제거, `firebase_project_id` + (배포용) 서비스 계정 인증 정보로 교체. 로컬은 에뮬레이터 사용 시 인증 정보 불필요(`FIRESTORE_EMULATOR_HOST` 만 있으면 됨).
- `tests/conftest.py`: DB `TRUNCATE ... RESTART IDENTITY` 대응 없음 — 매 테스트 전 관련 컬렉션의 문서를 모두 삭제하는 헬퍼(재귀 삭제, 에뮬레이터는 `http://localhost:8080/emulator/v1/projects/{id}/databases/(default)/documents` DELETE 로 한 번에 초기화 가능)로 교체.
- `seed.py`: 데모 견적서 3건을 Firestore 문서로 직접 `set()`.

## 9. 배포 / 인증 정보 관리

- 백엔드(Vercel Serverless Functions 또는 별도 컨테이너)에서 Firestore 접근은 **`google-cloud-firestore` + 서비스 계정**(Firebase Admin 자격 증명)으로 수행. Firebase Auth 는 쓰지 않음(§6, 범위 밖).
- 서비스 계정 키 JSON은 파일로 배포 이미지에 넣지 않고 **Vercel 환경변수**(`GOOGLE_APPLICATION_CREDENTIALS_JSON` 등)에 통째로 넣고, 프로세스 시작 시 임시 파일로 풀거나 `google.oauth2.service_account.Credentials.from_service_account_info()`로 메모리에서 바로 생성.
- **복합 인덱스**: `group_code == / status == / active == + orderBy(created_at)` 조합을 `firestore.indexes.json` 에 정의하고 `firebase deploy --only firestore:indexes` 로 배포. 어떤 조합이 실제로 필요한지는 §3 쿼리 헬퍼 구현 확정 후 Firestore 콘솔의 "인덱스 필요" 에러를 보고 채워도 무방(Firestore 가 누락된 인덱스를 에러 메시지에 콘솔 링크로 알려줌).

## 10. 실행 순서 — 진행 상태

1. ✅ `models.py` → dataclass 로 교체 (Quote/QuoteItem, ORM 의존 제거).
2. ✅ `database.py` → Firestore client 싱글턴 (+ `run_transaction` 재시도 헬퍼, §5 실측 결과 반영).
3. ✅ `services/numbering.py` 재작성 + 단위 테스트. 동시성은 단위 테스트(pytest, 순차)뿐 아니라 에뮬레이터로 2~15 스레드 실측까지 완료(§5).
4. ✅ `deps.py`(`get_db`, `scope_group`) 재작성.
5. ✅ `routers/quotes.py` 전체 엔드포인트 전환 + `services/query.py` 신규. TestClient 로 로그인→생성→목록→상세→수정→승인→엑셀/PDF export→삭제 전체 플로우, 그룹관리자 스코프/403/404, soft delete 후속 동작까지 수동 통합검증 완료.
6. ✅ `schemas.py`/`presenter.py` id 타입 수정.
7. ✅ 프론트 §7 반영, `npm run typecheck` 통과.
8. ✅ `tests/conftest.py` + `seed.py` 교체, `pytest` 30개 전부 통과. `seed.py --reset` 실행 확인.
9. ✅ `alembic/`, `docker-compose.yml`(Postgres), `scripts/init-db.sql` 제거, `CLAUDE.md` 명령 섹션 갱신.
10. ⬜ **미완료**: `firestore.indexes.json`(초안은 작성됨 — §3 쿼리 조합 4가지 기준. 실제 Firestore 프로젝트에 `firebase deploy --only firestore:indexes` 로 배포 안 해봄), Vercel 배포 파이프라인(백엔드를 Vercel Functions로 올릴지/Cloud Run 등 별도 컨테이너로 올릴지 재확인 필요 — `backend/Dockerfile`은 컨테이너 호스팅 전제라 Vercel Functions 라면 안 씀), 서비스 계정/환경변수 실제 설정.

## 11. 남는 미확정 항목

| 항목 | 임시 결정 | 재검토 트리거 |
|---|---|---|
| 목록 페이지네이션 방식(§3-4) | 애플리케이션 offset | 그룹당 문서 수천 건 이상 |
| 텍스트 부분검색(§3-2) | 애플리케이션 레벨 `in` 필터 | 검색 응답 지연 체감 시 |
| `total` 산출(§3-5) | 항상 Python `len()` | 그룹당 문서 많아져 "전체 읽기" 자체가 느려질 때 `count()` 애그리게이션 도입 |
| `firestore.indexes.json`(§9) | 초안 작성(§3 조합 4가지), 실배포/실검증 안 함 | Vercel/Firebase 배포 착수 시 `firebase deploy --only firestore:indexes` 로 실배포 + 콘솔 에러 기반 보완 |
| Vercel 배포 토폴로지 | 미확정 — 백엔드를 Vercel Functions 로 올릴지, Cloud Run 등 별도 컨테이너로 올릴지 | 배포 착수 시 첫 결정 사항. Functions 라면 `backend/Dockerfile` 무의미, WeasyPrint 시절과 달리 PDF(reportlab)는 이제 Functions 에서도 문제 없음 |
| 채번 트랜잭션 경합(§5) | `run_transaction` 애플리케이션 레벨 재시도(5회, 지수백오프) | 실사용 동시 등록자 수가 실측(에뮬레이터 15스레드)보다 훨씬 많아지면 재검토 |
