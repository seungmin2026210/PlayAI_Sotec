# 09. Export 구현

## 개별 견적서 — 엑셀 (`services/export_excel.py: build_quote_xlsx`)

- openpyxl `Workbook`, 시트 1개 "견적서".
- 레이아웃: 상단 자사 정보(사업자등록번호·대표자명·회사명) → 수신처 정보 → 견적서명/발행일자/담당자/관리번호/상태 → 항목 표(No, 품목, 갯수, 단가(공급가액), 금액) → 합계 블록(항목합계 / 공급가액(절사) / 부가세 / 부가세 포함가) → 부가세 포함/미포함 표기.
- 금액 셀 `number_format = '#,##0"원"'`.
- 응답: `StreamingResponse`, `Content-Disposition: attachment; filename="<mgmt_no>.xlsx"`,
  MIME `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`.

## 개별 견적서 — PDF (`services/export_pdf.py: build_quote_pdf`)

- Jinja 없이 f-string HTML 템플릿 → `weasyprint.HTML(string=...).write_pdf()`.
- 동일 정보 레이아웃, A4, 한글 폰트: 시스템 `Malgun Gothic` (Windows) / fallback `sans-serif`.
- 응답: `application/pdf`, `attachment; filename="<mgmt_no>.pdf"`.
- WeasyPrint 미설치/GTK 이슈 환경 대비: import 실패 시 `501 {code:"PDF_UNAVAILABLE"}` 반환하고 서버는 계속 동작.

## 목록 — 엑셀 (`build_list_xlsx`)

- 현재 목록 필터/스코프 그대로 적용해 전체 결과(페이지네이션 무시) 추출.
- 컬럼: 관리번호, 그룹코드, 그룹명, 견적서명, 수신처, 발행일자, 발행담당자, 공급가액, 부가세, 부가세포함가, 부가세포함여부, 상태, 잠금여부, 등록시간.
- filename: `quotes_YYYYMMDD_HHMM.xlsx`.

## 목록 — PDF

- **미지원** (의도된 설계, [PRODUCT 04](../product/04-scenarios.md) 4.8). 엔드포인트 없음.
