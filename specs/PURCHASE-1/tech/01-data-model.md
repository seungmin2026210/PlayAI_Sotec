# 1. Firestore 데이터 모델 (구매관리 · 자산관리)

배경: [`../DECISIONS.md`](../DECISIONS.md), [`../TECH.md`](../TECH.md). 컨벤션은 QUOTE-1과 동일하게 맞춤(`specs/QUOTE-1/tech/12-firestore-migration.md`) — 의미 있는 문서 ID를 우선 쓰고, 날짜는 Timestamp 대신 `YYYY-MM-DD` 문자열, soft delete는 상태값으로 표현.

> `asset_units`/`asset_product_seq`/`asset_products`(§1-3, §5)는 **구현 완료**(`backend/app/`,
> `TECH.md` 참고). `asset_assignments`(§4, §6-7)는 아직 자산관리 팀원 구현 전 설계 스케치다.

`db/schema.sql`의 PostgreSQL 버전(`asset_products`/`asset_units`/`asset_assignments`/트리거)은 이 설계의 로컬 검증용 프로토타입이다 — 실제 구현은 아래 컬렉션 구조와 트랜잭션 로직을 따른다.

## 1. `asset_products/{productId}`

상품 마스터. `productId`는 **auto-id**(상품명이 바뀔 수 있어서 name을 ID로 안 씀 — DECISIONS.md 남은 질문 3).

```jsonc
{
  "name": "인텔리제이",
  "vendor": "JetBrains",
  "asset_category": "SW",        // SW | HW | EDU
  "is_active": true,             // false = 신규 구매 드롭다운에서 숨김(기존 유닛은 그대로 보임)
  "created_at": <Timestamp>
}
```

## 2. `asset_product_seq/{productId}`

상품별 채번 카운터. 문서 ID = `productId` 그대로(쿼리 없이 `get()` 1회로 접근 — QUOTE-1의 `number_sequences/{year}-{group_code}`와 동일 패턴).

```jsonc
{ "last_seq": 2 }
```

## 3. `asset_units/{unitNo}`

구매관리 탭 전용. **문서 ID = `unit_no`**(예: `"인텔리제이-001"`) — 채번 트랜잭션이 끝나는 시점에 이미 유일성이 보장되므로 auto-id를 또 만들지 않는다(QUOTE-1의 `quotes/{mgmt_no}`와 동일 이유).

```jsonc
{
  "unit_no": "인텔리제이-001",      // 문서 ID와 동일 값 중복 저장(쿼리 편의)
  "product_id": "abc123",
  "product_name": "인텔리제이",     // 목록 화면에서 join 없이 보여주기 위한 비정규화
  "asset_category": "SW",          // product에서 복사(그룹 스코프 쿼리·필터용)

  "purchase_date": "2026-01-10",   // 문자열
  "purchased_from": "마이크로소프트 리셀러",
  "price": 1200000,

  "unit_type": "KEY",              // "KEY" | "ACCOUNT" | null(HW)
  "key_value": "ref-a1-2022",      // 키 값 또는 배정용 계정 값

  "expire_date": "2027-01-09",     // null = 무기한
  "status": "AVAILABLE",           // "AVAILABLE" | "ASSIGNED" | "EXPIRED" — 트랜잭션으로만 갱신(§5)

  "source_quote_id": null,         // 견적에서 연동된 경우 quotes 문서 ID
  "group_code": "A",              // config.GROUPS 참조(quotes와 동일 컨벤션, 별도 groups 컬렉션 없음)

  "retired_at": null,              // 만료/폐기 처리 시각. 채워져도 문서는 안 지움(번호 영구 보존)
  "created_at": <Timestamp>,
  "updated_at": <Timestamp>
}
```

## 4. `asset_assignments/{assignmentId}`

자산관리 탭 전용. `assignmentId`는 auto-id(한 유닛에 배정~반납이 여러 번 쌓이므로 자연스러운 비즈니스 키가 없음).

```jsonc
{
  "unit_id": "인텔리제이-001",      // asset_units 문서 ID
  "unit_no": "인텔리제이-001",      // 비정규화(목록에서 join 없이 표시)
  "assigned_to": "Z2300115",       // 사원번호
  "assigned_by": "admin",          // 배정한 전체관리자 — deps.py에서 role 체크
  "assigned_at": <Timestamp>,
  "returned_at": null              // null = 현재 배정 중. 채워지면 반납 완료(수동 처리만, §6)
}
```

## 5. 유닛 생성 — 채번 + (있으면) 견적서 잠금 원자적 처리

PostgreSQL 버전은 `nextval()` + `AFTER INSERT` 트리거로 처리했지만, Firestore는 **하나의 트랜잭션**으로 묶는다(QUOTE-1의 `create_quote`가 채번+생성을 트랜잭션으로 묶은 것과 동일 패턴).

