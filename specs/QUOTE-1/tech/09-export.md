# 09. Export 구현

개별 견적서(엑셀·PDF)는 `status == APPROVED` 인 견적서만 내보낼 수 있다 —
승인 전(`SUBMITTED`)/반려됨/취소됨 상태로 요청하면 `409 EXPORT_NOT_APPROVED`
(`routers/quotes.py: export_quote_xlsx/export_quote_pdf` → `services/status.py: guard_exportable`).
목록 엑셀(`/quotes/export.xlsx`)은 이 제약과 무관하게 모든 상태를 포함한다.

개별 견적서 엑셀(`build_quote_xlsx`)은 바탕화면 **`견적서_위탁계약용.xlsx`(실제 발행 양식)** 을
셀 단위(위치·병합·서식)로 그대로 옮긴 것 — 아래 "개별 견적서 — 엑셀" 절의 행 배치가 그
매핑이다. **위탁계약형으로 전면대체**했다(DECISIONS.md) — SW 품목형 `견적서 샘플.xlsx` 양식·
`build_quote_xlsx`의 이전 구현은 폐기했다. 자매 양식 `견적서_기성계약용.xlsx`(조선 설계용역
man-day형, 십만단위 절사 없이 단순 합산 — 위탁계약형과 계산 로직 자체가 다름)은 이번 범위
밖 — 실제로 필요해지면 별도 문서유형으로 추가한다(지금은 `Quote`에 문서유형 필드 없음, YAGNI).

PDF(`build_quote_pdf`)도 위탁계약형 엑셀과 동일 구성으로 재작성했다(아래 "개별 견적서 — PDF" 절
참고) — 셀 좌표가 아니라 reportlab Platypus 로 표현 가능한 동등 레이아웃(섹션 순서·항목 표 컬럼·
직인 위치·조건 문구 굵게 처리)으로 맞췄다. 양식/문구 상수는 `config.py` 한 곳(`COMPANY`,
`COMPANY_BIZ_LINES`, `MGMT_NO_DISPLAY_PREFIX`, `QUOTE_VALIDITY_NOTE`, `QUOTE_AUTHOR_TEAM/ROLE`,
`QUOTE_RECIPIENT_HONORIFIC`, `QUOTE_GREETING(_LINES)`, `QUOTE_CONDITION_LINES`, `SEAL_PATH`,
`SEAL_MM`)에 격리 — 협의로 확정되면 이 블록만 고친다(엑셀·PDF 둘 다 동시 반영됨).

## 로고 (`config.LOGO_PATH` → `backend/app/assets/sotec-logo.png`)

- **개별 견적서 엑셀(`build_quote_xlsx`)에는 로고를 넣지 않는다** — 원본 `견적서_위탁계약용.xlsx`
  에 로고 영역 자체가 없다(견적NO 라벨이 상단을 차지). 목록 엑셀(`build_list_xlsx`)과 PDF(옛
  SW형 레이아웃 유지 중)는 기존대로 로고를 넣는다.
- 목록 엑셀은 파일이 없거나 Pillow 미설치로 삽입이 실패해도 `_add_logo` 가 로고 없이 건너뛰고
  export 자체는 계속 성공한다. PDF 는 `LOGO_PATH` 가 없으면 `<Image>` 자체를 생략한다.
- 프론트 쪽 동일 로고: `frontend/src/assets/sotec-logo.png`(전체 로고, 헤더·로그인 화면),
  `sotec-mark.png`(단독 마크, 파비콘).

## 직인 (`config.SEAL_PATH` → `backend/app/assets/sotec-seal.png`, `config.SEAL_MM`)

- `status == APPROVED` 인 개별 견적서 export(엑셀·PDF)에만 공급자 **대표자명 옆**에 직인을 합성한다.
- 현재 파일은 `scripts/make_seal.py` 로 만든 **임시 "SOTEC" 직인**. 실제 직인이 오면 같은 경로에
  파일만 덮어쓰면 된다(정사각 PNG면 크기 무관 — 출력 시 `SEAL_MM` 한 변 길이로 정규화).
