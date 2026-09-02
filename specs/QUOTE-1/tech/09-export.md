# 09. Export 구현

개별 견적서(엑셀·PDF)는 **실제 견적서.jpg 양식**을 따른다. 양식/문구 상수는
`config.py` 한 곳(`COMPANY`, `MGMT_NO_DISPLAY_PREFIX`, `QUOTE_VALIDITY_NOTE`,
`QUOTE_AUTHOR_TEAM/ROLE`, `QUOTE_GREETING(_LINES)`, `QUOTE_CONDITIONS`,
`QUOTE_SIGNOFF_COLS`, `SEAL_PATH`, `SEAL_MM`)에 격리 — 협의로 확정되면 이 블록만 고친다.

## 로고 (`config.LOGO_PATH` → `backend/app/assets/sotec-logo.png`)

- 모든 export(개별 엑셀/PDF, 목록 엑셀) 상단에 자사 로고를 삽입한다.
- 파일이 없거나(개발 환경 등) 엑셀의 경우 Pillow 미설치로 삽입이 실패해도 export 자체는
  계속 성공해야 한다 — `export_excel._add_logo` 는 실패 시 로고 없이 조용히 건너뛰고,
  PDF 는 `_LOGO_DATA_URI` 가 빈 문자열이면 `<img>` 태그 자체를 생략한다.
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

## 개별 견적서 — 엑셀 (`services/export_excel.py: build_quote_xlsx`)

- openpyxl `Workbook`, 시트 1개 "견적서", 눈금선 숨김, 열 A~I.
- 레이아웃(위→아래):
  1. 좌상단 로고 → "견 적 서" 제목.
  2. 좌: 견적일자 / 견적유효기간 / 견적 NO(표시형식). 우: 공급자 박스(등록번호·상호·**대표자(+직인)**·주소·업태/종목·전화/FAX·견적 작성자[`팀명 + 그룹명 / 역할`]).
  3. 수신처: 고객사명 / 담당자(이름·연락처) / C.C(공란).
  4. 인사말(`QUOTE_GREETING` + 번호 문구).
  5. 합계금액(공급가액+세액) 요약 박스.
  6. 용역(계약)명(= `title`) / 용역(계약) 기간(공란).
  7. 항목 표 8열: No · 품목 · **규격(공란)** · 수량 · 단가 · 공급가액 · **세액(`round(금액×0.1)`)** · **비고(공란)**.
  8. 합계 블록: 공급가액 합계(십만단위 절사) / 세액(10%) / **합계금액**. 아래 주석에 항목 합계·절사 기준·부가세 포함여부.
  9. 대금결제조건 / 납품조건 / WORK SCOPE (`QUOTE_CONDITIONS`).
  10. 우측 서명란(`QUOTE_SIGNOFF_COLS` = 작성·검토·승인).
- 금액 셀 `number_format = '#,##0"원"'`.
- 응답: `StreamingResponse`, `Content-Disposition: attachment; filename="<mgmt_no>.xlsx"`,
  MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

## 개별 견적서 — PDF (`services/export_pdf.py: build_quote_pdf`)

- Jinja 없이 f-string HTML 템플릿 → `weasyprint.HTML(string=...).write_pdf()`.
- 엑셀과 **동일한 양식/섹션/문구**(공급자·수신처 2단, 인사말, 합계금액 박스, 항목 8열, 합계 블록, 조건, 서명란). APPROVED 는 공급자 블록에 직인 `<img>` 합성.
- A4, 한글 폰트: 시스템 `Malgun Gothic`(Windows) / fallback `sans-serif`.
- 응답: `application/pdf`, `attachment; filename="<mgmt_no>.pdf"`.
- Windows: `weasyprint` import 전에 표준 GTK3 런타임 경로(`C:\Program Files\GTK3-Runtime Win64\bin`)가
  있으면 `PATH` 앞에 얹는다. 설치: `winget install tschoonj.GTKForWindows`.
- WeasyPrint 미설치/GTK 이슈 환경 대비: import/렌더 실패 시 `501 {code:"PDF_UNAVAILABLE"}` 반환하고 서버는 계속 동작.

## 목록 — 엑셀 (`build_list_xlsx`)

- 현재 목록 필터/스코프 그대로 적용해 전체 결과(페이지네이션 무시) 추출.
- 좌상단 로고 → 헤더 행 → 데이터.
- 컬럼: 관리번호, 그룹코드, 그룹명, 견적서명, 수신처, 발행일자, 발행담당자, 공급가액, 부가세, 부가세포함가, 부가세포함여부, 상태, 잠금여부, 등록시간.
- filename: `quotes_YYYYMMDD_HHMM.xlsx`.

## 목록 — PDF

- **미지원** (의도된 설계, [PRODUCT 04](../product/04-scenarios.md) 4.8). 엔드포인트 없음.
