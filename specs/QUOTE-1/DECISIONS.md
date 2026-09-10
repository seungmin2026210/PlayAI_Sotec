# QUOTE-1 · 결정 로그 (DECISIONS)

원본 기획서 `기획서.md.md` v1.1 를 구현하며 내린 구체적 결정. 협의 대기 항목의 임시 결정은 [`tech/10-provisional-decisions.md`](./tech/10-provisional-decisions.md) 대응표 참조.

## 확정 사항 (기획서 명시)

- 채번 `YY-그룹코드-순번`, 그룹×연도 독립 시퀀스, 연도 롤오버 리셋, 결번 재사용 금지.
- 상태값 4종, "초안" 없음, 구매관리 반영은 상태 아닌 잠금 플래그.
- 십만단위 절사(총합계 기준, 내림), 부가세 = 절사 공급가액 × 0.1, 부가세 포함가 병기.
- 항목 금액은 항상 공급가액 기준 입력.
- 전체관리자 = 전 그룹 CRUD+승인/반려, 그룹관리자 = 본인 그룹 조회 전용.
- 반려 사유 필수, 반려건 읽기전용 보존, 재제출은 새 관리번호 신규 등록.
- 계정 정보는 상수 1곳(`config.ACCOUNTS`).
- 목록 PDF 미지원(의도).

## 구현 중 내린 결정 (기획서 공백 보완)

| 결정 | 내용 | 이유 |
|---|---|---|
| 채번 연도 기준 | 발행일자가 아닌 **등록 시각 서버 연도** | 발행일자 소급 입력 시 시퀀스 혼선 방지 |
| 삭제 방식 | 물리 삭제 아닌 soft delete(`deleted_at`) + `retired_numbers` | 결번 추적, 실수 복구 여지 |
| 999 초과 | `409 SEQ_EXHAUSTED` 로 등록 차단 | 4자리 확장은 스키마/포맷 변경이라 협의 필요 |
| 동시성 | `number_sequences` 행 `SELECT FOR UPDATE` + `quotes.mgmt_no UNIQUE` | 기획서 6장 "동시성 제어 필요" 반영 |
| 토큰 권한 | 토큰엔 username만, role/group은 매 요청 `ACCOUNTS` 재조회 | 상수 변경 즉시 반영, 권한 박제 방지 |
| 수정 시 상태 | 유지(되돌리지 않음) | open-10 미정 → 가장 단순한 기본값, 정책 함수로 격리 |
| 승인됨 읽기전용 전환 | `APPROVED` 도 `REJECTED`/`CANCELLED` 와 동일하게 `TERMINAL_STATUSES` 로 취급 — 승인 즉시 수정/취소/삭제 불가(구매관리 반영 여부 무관) | 승인 후 내용이 바뀌면 승인의 의미가 없음. 되돌릴 필요가 생기면 반려/재제출 경로로 유도 |
| 개별 export 승인 제약 | 개별 엑셀/PDF export(`/quotes/{id}/export.xlsx`\|`.pdf`)는 `status == APPROVED` 인 견적서만 허용, 아니면 `409 EXPORT_NOT_APPROVED`(`services/status.py: guard_exportable`). 프론트도 승인됨일 때만 엑셀/PDF/개인메일 발송 버튼 노출. 목록 엑셀(`/quotes/export.xlsx`)은 제약 없음 | 승인 전 견적서가 정식 문서(직인 포함 양식)로 외부에 유출되는 것을 방지 — 서버가 최종 방어선 |
| 감사로그 | 미구현, 단 상태전이 시각 컬럼은 확보 | open-5 미정, 향후 도입 비용 최소화 |
| PDF 실패 환경 | `501 PDF_UNAVAILABLE` 반환, 서버 계속 동작 | WeasyPrint(GTK) 설치 이슈 흔함, 데모 중단 방지 |
| 금액 표기 | `1,234,567원` (콤마+원, 통화기호 X) | open-6 미정 → 국내 관행 기본값, 포매터 1곳 격리 |
| 견적서 export 양식 | 엑셀·PDF 를 **실제 견적서.jpg 양식**으로 재작성(공급자/수신처 블록, 인사말, 합계금액 요약, 용역(계약), 규격·세액·비고 7열 항목표, 대금결제/납품/WORK SCOPE, 서명란) | 실사용 견적서와 서식 일치 요구 |
| export 정형 문구 | 견적유효기간·인사말·결제/납품/WORK SCOPE·작성자 팀명 등은 `config.py` 상수 1곳 | 협의로 문구 확정 시 한 곳만 수정 |
| 앱에 없는 폼 필드 | C.C(참조), 용역(계약)기간, 항목 규격·비고 는 **양식 자리만 두고 공란** | 모델/등록폼 확장 없이 서식만 맞춤 (필요 시 후속) |
| 견적NO 표기 | 저장값 `26-B-008` 유지, export 표시만 `혁신 2026-B 008` (`config.MGMT_NO_DISPLAY_PREFIX`) | 채번 로직 불변, 표기만 실사용 형식 |
| 승인 견적서 직인 | `status=APPROVED` 인 엑셀·PDF 에만 `config.SEAL_PATH` 직인 합성. 현재는 `scripts/make_seal.py` 임시 "SOTEC" 직인 → 실제 직인 오면 같은 경로 파일 교체 | 승인 완료 문서만 날인, 실직인 교체를 파일 1개로 |
| 라인별 세액 | 항목표 세액열은 `round(금액×0.1)` 참고 표시. 총계(절사·세액·합계)는 `calculation` 서비스가 정본 | 서식상 열은 채우되 세금계산서 정본 아님 |
| PDF export 구현체 | WeasyPrint(HTML→PDF) → **reportlab**(Platypus, 순수 파이썬)로 교체. 한글 폰트(나눔고딕)를 `app/assets/fonts/`에 파일로 두고 PDF에 직접 임베드 | 배포를 Vercel(서버리스)로 정하면서, WeasyPrint 가 요구하는 시스템 라이브러리(`libpango` 등)를 서버리스 함수에 설치할 수 없어 교체 필요. 순수 파이썬 + 폰트 임베드는 실행 환경(OS/시스템 라이브러리) 전혀 안 가림 |

