# QUOTE-1 · 기술 스펙 (Tech Spec)

> 아키텍처 / 시퀀싱 / 구현 형태의 source of truth.
> 사용자 대면 동작 기준은 [`PRODUCT.md`](./PRODUCT.md).

## 섹션 목차

| # | 파일 | 내용 |
|---|---|---|
| 01 | [tech/01-stack-and-setup.md](./tech/01-stack-and-setup.md) | 기술 스택, 로컬 실행, 환경변수 |
| 02 | [tech/02-architecture.md](./tech/02-architecture.md) | 시스템 구조, 디렉터리, 요청 흐름 |
| 03 | [tech/03-data-model.md](./tech/03-data-model.md) | DB 스키마 (테이블/제약/인덱스) |
| 04 | [tech/04-api-endpoints.md](./tech/04-api-endpoints.md) | REST API 명세, 에러 코드 |
| 05 | [tech/05-numbering-implementation.md](./tech/05-numbering-implementation.md) | 관리번호 채번 알고리즘·동시성 |
| 06 | [tech/06-status-machine.md](./tech/06-status-machine.md) | 상태 머신, 전이 가드 |
| 07 | [tech/07-auth-and-permissions.md](./tech/07-auth-and-permissions.md) | 인증 시뮬레이션, 권한 판정 |
| 08 | [tech/08-calculation-rules.md](./tech/08-calculation-rules.md) | 절사·부가세·포매팅 구현 |
| 09 | [tech/09-export.md](./tech/09-export.md) | 엑셀/PDF export 구현 |
| 10 | [tech/10-provisional-decisions.md](./tech/10-provisional-decisions.md) | 미정(❓) → 임시 결정 대응표 |
| 11 | [tech/11-testing-plan.md](./tech/11-testing-plan.md) | 테스트 전략, 검증 항목 |

## 구현 순서 (실제 진행)

1. 백엔드 스캐폴드 + config 상수 + DB 모델/마이그레이션 + seed
2. 채번 서비스 + 계산 서비스 (+ 단위 테스트)
3. 인증/권한 + 견적 CRUD API
4. 상태 전이 API (승인/반려/취소/삭제/잠금)
5. Export (엑셀 개별·목록, PDF 개별)
6. 프론트: 로그인 → 목록 → 상세 → 등록/수정 → 액션 → export/발송
7. 통합 확인 + README
