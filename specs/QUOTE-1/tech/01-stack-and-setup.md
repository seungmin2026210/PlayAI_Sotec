# 01. 기술 스택 / 로컬 실행

> DB 는 PostgreSQL → **Firestore** 로 전환됨(배포: Vercel + Firebase). 상세·마이그레이션 경과는
> [`12-firestore-migration.md`](./12-firestore-migration.md). 아래는 전환 후 현재 스택.

## 스택 (open-9 확정 + Firestore 전환)

| 레이어 | 선택 | 비고 |
|---|---|---|
| 프론트엔드 | React 18 + TypeScript + Vite | React Router, 순수 fetch 래퍼 |
| 백엔드 | Python 3.13 + FastAPI | Pydantic v2, Uvicorn |
| DB | **Firestore** | `google-cloud-firestore`. 로컬/테스트는 에뮬레이터(`firebase-tools`) |
| 엑셀 | openpyxl + Pillow | 개별/목록. Pillow 는 로고 이미지 삽입용(미설치 시 로고 없이 export 계속 성공) |
| PDF | **reportlab**(순수 파이썬) | 개별 견적서. 한글 폰트 임베드, 시스템 라이브러리 의존 없음(Vercel Serverless 대응) |
| 테스트 | pytest + httpx TestClient | 백엔드 위주. DB 필요 테스트는 Firestore 에뮬레이터로 실행 |

> 인증은 시뮬레이션(범위 외). 실제 SSO/출퇴근 API 연동은 향후. Firestore 전환은 **DB 저장소만**
> 바꾼 것이고 Firebase Auth 는 쓰지 않는다.

## 디렉터리

```
backend/
  app/
    main.py            FastAPI 앱, 예외 핸들러, CORS
    config.py          상수 1곳: COMPANY, GROUPS, ACCOUNTS, VAT_RATE, ...
    database.py        Firestore Client 싱글턴 + run_transaction(재시도 헬퍼)
    models.py          Quote/QuoteItem dataclass (to_dict/from_doc)
    schemas.py         Pydantic 스키마
    deps.py            get_db, get_current_user, 권한 판정
    auth.py            로그인 시뮬레이션(토큰 발급/검증)
    errors.py          AppError + 코드 상수
    routers/
      auth.py  meta.py  quotes.py
    services/
      numbering.py     채번 (Firestore 트랜잭션)
      query.py         목록 조회(등호 필터 + 애플리케이션 레벨 텍스트/날짜 필터)
      calculation.py   절사/부가세/포맷
      status.py        상태 전이 가드 + apply_edit_policy
      export_excel.py  export_pdf.py
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
firebase.json  firestore.rules  firestore.indexes.json
```

## 로컬 실행

```bash
# 1) DB(Firestore 에뮬레이터)
npx firebase-tools emulators:start --only firestore --project demo-quote   # :8090

# 2) 백엔드
cd backend
python -m venv .venv && . .venv/Scripts/activate   # windows: .venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # FIRESTORE_EMULATOR_HOST=127.0.0.1:8090 주석 해제
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
| `FIREBASE_PROJECT_ID` | `quote-dev` | Firestore 프로젝트ID |
| `FIRESTORE_EMULATOR_HOST` | `127.0.0.1:8090` | 로컬/테스트 전용. 실제 Firestore 사용 시 이 줄 삭제 + `GOOGLE_APPLICATION_CREDENTIALS` 설정 |
| `CORS_ORIGINS` | `http://localhost:5173` | 콤마 구분 |
| `TOKEN_SECRET` | `dev-secret` | 시뮬레이션 토큰 서명용 |
| `TOKEN_TTL_HOURS` | `12` | 토큰 유효시간 |