- 로고와 동일 방침: 파일 없음/ Pillow 미설치여도 export 는 직인 없이 계속 성공.

## 견적NO 표기 (`services/numbering.py: format_mgmt_no_display`)

- 저장 `mgmt_no`(`26-B-008`)·채번 로직은 불변. export 표시만 `혁신 2026-B 008` 형식
  (`{MGMT_NO_DISPLAY_PREFIX} {YYYY}-{그룹} {순번3자리}`). 그룹별 독립 채번.
- `MGMT_NO_DISPLAY_PREFIX`("혁신")는 전역 고정값 — 원본 위탁/기성계약용 샘플은 부서마다
  다른 접두어("혁신"/"의장")를 쓰지만, 지금은 이 팀만 발행하므로 미정(provisional) 항목으로
  남기고 전역 상수 그대로 둔다(협의되면 `tech/10-provisional-decisions.md` 갱신).
- 개별 견적서 엑셀은 표시를 두 셀로 나눠 넣는다: `{접두어} {YYYY}-{그룹}` + `{순번3자리}`
  (`mgmt_no_display.rsplit(" ", 1)`) — 원본 위탁계약용 샘플의 R2 배치 그대로.

## 개별 견적서 — 엑셀 (`services/export_excel.py: build_quote_xlsx`)

- openpyxl `Workbook`, 시트 1개 "견적서", 눈금선 숨김, 열 A~N(A열은 여백, 본문 B~N —
  `견적서_위탁계약용.xlsx` 그대로). 항목 표 앞까지는 **견적서마다 동일한 고정 행 번호**,
  항목 표는 실제 항목 수만큼만 늘어난다(원본은 16~33행 고정 18행이지만 빈 줄을 그대로
  옮기지 않고 동적으로 생성 — 항목 표 아래 합계 블록 위치도 그만큼 따라 움직인다).
- 셀 배치(1-based 행 번호):
  1. R2 — B2:J2 "견     적     서"(26pt) / K2:L2 "견적NO" 라벨 / M2·N2 각각 `{접두어 YYYY-그룹}`·`{순번}`.
  2. R3~R9 좌(견적 기본정보+수신처) / 우(공급자, G3:G9 세로 병합 "공급자" 라벨):
     - R3: 견적일자(B3 라벨+C3 값) · 견적유효일(D3:F3, 라벨+값 한 셀) / 등록번호(H3:I3 라벨·J3:N3 값).
     - R4: 고객사명(B4:C4) · 부서명(D4:F4) / 상호(H4:I4 라벨·J4 값) · 대표자(K4 라벨·L4:N4 값,
       **APPROVED 시 L4 옆에 직인**).
     - R5: (B5:C5 공란) · 담당자명(D5:E5, 직함 포함 자유텍스트) · 귀하(F5, 담당자 있을 때만) /
       주소(H5:I5 라벨·J5:N5 값).
     - R6~R8: C.C(B6:F6, `"C.C {customer_cc}"`, 값 없으면 공란) · (B7:F7 인사말 마지막 줄
       `QUOTE_GREETING`) · (B8/B9:F8/F9 공란) / 업태·종목 3행(H6:I8·K6:K8 세로 병합 라벨,
       `config.COMPANY_BIZ_LINES` 3쌍을 J6~J8·L6:N6~L8:N8 각 행에).
     - R9: 전화번호(H9:I9 라벨·J9 값) · FAX(K9 라벨·L9:N9 값).
  3. R10 G10:N10 — "견적 작성처 정보 : `{QUOTE_AUTHOR_TEAM} {그룹명} / {issuer_name} {QUOTE_AUTHOR_ROLE}`".
  4. R11~R12 인사말 2줄(`QUOTE_GREETING_LINES`), B:N 병합.
  5. R13 합계금액 박스 — B13:D13 라벨 / E13:J13 **한글 금액 표기**
     (`services/calculation.korean_amount_words`, `"일금  {말}원정"`) / K13:N13 `"(₩{금액:,})"`.
  6. R15 항목 표 헤더(B15:D15 용역(계약) · E15:H15 용역(계약) 기간 · I15:J15 공급가액 ·
     K15:L15 세액 · M15:N15 비고) — R16부터 항목 수만큼: 이름(B:D) · 기간 시작(E, `YYYY.MM.DD`)
     · `~`(F, 기간 있을 때만) · 기간 종료(G:H) · **공급가액 직접입력**(I:J, = `line_amount`,
     수량×단가 아님 — 항목 스키마는 `qty`/`unit_price` 그대로 쓰되 등록 폼이 `qty=1` 고정으로
     보내 `unit_price`가 곧 공급가액이 된다) · 세액(K:L, `round(공급가액×0.1)`, 참고용 — 합계
     세액은 절사된 공급가액 기준으로 별도 계산) · 비고(M:N, 공란).
  7. 합계 블록(항목 표 바로 아래, 빈 줄 없음) — 라벨 B:D·값 I:L·비고 M:N, 3행: 공급가액 합계
     (십만단위 절사, "원(십만단위절사)") / 세액(10%) / **합계금액**.
  8. 대금결제조건 / 납품조건 / WORK SCOPE / 납기(`QUOTE_CONDITION_LINES`, 번호·들여쓰기 포함
     원본 그대로 5줄) — 각 줄 B:N 병합.
  9. **서명란(작성/검토/승인) 없음** — 원본에 없다.