## 배포 아키텍처 전환 (DB 레이어 마이그레이션 완료 — 2026-09)

상세 설계·실측 결과: [`tech/12-firestore-migration.md`](./tech/12-firestore-migration.md).

- **결정**: 배포는 **Vercel**(프론트 + 백엔드), DB 는 **Firebase(Firestore)** 로 확정.
- `backend/app/models.py`(→ dataclass) / `database.py`(→ Firestore client) / `deps.py` /
  `routers/*` / `services/numbering.py`(→ Firestore 트랜잭션) 전부 재작성 완료. Alembic·
  PostgreSQL·docker-compose 제거. `pytest` 30개 전부 통과, 프론트 `id` 타입(문자열) 반영 완료.
- 채번(`YY-그룹코드-순번`) 동시성: `number_sequences` 문서를 Firestore 트랜잭션으로 read-then-write.
  **실측 결과**: 같은 문서에 스레드 4개 이상이 진짜 동시에 몰리면 SDK 기본 재시도로는 부족해
  일부 요청이 완전히 실패하는 걸 확인 → `database.run_transaction()`에 애플리케이션 레벨 재시도
  (지수백오프+지터)를 추가해 2~15 스레드 동시 채번을 중복/결번/실패 없이 통과시킴(tech/12 § 5).
- PDF export 는 이 결정에 맞춰 이미 reportlab 로 전환 완료. WeasyPrint 는 제거됨.
- **남은 것**(tech/12 § 10-9,10): `firestore.indexes.json` 실배포, Vercel 배포 토폴로지 확정
  (백엔드를 Vercel Functions 로 올릴지 Cloud Run 등 컨테이너로 올릴지 — 아직 미정), 서비스
  계정/환경변수 실제 설정. `backend/Dockerfile`은 컨테이너 호스팅 전제라 Vercel Functions 로
  가면 안 쓰게 될 수 있음.

## 검토 요청 항목 (협의 시 우선)

1. **open-10 수정 이력**: 4.2에서 수정이 정식 범위가 되며 감사로그 필요성 상승(기획서 4.7 각주). 감사로그 도입 여부/범위.
2. **open-2 test1 소속 그룹**: 데모 전 확정 필요.
3. **open-4 구매관리 반영 트리거**: 현재 수동 토글. 실제 연동 형태 결정 시 재설계.
4. **open-1 그룹관리자 권한**: 조회 전용 고정 시 전체관리자 소수에 등록·승인 업무 집중 → 업무량 검토.
