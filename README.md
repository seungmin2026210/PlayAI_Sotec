# SW 자산 견적서 관리 시스템 (QUOTE-1, 1단계)

바탕화면 `기획서.md.md` v1.1 의 **1단계: 견적서 관리** 구현체.

- 스펙(섹션별 분할): [`specs/QUOTE-1/PRODUCT.md`](specs/QUOTE-1/PRODUCT.md), [`specs/QUOTE-1/TECH.md`](specs/QUOTE-1/TECH.md)
- 결정 로그: [`specs/QUOTE-1/DECISIONS.md`](specs/QUOTE-1/DECISIONS.md)
- 미정(❓) 항목 → 임시 결정 대응표: [`specs/QUOTE-1/tech/10-provisional-decisions.md`](specs/QUOTE-1/tech/10-provisional-decisions.md)

## 스택

| 레이어 | 기술 |
|---|---|
| 프론트 | React 18 + TypeScript + Vite |
| 백엔드 | FastAPI + SQLAlchemy 2 |
| DB | PostgreSQL 15 |
| Export | openpyxl (엑셀), WeasyPrint (PDF) |

## 실행

### 1) PostgreSQL

```bash
docker compose up -d db     # quote / quote_test DB 자동 생성
```

Docker가 없으면 로컬 PostgreSQL에 `quote`, `quote_test` DB와 `quote/quote` 계정을 직접 만든 뒤
`backend/.env` 의 `DATABASE_URL` 을 맞춘다.

### 2) 백엔드

```bash
cd backend
py -3 -m venv .venv
.venv\Scripts\activate            # (bash: source .venv/Scripts/activate)
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python seed.py                    # 데모 견적서 3건
uvicorn app.main:app --reload --port 8000
```

- API 문서: http://localhost:8000/docs

> WeasyPrint(PDF)는 시스템 GTK 라이브러리가 필요하다. 미설치 환경에서는 PDF 엔드포인트가
> `501 PDF_UNAVAILABLE` 을 반환하고 나머지 기능은 정상 동작한다. 엑셀 export 는 의존성 없음.

### 3) 프론트엔드

```bash
cd frontend
npm install
npm run dev                       # http://localhost:5173 (API 는 :8000 으로 프록시)
```

## 데모 계정 (기획서 3.3)

| ID | PW | 역할 | 범위 |
|---|---|---|---|
| `Admin` | `1234` | 전체관리자 | 전체 그룹 CRUD·승인·반려 |
| `test1` | `1234` | 그룹관리자 | A그룹 **조회 전용** (임시, open-2) |

계정 정의는 `backend/app/config.py` `ACCOUNTS` 한 곳. 실사용 전환 시 개별 계정을 여기에 추가.

## 테스트 (백엔드)

PostgreSQL(`quote_test`)이 떠 있어야 한다.

```bash
cd backend
.venv\Scripts\activate
pytest                            # 27 tests: 계산 / 채번 / 상태전이 / 권한 / 통합흐름
```

프론트: `cd frontend && npm run typecheck && npm run build`

## 구현 범위

포함 (기획서 2.1): 견적서 등록·수정·취소·삭제 / 승인·반려 / 관리번호 자동 채번(동시성 제어) /
십만단위 절사·부가세 계산 / 역할 기반 조회 분리 / 개별 엑셀·PDF, 목록 엑셀 export /
발송 버튼(자리표시) / 구매관리 반영 잠금(자리표시).

범위 외: 실제 인증 연동, SMTP 발송, 구매관리 실연동, 예산·갱신캘린더·자산배정이력, 감사로그 UI.
자세한 미정 항목 처리는 `specs/QUOTE-1/DECISIONS.md` 참고.
