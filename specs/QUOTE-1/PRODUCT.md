# QUOTE-1 · SW 자산 견적서 관리 시스템 (1단계: 견적서 관리)

> 원본 기획서: `바탕화면/기획서.md.md` v1.1 (2026-08-21)
> 이 문서는 원본 기획서를 섹션별 파일로 분리한 **제품 스펙(source of truth)** 입니다.
> 사용자 대면 동작의 기준은 이 문서, 아키텍처/구현 기준은 [`TECH.md`](./TECH.md) 입니다.

## 목적 요약

그룹별 SW 자산 견적서를 엑셀 수기 관리하면서 발생하는 **이력 소실 / 현황 파악 불가 / 갱신일 누락** 문제를 해소하기 위한 전산화의 **1단계**. 이번 범위는 "견적서 관리" 기능만 포함한다.

## 섹션 목차

| # | 파일 | 내용 |
|---|---|---|
| 01 | [product/01-background.md](./product/01-background.md) | 배경 및 목적, 이번 기획의 범위 |
| 02 | [product/02-scope.md](./product/02-scope.md) | 포함 범위 / 범위 외 |
| 03 | [product/03-users-and-roles.md](./product/03-users-and-roles.md) | 사용자, 역할, 권한, 그룹, 인증 방식 |
| 04 | [product/04-scenarios.md](./product/04-scenarios.md) | 핵심 시나리오 (등록/수정/취소/삭제/승인/반려/발송/Export) |
| 05 | [product/05-data-fields.md](./product/05-data-fields.md) | 데이터 항목 정의 |
| 06 | [product/06-management-number.md](./product/06-management-number.md) | 관리번호 채번 규칙 |
| 07 | [product/07-status-transitions.md](./product/07-status-transitions.md) | 상태값 및 전이 규칙 |
| 08 | [product/08-screens.md](./product/08-screens.md) | 화면 구성 |
| 09 | [product/09-error-handling.md](./product/09-error-handling.md) | 예외 / 에러 처리 |
| 10 | [product/10-open-issues.md](./product/10-open-issues.md) | 미정 사항 종합 + 향후 로드맵 |

## 확정 / 미정 구분

- **확정**: 채번 규칙, 상태 전이, 십만단위 절사, 부가세 계산, 부가세 포함가 표기, 역할별 권한 원칙(전체관리자 / 그룹관리자 조회전용), 반려 시 원본 읽기전용 보존, 계정 정보 상수 1곳 정의.
- **미정(❓)**: [10-open-issues.md](./product/10-open-issues.md) 및 [`tech/10-provisional-decisions.md`](./tech/10-provisional-decisions.md) 참고. 미정 항목은 **협의 전까지 "임시 결정"으로 구현**하며, 변경이 쉽도록 상수/정책 함수 1곳에 격리한다.
