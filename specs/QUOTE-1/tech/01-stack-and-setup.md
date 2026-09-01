# 01. 기술 스택 / 로컬 실행

## 스택 (open-9 확정)

| 레이어 | 선택 | 비고 |
|---|---|---|
| 프론트엔드 | React 18 + TypeScript + Vite | React Router, 순수 fetch 래퍼 |
| 백엔드 | Python 3.11 + FastAPI | Pydantic v2, Uvicorn |
| ORM | SQLAlchemy 2.x | 동기 세션 |
| 마이그레이션 | Alembic | 초기 리비전 1개 + seed 스크립트 |
| DB | PostgreSQL 15 | `docker-compose`로 로컬 기동 |
| 엑셀 | openpyxl + Pillow | 개별/목록. Pillow 는 로고 이미지 삽입용(미설치 시 로고 없이 export 계속 성공) |
| PDF | WeasyPrint (HTML→PDF) | 개별 견적서 |
| 테스트 | pytest + httpx TestClient | 백엔드 위주 |

> 인증은 시뮬레이션(범위 외). 실제 SSO/출퇴근 API 연동은 향후.

## 디렉터리

```
backend/
  app/
    main.py            FastAPI 앱, 예외 핸들러, CORS
    config.py          상수 1곳: COMPANY, GROUPS, ACCOUNTS, VAT_RATE, ...
    database.py        엔진/세션
    models.py          SQLAlchemy 모델
    schemas.py         Pydantic 스키마
    deps.py            get_db, get_current_user, 권한 판정
    auth.py            로그인 시뮬레이션(토큰 발급/검증)
    errors.py          AppError + 코드 상수
    routers/
      auth.py  meta.py  quotes.py
    services/
      numbering.py     채번 (FOR UPDATE)
      calculation.py   절사/부가세/포맷
      status.py        상태 전이 가드 + apply_edit_policy
      export_excel.py  export_pdf.py
  alembic/  (env.py, versions/0001_init.py)
  seed.py
  tests/
  requirements.txt
  .env.example
frontend/
  src/
    api/client.ts  api/quotes.ts  api/auth.ts
    lib/money.ts   lib/vat.ts
    pages/  Login  QuoteList  QuoteDetail  QuoteForm
    components/  ItemsEditor  StatusBadge  Toast  RoleGate
    auth.tsx  App.tsx  main.tsx
  index.html  vite.config.ts  package.json
docker-compose.yml
```

## 로컬 실행

```bash
# 1) DB
docker compose up -d db

# 2) 백엔드
cd backend
python -m venv .venv && . .venv/Scripts/activate   # windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python seed.py
uvicorn app.main:app --reload --port 8000

# 3) 프론트
cd frontend
npm install
npm run dev   # http://localhost:5173, API 프록시 → :8000
```

## 환경변수 (`backend/.env`)

| 키 | 예시 | 설명 |
|---|---|---|
| `DATABASE_URL` | `postgresql+psycopg://quote:quote@localhost:5432/quote` | PostgreSQL 접속 |
| `CORS_ORIGINS` | `http://localhost:5173` | 콤마 구분 |
| `TOKEN_SECRET` | `dev-secret` | 시뮬레이션 토큰 서명용 |
| `TOKEN_TTL_HOURS` | `12` | 토큰 유효시간 |
