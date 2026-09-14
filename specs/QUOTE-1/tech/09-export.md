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

PDF(`build_quote_pdf`)는 **이번 범위 밖**(엑셀 확정 후 별도 작업) — 레이아웃은 옛 SW형 그대로고
문구 상수만 새 값을 그대로 물려받는다(아래 "개별 견적서 — PDF" 절 참고). 양식/문구 상수는
`config.py` 한 곳(`COMPANY`, `COMPANY_BIZ_LINES`, `MGMT_NO_DISPLAY_PREFIX`, `QUOTE_VALIDITY_NOTE`,
`QUOTE_AUTHOR_TEAM/ROLE`, `QUOTE_RECIPIENT_HONORIFIC`, `QUOTE_GREETING(_LINES)`,
`QUOTE_CONDITION_LINES`, `SEAL_PATH`, `SEAL_MM`)에 격리 — 협의로 확정되면 이 블록만 고친다.

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

## 개별 견적서 — PDF (`services/export_pdf.py: build_quote_pdf`) — 이번 범위 밖

- **레이아웃은 옛 SW 품목형 그대로 유지 중** — 위탁계약형 엑셀이 확정된 뒤 별도 작업으로
  재작성한다(그릴링 합의사항, 엑셀부터 먼저). 문구 상수(`QUOTE_GREETING(_LINES)`,
  `QUOTE_CONDITION_LINES`, `QUOTE_AUTHOR_ROLE` 등)는 위탁계약형 값을 그대로 물려받아
  내용은 새 문구가 나가지만, 섹션 구성(수량/단가/규격 열이 있는 8열 항목표, 서명란 등)은
  엑셀과 다르다 — 재작업 전까지 의도된 불일치.
- **reportlab**(Platypus: `Table`/`Paragraph`/`Image`) 로 직접 구성 — HTML/CSS 중간 표현 없음.
  이전 구현(WeasyPrint, HTML→PDF)은 시스템 라이브러리(`libpango` 등)가 필요해 Vercel Serverless
  같은 서버리스 환경에서 동작하지 않아 reportlab(순수 파이썬)으로 교체(DECISIONS.md 참조).
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
