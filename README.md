# SW 자산 견적서 관리 시스템 (QUOTE-1, 1단계)

바탕화면 `기획서.md.md` v1.1 의 **1단계: 견적서 관리** 구현체.

- 스펙(섹션별 분할): [`specs/QUOTE-1/PRODUCT.md`](specs/QUOTE-1/PRODUCT.md), [`specs/QUOTE-1/TECH.md`](specs/QUOTE-1/TECH.md)
- 결정 로그: [`specs/QUOTE-1/DECISIONS.md`](specs/QUOTE-1/DECISIONS.md)
- Firestore 마이그레이션 설계·경합 실측: [`specs/QUOTE-1/tech/12-firestore-migration.md`](specs/QUOTE-1/tech/12-firestore-migration.md)
- 미정(❓) 항목 → 임시 결정 대응표: [`specs/QUOTE-1/tech/10-provisional-decisions.md`](specs/QUOTE-1/tech/10-provisional-decisions.md)

## 스택

| 레이어 | 기술 |
|---|---|
| 프론트 | React 18 + TypeScript + Vite |
| 백엔드 | FastAPI |
| DB | Firebase Firestore (로컬은 에뮬레이터) |
| Export | openpyxl(엑셀) / reportlab(PDF, 순수 파이썬 — 시스템 라이브러리 불필요) |
| 배포 | Vercel(프론트+백엔드) + Firebase(Firestore) |

## 실행

### 1) Firestore 에뮬레이터

```bash
npx firebase-tools emulators:start --only firestore --project demo-quote   # :8090
```

Java 런타임이 필요하다(`brew install openjdk`, macOS는 `/opt/homebrew/opt/openjdk/bin`을 PATH에 추가).
첫 실행은 에뮬레이터 jar 다운로드로 조금 느리다. 포트/프로젝트는 `firebase.json` 참고.

### 2) 백엔드

```bash
cd backend
py -3 -m venv .venv
.venv\Scripts\activate            # (bash: source .venv/Scripts/activate)
pip install -r requirements.txt
copy .env.example .env            # FIRESTORE_EMULATOR_HOST=127.0.0.1:8090 주석 해제(로컬 개발)
python seed.py                    # 데모 견적서 3건 (--reset 로 초기화)
uvicorn app.main:app --reload --port 8000
```

- API 문서: http://localhost:8000/docs
- PDF export는 reportlab(순수 파이썬) + `app/assets/fonts/` 임베드 한글 폰트라 시스템 의존성 없이 동작한다(Vercel Serverless 포함). import/렌더 실패 시에만 `501 PDF_UNAVAILABLE`을 반환하고 나머지 기능은 정상 동작한다. 엑셀 export도 의존성 없음.
- 실제 Firestore(배포)에 붙일 땐 `.env`의 `FIRESTORE_EMULATOR_HOST`를 지우고 `GOOGLE_APPLICATION_CREDENTIALS`(서비스 계정 키 경로)를 설정한다(`tech/12-firestore-migration.md` § 9).

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

Firestore 에뮬레이터가 떠 있어야 DB 관련 테스트까지 실행된다(미기동 시 해당 테스트만 skip, `tests/unit/`은 항상 실행).

```bash
npx firebase-tools emulators:start --only firestore --project demo-quote &
cd backend
.venv\Scripts\activate
pytest                            # 32 tests: 계산 / 채번 / 상태전이 / 권한 / 통합흐름 / export
```

프론트: `cd frontend && npm run typecheck && npm run build`

## 구현 범위

포함 (기획서 2.1): 견적서 등록·수정·취소·삭제 / 승인·반려 / 관리번호 자동 채번(동시성 제어) /
십만단위 절사·부가세 계산 / 역할 기반 조회 분리 / 개별 엑셀·PDF, 목록 엑셀 export /
승인된 견적서 읽기전용화 / 발송 버튼(자리표시) / 구매관리 반영 잠금(자리표시).

범위 외: 실제 인증 연동, SMTP 발송, 구매관리 실연동, 예산·갱신캘린더·자산배정이력, 감사로그 UI,
반려↔재제출 참조 필드. 자세한 미정 항목 처리는 `specs/QUOTE-1/DECISIONS.md` 참고.
