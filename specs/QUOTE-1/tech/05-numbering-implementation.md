# 05. 관리번호 채번 구현

> **`SELECT ... FOR UPDATE` 는 Firestore 트랜잭션으로 교체됨.** 형식(`YY-그룹코드-순번`)·연도 기준·결번 정책은 동일하게 유지. 실제 구현은 [`12-firestore-migration.md` § 5`](./12-firestore-migration.md)(동시성 실측 결과 포함) 참고.

## 형식

`f"{yy:02d}-{group_code}-{seq:03d}"` — `yy = year % 100`, `seq` 1..999.

- `year` = **등록 시각 서버 연도** (발행일자 아님, [PRODUCT 06](../product/06-management-number.md) 참고).

## 알고리즘 (`services/numbering.py: allocate(db, group_code) -> Allocation`)

```
with db.begin_nested():                      # 또는 상위 트랜잭션에 편승
    year = now().year
    row = db.execute(
        select(NumberSequence)
        .where(NumberSequence.seq_year == year,
               NumberSequence.group_code == group_code)
        .with_for_update()
    ).scalar_one_or_none()

    if row is None:
        db.execute(pg_insert(NumberSequence)
                   .values(seq_year=year, group_code=group_code, last_seq=0)
                   .on_conflict_do_nothing())
        db.flush()
        row = db.execute(select(NumberSequence)
                         .where(...).with_for_update()).scalar_one()

    if row.last_seq >= 999:
        raise AppError("SEQ_EXHAUSTED", 409, "...999건을 초과했습니다...")

    row.last_seq += 1
    seq = row.last_seq
    mgmt_no = f"{year % 100:02d}-{group_code}-{seq:03d}"
    return Allocation(year=year, group_code=group_code, seq_no=seq, mgmt_no=mgmt_no)
```

- 채번은 **견적 insert와 같은 트랜잭션**에서 수행. 커밋 실패 시 시퀀스 증가도 롤백.
- `quotes.mgmt_no UNIQUE` 제약이 최종 방어선 (경합 시 `IntegrityError` → 500 대신 재시도 1회).

## 결번 (삭제)

- 삭제 시: `quotes.deleted_at = now()`, `retired_numbers` insert.
- `number_sequences.last_seq` **감소시키지 않음** → 이후 채번은 다음 번호부터 → 결번 자연 발생, 재사용 없음.
- 결번은 `(seq_year, group_code)` 조합 내부 개념일 뿐, 다른 조합 시퀀스에 영향 없음.

## 연도 롤오버

- 2027-01-01 00:00(서버시) 이후 첫 등록: `(2027, 'A')` 행이 없으므로 생성되어 `27-A-001`부터 시작. 2026 시퀀스는 그대로 보존.

## 동시성 테스트 (11-testing-plan 참조)

- 스레드/프로세스 2개가 동시에 같은 그룹 등록 → 관리번호 중복 없이 연속 채번.
