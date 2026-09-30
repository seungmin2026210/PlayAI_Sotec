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
| POST | `/api/asset-units/{unit_no}/retire` | 전체관리자 | 폐기(soft delete) + 가져온 자산 연쇄 폐기(ASSET-1 D49) |
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

## 남은 작업

1. ~~프론트엔드(`/purchase` 라우트)~~ — 완료.
2. 자산관리(`asset_assignments`) — 팀원 구현, 이 문서의 `AssetUnit.status` 전이(AVAILABLE↔ASSIGNED)를
   그쪽에서 트랜잭션으로 갱신하게 된다(`tech/01-data-model.md` § 6-7 참고).
3. `firestore.indexes.json` — 실제 배포 전 `asset_units`의 등호 필터 조합(product_id+status,
   group_code+status 등) 쿼리 에러를 보고 복합 인덱스 추가(QUOTE-1과 동일 절차).
