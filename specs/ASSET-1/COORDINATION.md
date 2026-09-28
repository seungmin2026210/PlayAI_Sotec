# ASSET-1 · 구매관리(PURCHASE-1) 담당자와 조율할 사항

> 자산관리 설계(2026-09-28 인터뷰, [`DECISIONS.md`](./DECISIONS.md))가 기존 PURCHASE-1 설계와 부딪히는
> 지점만 모았다. **합의 전에는 자산관리 구현을 시작하지 않는다.** 합의 결과는 각 항목의 "합의 결과"
> 칸에 적고, PURCHASE-1 쪽 문서(`specs/PURCHASE-1/DECISIONS.md`, `tech/01-data-model.md`)도 같이 고친다.

## 요약

PURCHASE-1은 "구매 유닛 = 자산"을 전제로 배정까지 구매 유닛에 붙이는 설계였다. 자산관리는
**재판매(대리구매)품이 섞여 있다**는 이유로 자산을 별도 컬렉션(`assets`)으로 분리하고, 구매 유닛은
"골라서 가져오는" 원천으로만 쓴다. 이 때문에 아래 항목들이 바뀐다.

---

## C1. 배정 설계(`asset_assignments`)의 소유권 이동

- **현재(PURCHASE-1)**: `asset_assignments.unit_id` → `asset_units` 참조. 배정 시 `asset_units.status`를
  `AVAILABLE → ASSIGNED`로 갱신(`tech/01-data-model.md` §4, §6, §7 — 설계 스케치, 미구현).
- **제안(ASSET-1)**: 배정은 `assets`에 붙는다. `asset_assignments.asset_no` → `assets` 참조.
  구매 유닛은 배정과 무관.
- **필요한 변경**: PURCHASE-1 `tech/01-data-model.md` §4·§6·§7을 "ASSET-1로 이관" 표시 후 삭제 또는
  링크로 대체. `TECH.md` "남은 작업 2"도 갱신.
- **합의 결과**: _(미정)_

## C2. 구매 유닛 상태 `ASSIGNED`(배정됨) 폐지

- **현재**: `ASSET_UNIT_STATUS_LABELS = 재고 / 배정됨 / 만료`(`backend/app/config.py`), 구매 목록 상태 필터에도 노출.
- **제안**: 구매 유닛에서 "배정됨"은 더 이상 발생하지 않음 → 상태를 `재고(AVAILABLE) / 만료(EXPIRED)`로
  줄이거나, 의미를 바꾸지 말고 그대로 두되 쓰지 않음.
- **대안**: 자산으로 가져온 유닛은 C3의 `asset_no`로 구분하므로 상태값을 건드리지 않는 방법도 있다
  (코드 변경 최소). **자산관리 쪽 추천: 상태값 정리는 구매관리 담당자 판단에 맡김.**
- **합의 결과**: _(미정)_

## C3. 구매 유닛에 `asset_no` 역참조 필드 추가

- **제안**: `asset_units/{unit_no}`에 `asset_no: string | null` 추가. 자산관리 "가져오기" 트랜잭션이
  이 값을 채운다(같은 유닛 중복 가져오기 방지, DECISIONS D4).
- **구매관리 쪽 영향**:
  - 모델(`models.AssetUnit`)·스키마·presenter에 필드 추가(기본 `null`, 기존 문서는 없음 = null 취급)
  - 구매 목록/상세에 **"자산 등록됨(SW-26-012)"** 배지 + 자산 상세 링크
  - 쓰기 주체는 자산관리 트랜잭션뿐 — 구매관리 API로는 수정 불가
- **합의 결과**: _(미정)_

## C4. 자산으로 가져온 구매 유닛의 폐기

- **질문**: 구매관리에서 유닛을 폐기(`retire`)하면, 이미 가져온 자산은?
- **자산관리 쪽 제안**: 자산은 영향 없음(D2 — 가져오는 시점 복사). 구매 유닛 폐기는 "구매 기록"의 일이고,
  자산 폐기는 자산관리에서 따로. 단, 구매 상세에서 폐기할 때 "자산 SW-26-012로 등록된 유닛입니다" 경고
  정도는 있으면 좋음.
- **합의 결과**: _(미정)_

## C5. 구매 유닛의 키 값(`unit_type`/`key_value`) 매핑

- 가져오기 시 매핑 규칙(자산관리 쪽 제안):
  | 구매 유닛 | → 자산 |
  |---|---|
  | `unit_type=KEY`, `key_value` | SW `license_key` |
  | `unit_type=ACCOUNT`, `key_value` | SW/EDU `account_id` |
  | `expire_date` | `valid_to` |
  | `product_name` | `name`(EDU는 `course_title`에도) |
  | `purchased_from` / `price` / `purchase_date` | 동일 필드 |
  | `source_quote_id` | `quote_no` |
  | `group_code` | `group_code`(등록 그룹) |
- **확인 필요**: PURCHASE-1 TECH.md "알려진 개선 포인트" — SW인데 유닛 타입 미선택 등록을 막지 않음.
  비어 있으면 자산 쪽에서 빈 값으로 가져와 나중에 입력받으면 되므로 **블로커 아님**.
- **계정 비밀번호**: 구매 유닛엔 비밀번호 칸이 없다. 자산관리에서만 입력·암호화 저장(D15).
  구매 쪽에 비밀번호 칸을 추가하지 **않는 것**을 제안(평문 저장 지점을 늘리지 않기 위해).
- **합의 결과**: _(미정)_

## C6. `config.py` 상수 공유

- 기존 `ASSET_CATEGORY_LABELS`(SW/HW/EDU)는 그대로 재사용. `EDU` 라벨이 "교육자산"인데 자산관리 메뉴는
  "교육"으로 표기 — 라벨을 바꿀지, 화면에서만 다르게 쓸지.
- 신규 상수(`ASSET_STATUS_*`, `ASSET_SUBCATEGORIES`, `ASSET_NO_*`)는 같은 파일의 PURCHASE-1 섹션 아래
  "자산관리(ASSET-1)" 섹션으로 추가 — 충돌 방지 위해 섹션 분리.
- **합의 결과**: _(미정)_

## C7. 사이드바·라우트

- `design/Sidebar.tsx`의 `CONTRACT_CHILDREN`에 `{ key: "assets", label: "자산관리", path: "/assets" }` 추가,
  `App.tsx`에 `/assets/*` 라우트 추가. 구매관리 브랜치와 같은 파일을 만지므로 **머지 순서** 합의 필요
  (추천: 구매관리 브랜치 main 머지 후 자산관리 브랜치를 그 위에서 시작).
- **합의 결과**: _(미정)_

## C8. 범위(CLAUDE.md) 변경

- CLAUDE.md "범위 밖" 목록의 **갱신 캘린더**, **자산 배정 이력**이 이번 자산관리 범위로 들어온다(D28).
  CLAUDE.md 갱신은 자산관리 구현 PR에서 같이 한다 — 이견 있으면 알려주기.
- **합의 결과**: _(미정)_
