# PURCHASE-1 · 기술 스펙 (Tech Spec)

> 아키텍처/구현 기준. 사용자 대면 동작 기준은 [`PRODUCT.md`](./PRODUCT.md).
> 데이터 모델 상세: [`tech/01-data-model.md`](./tech/01-data-model.md).
> 결정 로그: [`DECISIONS.md`](./DECISIONS.md).

## 스택

QUOTE-1과 동일한 백엔드/프론트엔드를 그대로 확장한다 — 새 스택 도입 없음.

- 백엔드: FastAPI + `google-cloud-firestore` (`backend/app/`)
- 프론트엔드: React 18 + TypeScript + Vite (`frontend/src/`)
- DB: Firestore(에뮬레이터로 로컬 개발/테스트, `npx firebase-tools emulators:start --only firestore`)

## 구현된 백엔드 구조

| 파일 | 역할 |
|---|---|
| `config.py` | `ASSET_CATEGORY_LABELS`(SW/HW/EDU), `ASSET_UNIT_STATUS_LABELS`(재고/배정됨/만료), `ASSET_UNIT_TYPE_LABELS`(키/계정) 추가 — 기존 상수 정의 원칙(1곳) 유지 |
| `models.py` | `AssetProduct`(`asset_products/{id}`, auto-id), `AssetUnit`(`asset_units/{unit_no}`, 문서ID=unit_no) dataclass 추가. `Quote`/`QuoteItem` 패턴과 동일(`to_dict`/`from_doc`) |
| `errors.py` | `PRODUCT_INACTIVE`, `ALREADY_RETIRED` 코드 추가 |
| `deps.py` | `assert_can_view_asset_unit(unit, user)` 추가 — `assert_can_view(quote, user)`와 동일 원칙(그룹관리자 타그룹 접근 시 404) |
| `services/asset_numbering.py` | `allocate_unit_no_in`/`allocate_unit_no` — `services/numbering.py`의 `number_sequences` 패턴을 `asset_product_seq/{product_id}`에 적용(연도 개념 없음) |
| `services/asset_query.py` | `list_asset_units` — `services/query.py`와 동일 원칙(등호 필터만 Firestore 쿼리, 나머지는 애플리케이션 레벨) |
| `routers/asset_products.py` | `GET/POST /api/asset-products`, `PATCH /api/asset-products/{id}` |
| `routers/asset_units.py` | `GET/POST /api/asset-units`, `GET /api/asset-units/{unit_no}`, `POST /api/asset-units/{unit_no}/retire` |
| `presenter.py` | `to_asset_product_read`, `to_asset_unit_read`, `to_asset_unit_list_item` — 파생 필드(라벨류) 계산 |

## 데이터 모델

전체 필드 정의: [`tech/01-data-model.md`](./tech/01-data-model.md). 구현 중 원 설계에서 바뀐 점:

- **`group_id`(UUID, 별도 `groups` 컬렉션) → `group_code`(문자열, `config.GROUPS`)로 변경.**
  QUOTE-1이 이미 `groups` 컬렉션 없이 `config.GROUPS`(A~E) 상수 + `group_code` 필드로 그룹을
  다루고 있어서, 그 컨벤션을 그대로 따랐다(새 컬렉션을 만들지 않음).
- **배정 대상자(`assigned_to`)는 사용자 컬렉션 참조가 아니라 자유 텍스트가 될 예정**이다 —
  QUOTE-1에 개별 직원 로그인/디렉터리가 없고(`config.ACCOUNTS`는 관리자 계정 2개뿐), 이 필드는
  이번 PR 범위(구매관리)에 없으므로 자산관리 구현 시 확정한다.

## 견적 연동 — 기존 잠금 메커니즘 재사용

