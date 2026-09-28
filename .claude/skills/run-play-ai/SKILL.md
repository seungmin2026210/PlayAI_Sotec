---
name: run-play-ai
description: Play_AI(QUOTE-1/PURCHASE-1/ASSET-1) 프로젝트를 로컬에서 실행/테스트하는 방법 — Firestore 에뮬레이터, 백엔드(FastAPI/uvicorn), 프론트엔드(Vite) 기동, pytest 실행. "프로젝트 실행해줘", "테스트 돌려줘", "백엔드/프론트 켜줘" 같은 요청에 사용.
---

## 명령

### DB (Firestore 에뮬레이터)
```bash
npx firebase-tools emulators:start --only firestore --project demo-quote   # :8090
```
Java 런타임 필요(`brew install openjdk`, macOS는 `/opt/homebrew/opt/openjdk/bin`을 PATH에 추가). 첫 실행은 에뮬레이터 jar 다운로드로 조금 느림. 포트/프로젝트는 `firebase.json` 참고.

### 백엔드
```bash
cd backend
py -3 -m venv .venv && .venv\Scripts\activate      # bash: source .venv/Scripts/activate
pip install -r requirements.txt
copy .env.example .env    # FIRESTORE_EMULATOR_HOST=127.0.0.1:8090 주석 해제(로컬 개발)
python seed.py                    # 데모 견적서 3건 (--reset 로 초기화)
uvicorn app.main:app --reload --port 8000          # /docs 에 API 문서
```
- PDF export: reportlab(순수 파이썬) + `app/assets/fonts/` 임베드 폰트라 OS/시스템 라이브러리 무관하게 동작(Vercel Serverless 포함). 실패 시에만 `501 PDF_UNAVAILABLE`.
- 임시 직인 재생성(문구/크기 변경 시): `py -3 ../scripts/make_seal.py`. 실제 직인은 `backend/app/assets/sotec-seal.png` 교체.
- 실제 Firestore(배포)에 붙일 땐 `.env`의 `FIRESTORE_EMULATOR_HOST` 를 지우고 `GOOGLE_APPLICATION_CREDENTIALS`(서비스 계정 키 경로)를 설정(12-firestore-migration.md § 9).
- 자산 계정 비밀번호 저장/열람엔 `.env` 의 `ASSET_SECRET_KEY`(Fernet 키, 생성법은 `.env.example`) 필요. 없으면 비밀번호가 포함된 요청만 `501 SECRET_KEY_MISSING`. **키를 잃으면 저장된 비밀번호 복구 불가** — 배포 키는 따로 백업.

### 프론트엔드
```bash
cd frontend
npm install
npm run dev                       # :5173, /api → :8000 프록시
npm run typecheck                 # tsc --noEmit
npm run build                     # tsc && vite build
```

### 테스트
```bash
npx firebase-tools emulators:start --only firestore --project demo-quote &   # 미기동 시 DB 테스트는 skip
cd backend && .venv\Scripts\activate
pytest                            # 101 tests (자산관리: tests/test_assets.py, tests/unit/test_asset_rules.py).
```
- `conftest.py` 가 `FIRESTORE_EMULATOR_HOST`(기본 `127.0.0.1:8090`) 로 접속, 매 테스트 전 `quotes`/`number_sequences`/`retired_numbers` 문서를 전부 지운다(TRUNCATE 대응). 에뮬레이터 미기동 시 연결 실패로 DB 테스트는 skip, `tests/unit/` 만 실행.
- 계산/채번 로직만 빠르게 확인: `python -c "from app.services.calculation import compute; ..."` (DB 불필요, 순수 함수)
