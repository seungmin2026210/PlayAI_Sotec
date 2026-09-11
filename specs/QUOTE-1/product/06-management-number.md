# 06. 관리번호 채번 규칙

## 규칙 (확정)

- 형식: `YY-그룹코드-순번` (예: `26-A-001` = 2026년 · 기술개발그룹 · 1번).
- 그룹코드: [03-users-and-roles.md](./03-users-and-roles.md) 3.2 (A~E).
- 순번은 **그룹 × 연도 조합별로 독립적인 시퀀스** (예: `26-A-001`과 `26-B-001`은 서로 무관).
- 연도가 바뀌면 각 그룹 시퀀스는 `001`부터 재시작.
- 삭제 시 해당 관리번호는 **결번 처리**, 결번은 **해당 연도+그룹 조합 안에서만** 유효 (다른 그룹/연도 시퀀스에 영향 없음).
- 결번은 **재사용하지 않음**.
- 연도(`YY`)는 **견적 발행일자**가 아니라 **등록 시각(서버 기준)** 의 연도를 사용한다. *(구현 상 결정 — 발행일자 소급 입력 시 시퀀스 혼선 방지)*

## ❓ 미정 (open-11)

- 순번 3자리(999건) 초과 시 처리 방식 미정.
  → **임시 결정**: 1000번째 채번 시도 시 `409 Conflict` + 메시지 `"해당 그룹/연도 관리번호가 999건을 초과했습니다. 관리자에게 문의하세요."` 반환하고 등록 차단. 4자리 확장은 협의 후.
- 동시 등록 시 시퀀스 중복 방지(동시성 제어) 필요.
  → **구현**: `number_sequences/{year}-{group_code}` 문서를 Firestore 트랜잭션으로 읽고 `last_seq + 1`로 갱신(등록 자체와 같은 트랜잭션에 묶어 원자성 확보). 문서 ID가 `mgmt_no`이므로 중복 생성 자체가 불가능해 이중 안전장치 역할도 겸한다. (구 설계였던 PostgreSQL `SELECT ... FOR UPDATE` + `UNIQUE` 제약은 폐기됨 — [`tech/12-firestore-migration.md`](../tech/12-firestore-migration.md) 참고.)

## 구현 매핑

- 알고리즘·트랜잭션: [`tech/05-numbering-implementation.md`](../tech/05-numbering-implementation.md), [`tech/12-firestore-migration.md`](../tech/12-firestore-migration.md) § 5.
- 컬렉션: `number_sequences`, `retired_numbers` — 원 설계는 [`tech/03-data-model.md`](../tech/03-data-model.md)(폐기, 개념 참고용), 실제 문서 구조는 `tech/12-firestore-migration.md`.