QUOTE-1은 이미 `Quote.purchase_locked`/`locked_at` 필드와 `services/status.apply_purchase_lock()`을
가지고 있었다(구매관리 반영을 위한 자리표시 — `specs/QUOTE-1/DECISIONS.md` open-4 "현재 수동
토글. 실제 연동 형태 결정 시 재설계"). 이번 구현이 그 실연동이다:

```python
# routers/asset_units.py: create_asset_unit 내부
if quote is not None and apply_purchase_lock(quote):
    transaction.update(quote_ref, {"purchase_locked": True, "locked_at": quote.locked_at})
```

`/quotes/{id}/purchase-lock` 수동 엔드포인트는 그대로 남겨둔다(견적 연동 없이 별도로 구매한
경우 등 대비) — 이번 변경은 추가일 뿐 기존 동작을 없애지 않는다.

**Firestore 트랜잭션 read-before-write 제약**: 한 트랜잭션 안에서 모든 read는 모든 write보다
먼저 실행돼야 한다. `create_asset_unit`은 (1) 견적서 read → (2) 채번(`asset_product_seq` read
+ write) → (3) 유닛 write → (4) 견적서 update 순서로, 두 번째 read(채번 내부의 read)까지 전부
첫 번째 write(채번 내부의 write) 이전에 끝나도록 순서를 맞췄다.

## API 엔드포인트

| 메서드 | 경로 | 권한 | 설명 |
|---|---|---|---|
| GET | `/api/asset-products` | 로그인 | 상품 목록(`is_active` 필터) |
| POST | `/api/asset-products` | 전체관리자 | 상품 등록 |
| PATCH | `/api/asset-products/{id}` | 전체관리자 | 이름/벤더/사용여부 수정 |
| GET | `/api/asset-units` | 로그인(그룹 스코프) | 유닛 목록(상품/상태/그룹 필터, 페이지네이션) |
| POST | `/api/asset-units` | 전체관리자 | 유닛 등록(채번 + 견적 연동 시 자동 잠금) |
| GET | `/api/asset-units/{unit_no}` | 로그인(그룹 스코프) | 유닛 상세 |
| POST | `/api/asset-units/{unit_no}/retire` | 전체관리자 | 폐기(soft delete) |
| GET | `/api/meta` | 로그인 | 기존 응답에 `asset_categories` 필드 추가 |

에러 코드는 `errors.py`에 상수로 정의, 응답 형태는 QUOTE-1과 동일 `{"detail":{"code","message"}}`.

## 테스트

`backend/tests/test_purchase.py` — 상품 CRUD/권한, 상품별 독립 채번, 결번 재사용 방지, 비활성
상품 등록 차단, 폐기(soft delete·중복폐기 차단), 견적 연동 자동 잠금, 그룹 스코프(목록/상세/403)를
검증. 기존 `conftest.py`의 `_COLLECTIONS` 정리 목록에 `asset_products`/`asset_product_seq`/
`asset_units` 추가.

```bash
cd backend && source .venv/bin/activate
python -m pytest tests/test_purchase.py -v
```

로컬 검증 결과: 신규 14개 + 기존 36개 = **50개 전부 통과**, 회귀 없음.

## 프론트엔드 구현 완료 (2026-09)

`frontend/src/pages/Purchase{List,Form,Detail,ProductList}.tsx` — 기존 `design/AppShell`·
`Sidebar`·`/purchase` 라우트를 그대로 확장(새 디자인 시스템 없음). `api/purchase.ts`에 엔드포인트
래퍼, `api/client.ts`에 `PATCH` 메서드 지원 추가(상품 활성/비활성 토글용).

로컬 Firestore 에뮬레이터 + 실행 중인 개발 서버로 브라우저 전체 플로우를 직접 확인했다: 상품
등록 → 구매 유닛 등록(채번 `인텔리제이-001` 확인) → 목록/필터 → 견적 연동 시 해당 견적서
자동 잠금(`읽기전용(구매반영)` 배지 표시 확인) → 폐기 처리(상태 `만료` 전환, 번호 보존).

**알려진 개선 포인트(치명적이지 않음)**: SW 상품인데 유닛 타입(키/계정)을 선택하지 않고
등록해도 현재는 막지 않는다 — 실사용하면서 필수로 강제할지 결정.

## 사용성 피드백 반영 (2026-09-30)

실사용 피드백: 잘못 등록한 구매 정보를 고칠 방법이 없어 "삭제 후 재등록"을 시도했지만
애초에 삭제 자체가 없어서(번호 영구보존 원칙) 막힌 사례. 이걸 계기로 두 가지 추가:

- **`PATCH /api/asset-units/{unit_no}`** — 구매 유닛 수정. 삭제는 여전히 없음(번호 영구보존
  유지) — 대신 수정으로 고친다. 상품(`product_id`)·유닛번호·연동 견적서는 바꾸지 않음(번호가
  상품명 기준이라 상품이 바뀌면 어긋남). 폐기(`EXPIRED`)된 유닛은 수정도 막는다(전체관리자만,
  `require_super_admin`). 프론트: `PurchaseForm`을 create/edit 겸용으로 바꾸고 `PurchaseDetail`에
  "수정" 버튼 추가.
- **금액 입력 콤마 포맷팅** — `components/MoneyInput.tsx` 신규(타이핑 중 실시간 천단위 콤마,
  `lib/money.parseWon`으로 역파싱). 구매관리 등록/수정뿐 아니라 견적서 항목 입력
  (`ItemsEditor`)과 자산관리 등록(`AssetForm`, ASSET-1)까지 전부 적용 — "금액 입력은 어디서든
  일관되게" 라는 피드백이라 PURCHASE-1 범위를 넘어 프로젝트 전체 금액 입력 필드에 반영했다.

## 견적서 "종결" 상태 추가 (2026-09-30, QUOTE-1 상태 머신 확장)

배경: 구매관리를 실사용하면서 "승인된 견적서가 계속 쌓이면 목록이 길어져서 보기 불편하다"는
피드백. 처음엔 "이 견적서로 등록된 자산 합계가 견적 금액을 다 채우면 자동 종결"하는 방향을
검토했으나(자산의 `quote_no`가 항상 실제 견적서 ID라는 보장이 없어 신뢰성 문제도 있었음),
논의 끝에 **수동 종결 버튼**으로 단순화했다 — "더 이상 이 견적서로 구매하지 않을 때" 전체관리자가
직접 누르는 액션.

- `config.STATUS_CLOSED`("CLOSED"/"종결") 추가. `services/status.py`의 `TERMINAL_STATUSES`에
  포함(이미 `APPROVED`가 읽기전용이라 권한/수정 로직에는 변화 없음 — 목록 노출만 바뀜).
  `ALLOWED`에 `(APPROVED, "close") -> CLOSED` 전이 추가, `Quote.closed_at` 필드 신규.
- `POST /api/quotes/{id}/close`(전체관리자만) — `routers/quotes.py`.
- `services/query.py: list_quotes` — **`status` 필터를 명시적으로 안 준 기본 목록 조회에서만**
  `CLOSED`를 제외. 상태 필터를 `CLOSED`로 지정하면 그대로 조회됨(완전히 숨기지 않고 필터로
  찾아볼 수 있게 — 감사·확인 목적).
  `guard_exportable`은 `APPROVED`뿐 아니라 `CLOSED`도 허용(승인 문서 자체는 그대로라 export는
  계속 가능해야 함 — 처음 구현 때 빠뜨렸다가 리뷰 중 수정).
- 프론트: `QuoteDetail`에 "종결" 버튼(APPROVED일 때만), 엑셀/PDF 버튼은 `APPROVED`뿐 아니라
  `CLOSED`에서도 노출(`canExport`). `QuoteList`의 상태 필터 드롭다운은 `meta.statuses`를 그대로
  쓰므로 코드 변경 없이 "종결"이 자동으로 옵션에 추가됨.
- **부수 효과(의도된 것)**: 견적 종결 시 상태가 `APPROVED`가 아니게 되므로, 구매관리
  "연동 견적서" 드롭다운(`status=APPROVED`만 조회)에서 자동으로 빠진다 — 별도 코드 없이
  "종결된 견적서로는 더 이상 새로 구매 연동을 못 한다"가 자연스럽게 성립.
- 테스트: `backend/tests/test_status.py`에 6개 추가(전이 제약, 목록 숨김/필터 조회, export
  가능 확인, 중복 종결 차단, 권한). `backend/tests/test_purchase.py`에 PATCH 관련 4개 추가.
  전체 **111개 전부 통과**.

## 남은 작업

1. ~~프론트엔드(`/purchase` 라우트)~~ — 완료.
2. 자산관리(`asset_assignments`) — 팀원 구현, 이 문서의 `AssetUnit.status` 전이(AVAILABLE↔ASSIGNED)를
   그쪽에서 트랜잭션으로 갱신하게 된다(`tech/01-data-model.md` § 6-7 참고).
3. `firestore.indexes.json` — 실제 배포 전 `asset_units`의 등호 필터 조합(product_id+status,
   group_code+status 등) 쿼리 에러를 보고 복합 인덱스 추가(QUOTE-1과 동일 절차).
