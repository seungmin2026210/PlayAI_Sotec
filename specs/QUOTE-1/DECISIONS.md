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

## 개별 견적서 양식 — 위탁계약형 전면대체 (2026-09)

상세 셀 매핑: [`tech/09-export.md`](./tech/09-export.md).

- **결정**: 개별 견적서 엑셀(`build_quote_xlsx`)을 SW 품목형(`견적서 샘플.xlsx`) 대신
  **`견적서_위탁계약용.xlsx`(바탕화면, 실제 발행 양식)** 로 **전면대체**. 옛 SW 품목형 구현·
  데모 데이터·테스트는 폐기하고 위탁계약형 기준으로 다시 작성했다.
- 자매 양식 `견적서_기성계약용.xlsx`(조선 설계용역 man-day형, 십만단위 절사 없이 단순 합산 —
  위탁계약형과 계산 로직 자체가 다름)는 이번 범위 밖. `Quote`에 문서유형 필드는 아직 두지
  않았다(YAGNI) — 기성계약형을 실제로 만들 때 그 작업의 일부로 추가한다.
- 스키마 확장: `Quote`에 `customer_department`(수신처 부서명)·`customer_cc`(C.C 참조인) 선택
  필드 추가, `QuoteItem`에 `period_start`/`period_end`(용역 기간) 선택 필드 추가. `qty`/
  `unit_price`는 그대로 두되(스키마 변경 최소화) 등록 폼이 `qty=1` 고정으로 보내 `unit_price`
  가 곧 공급가액이 되는 방식을 택했다 — 위탁계약형은 항목별 공급가액을 직접 입력한다.
- `COMPANY["ceo_name"]`을 "신인규" → "선인규"로 정정(실사값 재확인, `견적서 샘플.xlsx`/
  `_기성계약용.xlsx`/`_위탁계약용.xlsx` 3개 파일 모두 "선인규"로 일치). 업태/종목은 실제로
  3행(서비스·정보통신업·서비스 / 선박임가공·응용 SW 개발 및 공급업·기술검사)이라 `COMPANY`
  단일 필드 대신 `COMPANY_BIZ_LINES` 상수를 새로 뒀다.
- 한글 금액 표기("일금 ○○○원정")를 위해 `services/calculation.korean_amount_words()` 추가
  (만/억/조 단위 순수 함수, 원본 위탁/기성 샘플 실측값으로 검증).
- 개별 견적서 로고를 뺐다 — 원본 위탁계약용 양식에 로고 영역이 없음(상단은 "견적NO" 라벨 차지).
  목록 엑셀은 로고 그대로 유지.
- PDF(`build_quote_pdf`)도 엑셀 확정 후 별도 PR 로 위탁계약형에 맞춰 재작성했다(2026-09,
  아래 "개별 견적서 PDF — 엑셀 셀 그리드 직접 렌더링" 절 참고 — 처음엔 reportlab 으로
  손으로 재현했다가, 육안 비교에서 계속 어긋나 결국 셀 그리드를 그대로 읽어 그리는 방식으로
  다시 바꿨다).
- 관리번호 표시 접두어(`MGMT_NO_DISPLAY_PREFIX`)는 원본 샘플에서 부서마다 다르게 나타났지만
  ("혁신"/"의장"), 지금은 이 팀만 발행하므로 전역 상수 "혁신" 고정을 유지하고 미정 항목으로만
  기록했다(`tech/10-provisional-decisions.md`).

## 개별 견적서 PDF — 엑셀 셀 그리드 직접 렌더링 (2026-09)

상세: [`tech/09-export.md`](./tech/09-export.md) "개별 견적서 — PDF" 절.

- **문제**: 위탁계약형 엑셀 재작성 직후 PDF 도 reportlab `Platypus`(Table/Paragraph) 로
  손수 재현했으나, 라벨 문구·섹션 순서·항목 표 컬럼 등을 엑셀과 맞출 때마다 어긋나는 부분이
  계속 나왔다 — 근본 원인은 "같은 내용을 다른 코드로 두 번 표현"하는 구조 자체(엑셀 쪽 문구가
  바뀌면 PDF 쪽도 매번 손으로 따라가야 함).
- **검토한 대안**(사용자와 트레이드오프 협의):
  1. reportlab 손 재현 정밀도 개선 — 추가 개선해도 구조적으로 "따로 유지"라 근본 해결 아님.
  2. **엑셀 워크북을 셀 그리드째로 읽어 reportlab 캔버스에 직접 그리기** ← 채택.
  3. 엑셀 파일 자체를 LibreOffice 등으로 진짜 변환 — 결과물은 완전 동일하지만, 이 프로젝트가
     WeasyPrint→reportlab 전환(위 "PDF export 구현체" 결정)으로 이미 한 번 없앤 네이티브
     라이브러리 의존성을 Vercel Serverless 배포에 다시 들여오는 셈이라 기각.
  4. 클라우드 변환 API(Google Drive/Sheets, CloudConvert 등) — 배포 제약은 피하지만 견적서
     (고객사명 등)를 매 export 마다 외부로 전송해야 해 보안/개인정보 검토·요금·네트워크 장애
     처리가 새로 필요해져 기각.
- **결정**: 2번 — `export_excel.build_quote_workbook(q)`(엑셀 export 와 공유하는, 값이 채워진
  openpyxl 워크북 생성 함수로 분리)의 결과를 `export_pdf.py` 가 셀 단위로 읽어(열 너비·행
  높이·병합·테두리·배경색·정렬·rich-text 굵기) reportlab 캔버스 좌표로 변환해 그린다. 라벨
  문구·강조 규칙을 더 이상 `config.py`/PDF 코드에 중복 보관하지 않는다 — 템플릿 파일 1곳만
  정본. 네이티브 라이브러리 의존 없음(Vercel Serverless 유지).
- **트레이드오프**: 템플릿 폰트("맑은 고딕"/"Noto Sans CJK SC")가 저장소에 없어 PDF 는 여전히
  `NanumGothic` 로 대체 렌더링 — 글자폭 차이로 줄바꿈 위치 등이 미세하게 다를 수 있다(그 외
  위치·구조·서식은 동일). 사용자에게 이 한계를 명시하고 합의됨.
- **알려진 한계(범위 밖)**: 항목 18개 초과(`_extend_item_rows`, `ws.insert_rows` 경로)에서
  openpyxl 의 병합 셀 처리 한계로 세액 열이 비어 보이는 렌더링 버그 발견 — 이번 작업 범위
  밖이라 별도 트래킹(`tests/unit/test_export_pdf.py` 주석).

## 검토 요청 항목 (협의 시 우선)

1. **open-10 수정 이력**: 4.2에서 수정이 정식 범위가 되며 감사로그 필요성 상승(기획서 4.7 각주). 감사로그 도입 여부/범위.
2. **open-2 test1 소속 그룹**: 데모 전 확정 필요.
3. **open-4 구매관리 반영 트리거**: 현재 수동 토글. 실제 연동 형태 결정 시 재설계.
4. **open-1 그룹관리자 권한**: 조회 전용 고정 시 전체관리자 소수에 등록·승인 업무 집중 → 업무량 검토.
