# 10. 미정(❓) → 임시 결정 대응표

> 협의 미완료 항목을 "빈칸"이 아니라 **눈에 띄고 교체 쉬운 임시값**으로 구현한다.
> 협의 결과가 나오면 아래 "격리 위치"만 수정한다. 원본 근거: [PRODUCT 10](../product/10-open-issues.md).

| # | 미정 | 임시 결정 | 격리 위치 (여기만 고치면 됨) |
|---|---|---|---|
| open-1 | 그룹관리자 권한 확장 | 조회 전용 고정 | `backend/app/deps.py` (`require_super_admin`, `apply_scope`) |
| open-2 | test1 소속 그룹 | `A` | `backend/app/config.py: ACCOUNTS["test1"]["group_code"]` |
| open-3 | 역할별 화면 상세 | 원칙 기반 조건부 렌더 | `frontend/src/components/RoleGate.tsx` |
| open-4 | 구매관리 반영 트리거 | 전체관리자 수동 토글 버튼 | `POST /quotes/{id}/purchase-lock` + `frontend QuoteDetail` |
| open-5 | 감사로그 | UI 미구현, 타임스탬프만 저장 | `quotes.approved_at/rejected_at/...` 컬럼 (모델 확장 지점) |
| open-6 | 금액 표기 규칙 | `1,234,567원` | `backend services/calculation.py: format_won`, `frontend/src/lib/money.ts` |
| open-7 | 목록 필터 항목 | 관리번호/견적서명/그룹/상태/발행일자범위/담당자명 | `backend routers/quotes.py: list_quotes` params, `frontend QuoteList` 필터바 |
| open-8 | 개발 우선순위 | 잠정 순서 채택, 전 범위 구현 | — (진행상 결정) |
| open-9 | 기술 스택 | React+TS / FastAPI / **Firestore**(배포: Vercel+Firebase) | [01-stack-and-setup.md](./01-stack-and-setup.md), [12-firestore-migration.md](./12-firestore-migration.md) |
| open-10 | 수정 상세 범위 | 전체 필드 / 상태 유지 / 감사로그 미기록 | `backend services/status.py: apply_edit_policy` |
| open-11 | 999 초과 / 동시성 | 초과 시 409 차단, **Firestore 트랜잭션**(구 `FOR UPDATE`+`UNIQUE`는 폐기) | `backend services/numbering.py: allocate_in`, [12-firestore-migration.md § 5](./12-firestore-migration.md) |

## 담당자 실명 표기 (PRODUCT 03 주석)

- `config.ACCOUNTS[*].display_name` 에만 존재. 문서/화면에는 role 라벨 우선 노출, display_name 은 상세 툴팁 수준. 배포 범위 확정 시 이 값만 교체.