- 금액 셀 `number_format = '#,##0"원"'`.
- 응답: `StreamingResponse`, `Content-Disposition: attachment; filename="<mgmt_no>.xlsx"`,
  MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

## 개별 견적서 — PDF (`services/export_pdf.py: build_quote_pdf`)

- **엑셀과 같은 워크북을 셀 그리드째로 그대로 그린다** — 엑셀 전용 별도 프로그램(LibreOffice
  등)으로 파일을 변환하는 게 아니라, `export_excel.build_quote_workbook(q)`(엑셀 export 와
  공유하는 워크북 생성 함수 — export_excel.py 참고)가 만든, 값이 채워진 openpyxl 워크시트를
  `export_pdf.py` 가 직접 좌표 계산해서 reportlab 캔버스에 그린다(`_render_workbook_pdf`).
  열 너비·행 높이·병합 범위·테두리·배경색·정렬·굵기(rich-text 부분굵게 포함)를 셀에서 그대로
  읽어 재현하므로, 라벨 문구·인사말·대금결제조건 문구·강조 규칙이 전부 "엑셀에 있는 그대로"다
  — 이전엔 이 문구들을 `config.py` 상수로 따로 옮겨 적어 엑셀이 바뀌면 PDF 도 손으로 맞춰야
  했는데(2026-09 상반기), 이제는 템플릿 파일만 바꾸면 PDF 도 자동으로 따라간다.
  - 페이지 배치는 템플릿의 인쇄 설정(`ws.page_margins`, "한 페이지에 맞추기") 그대로 반영해
    A4 안에 맞춘다(가로/세로 중 더 작은 배율로 축소, 확대는 하지 않음).
  - 엑셀은 항목별 세액·합계 블록(공급가액/세액/합계)·K13(₩표기)을 시트 수식(`=ROUND(...)`,
    `=ROUNDDOWN(...)`)으로 남겨 Excel 이 열 때 재계산하지만, PDF 는 수식 엔진이 없으므로 이
    값들만 `Quote`(이미 계산된 정본)에서 가져와 덮어써 그린다(`_value_overrides`) — 그 외
    모든 셀은 워크북 값을 그대로 사용.
  - APPROVED 견적서의 직인은 엑셀과 같은 위치 계산식(대표자 셀 `L4` 기준 `SEAL_MM`/
    `SEAL_OFFSET_X_MM`)으로 별도 그린다 — openpyxl 이 셀 그리드에 심어 둔 이미지 앵커를
    파싱하는 대신 같은 계산식을 재사용하는 편이 더 견고해서.
  - 한글 폰트는 여전히 `NanumGothic`(임베드) 로 대체된다 — 템플릿이 쓰는 "맑은 고딕"/"Noto
    Sans CJK SC" 파일은 이 저장소에 없다. 그래서 글자폭이 미세하게 달라 줄바꿈 위치 등이
    엑셀과 살짝 다를 수 있다(그 외 위치·구조·서식은 동일) — 이 트레이드오프는 사용자와
    협의된 것(그리드 렌더링 vs 실제 파일 변환/외부 API, DECISIONS.md 참고).
  - **알려진 한계**: 항목이 `QUOTE_TEMPLATE_ITEM_ROWS`(18) 을 초과해 `_extend_item_rows`
    가 `ws.insert_rows` 로 행을 늘리는 경로에서, openpyxl 의 병합 셀 처리 한계(삽입 시 기존
    병합 범위가 제대로 밀리지 않고 겹치는 경우가 있음 — openpyxl 자체가 알려진 제약사항)로
    새로 늘어난 항목 행의 세액이 비어 보이는 렌더링 버그가 있다. 엑셀 파일 자체의 병합
    데이터 문제라 PDF 만의 문제는 아니며, 이번 작업 범위 밖이라 별도로 다룬다
    (`tests/unit/test_export_pdf.py` 상단 주석에 기록).