```python
# services/units.py 개념 스케치
def create_asset_unit(client, *, product_id, purchase_date, purchased_from, price,
                       unit_type=None, key_value=None, expire_date=None,
                       source_quote_id=None, group_code):
    @firestore.transactional
    def txn(transaction):
        # Firestore 트랜잭션은 모든 read 가 모든 write 보다 먼저 실행돼야 한다 — 견적서를
        # 먼저 읽어두고, 채번(내부적으로 read-then-write)을 그 다음에 호출한다.
        product_ref = client.collection("asset_products").document(product_id)
        product = product_ref.get(transaction=transaction).to_dict()

        quote_ref, quote = None, None
        if source_quote_id:
            quote_ref = client.collection("quotes").document(source_quote_id)
            quote = quote_ref.get(transaction=transaction).to_dict()

        seq_ref = client.collection("asset_product_seq").document(product_id)
        seq_snap = seq_ref.get(transaction=transaction)
        next_seq = (seq_snap.to_dict()["last_seq"] if seq_snap.exists else 0) + 1
        unit_no = f'{product["name"]}-{next_seq:03d}'

        transaction.set(seq_ref, {"last_seq": next_seq})

        unit_ref = client.collection("asset_units").document(unit_no)
        transaction.set(unit_ref, {
            "unit_no": unit_no, "product_id": product_id,
            "product_name": product["name"], "asset_category": product["asset_category"],
            "purchase_date": purchase_date, "purchased_from": purchased_from, "price": price,
            "unit_type": unit_type, "key_value": key_value, "expire_date": expire_date,
            "status": "AVAILABLE", "source_quote_id": source_quote_id, "group_code": group_code,
            "retired_at": None, "created_at": SERVER_TIMESTAMP, "updated_at": SERVER_TIMESTAMP,
        })

        # 새 필드를 만들지 않고 QUOTE-1의 기존 apply_purchase_lock()을 그대로 재사용한다
        # (specs/QUOTE-1/DECISIONS.md open-4 실연동, DECISIONS.md "백엔드 구현 완료" 참고).
        if quote and not quote.get("purchase_locked"):
            transaction.update(quote_ref, {"purchase_locked": True, "locked_at": SERVER_TIMESTAMP})

        return unit_no

    return run_transaction(client, txn)  # database.run_transaction — 재시도 로직 포함(기존 공용 함수 재사용)
```

`run_transaction`은 QUOTE-1에서 이미 만든 재시도 래퍼(`backend/app/database.py`)를 그대로 재사용한다 — 동시 구매 등록이 몰릴 때 SDK 기본 재시도로 부족한 경우 대비(tech/12 §5 실측과 동일 이유).

## 6. 배정 생성 — 중복 배정 방지 + 유닛 상태 동기화

PostgreSQL 버전은 부분 `UNIQUE` 인덱스로 "유닛당 활성 배정 1건"을 강제했다. Firestore는 제약이 없으므로 **트랜잭션 안에서 직접 확인**한다.

```python
def assign_unit(client, *, unit_id, assigned_to, assigned_by):
    @firestore.transactional
    def txn(transaction):
        unit_ref = client.collection("asset_units").document(unit_id)
        unit = unit_ref.get(transaction=transaction).to_dict()
        if unit["status"] != "AVAILABLE":
            raise AppError("ASSET_NOT_AVAILABLE", 409, "이미 배정되었거나 재고 상태가 아닙니다")

        assignment_ref = client.collection("asset_assignments").document()
        transaction.set(assignment_ref, {
            "unit_id": unit_id, "unit_no": unit_id,
            "assigned_to": assigned_to, "assigned_by": assigned_by,
            "assigned_at": SERVER_TIMESTAMP, "returned_at": None,
        })
        transaction.update(unit_ref, {"status": "ASSIGNED", "updated_at": SERVER_TIMESTAMP})
        return assignment_ref.id

    return run_transaction(client, txn)
```

`unit.status`를 트랜잭션 안에서 읽고 확인하므로, PostgreSQL의 부분 `UNIQUE` 인덱스와 동일한 효과(동시에 두 건이 같은 유닛을 배정하려 하면 트랜잭션 충돌로 하나는 재시도/실패)를 낸다.

## 7. 반납 — 수동 처리, 유닛 상태 복구

```python
def return_unit(client, *, assignment_id):
    @firestore.transactional
    def txn(transaction):
        assignment_ref = client.collection("asset_assignments").document(assignment_id)
        assignment = assignment_ref.get(transaction=transaction).to_dict()
        if assignment["returned_at"] is not None:
            raise AppError("ALREADY_RETURNED", 409, "이미 반납 처리되었습니다")

        transaction.update(assignment_ref, {"returned_at": SERVER_TIMESTAMP})

        unit_ref = client.collection("asset_units").document(assignment["unit_id"])
        transaction.update(unit_ref, {"status": "AVAILABLE", "updated_at": SERVER_TIMESTAMP})

    run_transaction(client, txn)
```

만료 시 자동 반납은 만들지 않는다(DECISIONS.md) — 이 함수는 관리자가 자산관리 화면에서 명시적으로 호출할 때만 실행된다.

## 8. 조회 — 그룹 스코프 · 잔여수량

- **그룹 스코프**: QUOTE-1과 동일하게 `group_code == ...` 등호 필터 + 서버(`deps.py`) 최종 방어선. RLS 없음(Firestore 자체 제약).
- **상품별 잔여수량**: 별도 카운터를 저장하지 않고, `asset_units`에서 `product_id == X AND status == "AVAILABLE"`을 쿼리해서 개수를 센다(QUOTE-1이 `total`을 애플리케이션 레벨 `len()`으로 계산한 것과 동일 이유 — 지금 규모에서는 캐시 필드를 따로 관리하는 비용이 더 큼).
- 복합 필터(`product_id` + `status`, `group_code` + `status` 등)는 `firestore.indexes.json`에 복합 인덱스 추가 필요 — 실제 쿼리 작성 시점에 에러 메시지 보고 추가(QUOTE-1 때와 동일 절차, tech/12 §9).