- **reportlab**(`pdfgen.canvas`, `platypus.Paragraph` 로 셀 텍스트만) 로 직접 그린다 — HTML/CSS
  중간 표현 없음. 이전 구현(WeasyPrint, HTML→PDF)은 시스템 라이브러리(`libpango` 등)가 필요해
  Vercel Serverless 같은 서버리스 환경에서 동작하지 않아 reportlab(순수 파이썬)으로 교체
  (DECISIONS.md 참조) — 이번 재작성도 이 제약(네이티브 라이브러리 의존 없음)을 그대로 지킨다.
- A4, 한글 폰트: **`app/assets/fonts/NanumGothic-{Regular,Bold}.ttf` 를 PDF 안에 직접 임베드**
  (`pdfmetrics.registerFont(TTFont(...))`) — 실행 환경(OS)에 한글 폰트가 설치돼 있는지와 무관하게
  항상 동일하게 렌더링된다. 시스템 라이브러리·시스템 폰트 의존성 전부 없음.
- 응답: `application/pdf`, `attachment; filename="<mgmt_no>.pdf"`.
- PDF 는 **서버가 렌더링**해서 바이트로 응답하므로, 사용자 PC/브라우저의 OS·폰트와는 무관하다.
- reportlab import/폰트 파일 로드 실패 대비: 실패 시 `501 {code:"PDF_UNAVAILABLE"}` 반환하고 서버는 계속 동작
  (순수 파이썬이라 정상 설치 환경에서는 거의 발생하지 않음 — 폰트 자산 파일이 삭제된 경우 등 방어용).

## 목록 — 엑셀 (`build_list_xlsx`)

- 현재 목록 필터/스코프 그대로 적용해 전체 결과(페이지네이션 무시) 추출.
- 좌상단 로고 → 헤더 행 → 데이터.
- 컬럼: 관리번호, 그룹코드, 그룹명, 견적서명, 수신처, 발행일자, 발행담당자, 공급가액, 부가세, 부가세포함가, 부가세포함여부, 상태, 잠금여부, 등록시간.
- filename: `quotes_YYYYMMDD_HHMM.xlsx`.

## 목록 — PDF

- **미지원** (의도된 설계, [PRODUCT 04](../product/04-scenarios.md) 4.8). 엔드포인트 없음.
