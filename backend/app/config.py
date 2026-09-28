"""
전역 상수 및 설정 — 계정 / 그룹 / 자사정보 / 계산 상수의 **유일한 정의처**.

기획서 3.3: "계정 정보(ID/PW/역할/소속 그룹 매핑)는 상수 파일 1곳에만 정의하고
코드 곳곳에 흩뿌리지 않음." 개별 계정으로 늘어나도 이 파일에만 추가한다.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Firestore. 로컬/테스트는 FIRESTORE_EMULATOR_HOST 환경변수만 있으면 이 프로젝트ID로도
    # 에뮬레이터에 붙는다(인증 불필요, google-cloud-firestore 가 해당 변수를 자동 인식).
    # 배포(실제 Firestore) 시엔 이 값을 실제 Firebase 프로젝트ID로, 서비스 계정 인증정보는
    # GOOGLE_APPLICATION_CREDENTIALS(파일 경로) 또는 GOOGLE_APPLICATION_CREDENTIALS_JSON
    # (Vercel 환경변수, 내용 그대로)으로 준다. 12-firestore-migration.md § 9.
    firebase_project_id: str = "quote-dev"
    # .env 로만 지정 가능(pydantic-settings 는 .env 를 os.environ 에 반영하지 않으므로
    # database.get_client() 가 이 값을 읽어 직접 os.environ 에 넣어준다).
    firestore_emulator_host: str | None = None
    cors_origins: str = "http://localhost:5173"
    token_secret: str = "dev-secret-change-me"
    token_ttl_hours: int = 12
    # ASSET-1 비밀번호 암호화(Fernet) 키. 코드·저장소에 두지 않는다 — 환경변수 ASSET_SECRET_KEY.
    # 없으면 비밀번호가 포함된 요청만 501 SECRET_KEY_MISSING(services/asset_secret.py).
    asset_secret_key: str | None = None

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()

# ---------------------------------------------------------------------------
# 역할
# ---------------------------------------------------------------------------
ROLE_SUPER_ADMIN = "SUPER_ADMIN"      # 전체관리자
ROLE_GROUP_MANAGER = "GROUP_MANAGER"  # 그룹관리자 (조회 전용, open-1)

# ---------------------------------------------------------------------------
# 그룹 (기획서 3.2, 데모 기준)
# ---------------------------------------------------------------------------
GROUPS: dict[str, str] = {
    "A": "기술개발그룹",
    "B": "스마트개발그룹",
    "C": "설계시스템개발그룹",
    "D": "ADX개발그룹",
    "E": "DT개발그룹",
}
GROUP_CODES = tuple(GROUPS.keys())

# ---------------------------------------------------------------------------
# 계정 (기획서 3.3) — 개발/테스트용 하드코딩. 실사용 전환 시 개별 계정을 여기에 추가.
#   - 계정 공유 금지(운영 규칙). 승인/반려/수정 주체가 실제 인물로 식별되어야 함.
# ---------------------------------------------------------------------------
ACCOUNTS: dict[str, dict] = {
    "Admin": {
        "password": "1234",
        "role": ROLE_SUPER_ADMIN,
        "group_code": None,               # 전체(그룹 제한 없음)
        "display_name": "전체관리자",      # 실명 대신 역할 라벨 (배포 범위 확정 시 교체 — open, PRODUCT 03 주석)
    },
    "test1": {
        "password": "1234",
        "role": ROLE_GROUP_MANAGER,
        # open-2 미정: 임시로 A 그룹 지정. 협의 후 확정.
        "group_code": "A",
        "display_name": "그룹관리자(A)",
    },
}

# ---------------------------------------------------------------------------
# 자사(발행자) 고정 정보 (기획서 5장: 자동 반영, 수정 불가)
#   실제 견적서.jpg 기준 실사값. 변경 시 이 dict 1곳만 수정.
# ---------------------------------------------------------------------------
COMPANY: dict[str, str] = {
    "name": "쏘테크(주)",
    "biz_no": "612-81-23163",       # 사업자등록번호
    "ceo_name": "선인규",
    "address": "경남 거제 장평3로 75",
    "tel": "055-630-1263",
    "fax": "055-631-5286",
    "biz_type": "정보통신업",                        # 업태 (단일값 참고용 — 출력물은 COMPANY_BIZ_LINES 사용)
    "biz_item": "응용 소프트웨어 개발 및 공급업",     # 종목 (위와 동일)
}
# 견적서 출력물의 업태/종목 3행 — 실사업자등록증 기준 복수 등록 업태·종목
# (`견적서_위탁계약용.xlsx` H6:I8/K6:K8~L8 전사). 순서 고정.
COMPANY_BIZ_LINES: tuple[tuple[str, str], ...] = (
    ("서비스", "선박임가공"),
    ("정보통신업", "응용 소프트웨어 개발 및 공급업"),
    ("서비스", "기술검사"),
)

# PDF/엑셀 견적서 출력물에 삽입하는 자사 로고. 파일 없으면 각 export 서비스가
# 조용히 로고 없이 출력한다(PDF_UNAVAILABLE 과 동일하게 export 자체는 항상 성공).
# 개별 견적서 엑셀(`build_quote_xlsx`)은 `견적서_위탁계약용.xlsx` 원본에 로고 영역이
# 없어 로고를 넣지 않는다 — 목록 엑셀(`build_list_xlsx`)에서만 사용.
LOGO_PATH: Path = Path(__file__).resolve().parent / "assets" / "sotec-logo.png"

# 개별 견적서 엑셀의 원본 템플릿 — 바탕화면 `견적서_위탁계약용.xlsx` 를 셀 단위(서식·
# 병합·테두리·폰트) 그대로 커밋해 둔 것. `build_quote_xlsx` 는 이 파일을 열어 값만
# 채워 넣는다(스타일을 코드로 재현하지 않음 — 재현 시 폰트/테두리가 원본과 미묘하게
# 달라지는 문제가 있었다, tech/09-export.md). 실제 양식이 바뀌면 이 파일만 교체한다.
QUOTE_TEMPLATE_PATH: Path = Path(__file__).resolve().parent / "assets" / "quote_template_consignment.xlsx"
QUOTE_TEMPLATE_SHEET = "위탁견적서"
QUOTE_TEMPLATE_ITEM_ROWS = 18  # 템플릿이 미리 서식을 잡아둔 항목 행 수(R16~R33)

# 승인(APPROVED) 견적서 export 에 대표자명 옆에 합성하는 직인.
#   현재는 scripts/make_seal.py 로 만든 임시 "SOTEC" 직인. 실제 직인이 오면
#   같은 경로에 파일만 교체하면 된다(크기가 달라도 SEAL_MM 으로 흡수).
SEAL_PATH: Path = Path(__file__).resolve().parent / "assets" / "sotec-seal.png"
SEAL_MM: float = 22.0            # 출력물에서 직인 한 변 길이(mm). 실제 직인 비율에 맞게 조정.
# 대표자명 셀(L4, 병합 L4:N4)에 "{대표자명} (인)"이 가운데정렬로 들어가 있어, 셀
# 왼쪽 끝에 그대로 합성하면 이름 위에 겹친다 — "(인)" 글자 쪽으로 밀기 위한 가로
# 오프셋(mm). 대표자명 길이가 바뀌면(글자 수 등) 눈대중으로 같이 조정해야 하는
# 값이라 SEAL_MM 과 함께 여기 둔다(임시/눈대중 값 — 실측 후 조정).
SEAL_OFFSET_X_MM: float = 15.0

# PDF export(services/export_pdf.py) 한글 폰트. reportlab 로 PDF 안에 직접 임베드해서
# 시스템에 한글 폰트/네이티브 라이브러리가 전혀 없어도(Vercel Serverless 등) 동작하게 한다.
# 나눔고딕(SIL OFL, 재배포 가능) — 교체 시 이 두 파일만 바꾸면 됨.
FONT_REGULAR_PATH: Path = Path(__file__).resolve().parent / "assets" / "fonts" / "NanumGothic-Regular.ttf"
FONT_BOLD_PATH: Path = Path(__file__).resolve().parent / "assets" / "fonts" / "NanumGothic-Bold.ttf"

# ---------------------------------------------------------------------------
# 견적서 출력물(엑셀/PDF) 정형 문구 — `견적서_위탁계약용.xlsx`(바탕화면, 실제 발행 양식)
#   에서 전사(DECISIONS.md: 위탁계약형 전면대체). 협의로 문구가 확정되면 이 블록만
#   수정한다(격리 지점, tech/09-export.md).
# ---------------------------------------------------------------------------
MGMT_NO_DISPLAY_PREFIX = "혁신"          # 출력용 견적NO 접두어. 저장 mgmt_no 는 26-B-008 그대로.
                                          # 부서별로 다를 수 있음(예: 의장설계팀="의장") — 지금은
                                          # 이 팀만 쓰므로 전역 고정, 협의 전까지 미정(provisional).
QUOTE_VALIDITY_NOTE = "견적일로부터 30일"  # 견적유효기간
QUOTE_AUTHOR_TEAM = "스마트혁신팀"         # 견적 작성처 정보 = 이 팀 + 견적 그룹명 + 발행담당자명 + 아래 직급
QUOTE_AUTHOR_ROLE = "그룹장"               # 발행담당자명 뒤에 붙는 고정 직급 표기(모든 담당자가 실제로
                                          # 이 직급은 아닐 수 있음 — 격리 지점, tech/09-export.md)
QUOTE_RECIPIENT_HONORIFIC = "귀하"         # 수신처 담당자명 뒤 존칭

QUOTE_GREETING = "아래와 같이 견적합니다."  # 수신처 블록 마지막 줄
QUOTE_GREETING_LINES = (
    "1. 귀사의 일익 번창하심을 기원합니다.",
    "2. 귀부서의 업무 협조에 깊은 감사를 드리며, 상기의 건 관련하여 견적서를 아래와 같이 제출합니다.",
)
# 대금결제조건/납품조건/WORK SCOPE/납기 — 번호·들여쓰기까지 원본 그대로(줄 단위 상수).
QUOTE_CONDITION_LINES = (
    "3. 대금 결제조건 : 귀사의 결제 조건에 따름.",
    "4. 납품조건",
    "   - 제출용 : 귀사의 작성 기준에 준함.",
    "5. WORK SCOPE : 귀사의 설계용역 범위내",
    "6. 납  기 : 귀사의 일정에 준하여 일정표 제출 예정임",
)

# ---------------------------------------------------------------------------
# 계산 상수 (기획서 5장 / 확정)
# ---------------------------------------------------------------------------
VAT_RATE = 0.1
TRUNCATE_UNIT = 100_000   # 공급가액 합계 십만단위 절사(내림)
SEQ_MAX = 999             # 관리번호 순번 3자리 (open-11)

# ---------------------------------------------------------------------------
# 상태값 (기획서 7장)
# ---------------------------------------------------------------------------
STATUS_SUBMITTED = "SUBMITTED"   # 제출됨
STATUS_APPROVED = "APPROVED"     # 승인됨
STATUS_REJECTED = "REJECTED"     # 반려됨
STATUS_CANCELLED = "CANCELLED"   # 취소됨

STATUS_LABELS: dict[str, str] = {
    STATUS_SUBMITTED: "제출됨",
    STATUS_APPROVED: "승인됨",
    STATUS_REJECTED: "반려됨",
    STATUS_CANCELLED: "취소됨",
}

# ---------------------------------------------------------------------------
# 구매관리 · 자산관리 (PURCHASE-1, specs/PURCHASE-1/)
# ---------------------------------------------------------------------------
ASSET_CATEGORY_LABELS: dict[str, str] = {
    "SW": "소프트웨어",
    "HW": "하드웨어",
    "EDU": "교육자산",
}
ASSET_CATEGORIES = tuple(ASSET_CATEGORY_LABELS.keys())

ASSET_UNIT_STATUS_AVAILABLE = "AVAILABLE"
ASSET_UNIT_STATUS_ASSIGNED = "ASSIGNED"
ASSET_UNIT_STATUS_EXPIRED = "EXPIRED"

ASSET_UNIT_STATUS_LABELS: dict[str, str] = {
    ASSET_UNIT_STATUS_AVAILABLE: "재고",
    ASSET_UNIT_STATUS_ASSIGNED: "배정됨",
    ASSET_UNIT_STATUS_EXPIRED: "만료",
}

ASSET_UNIT_TYPE_LABELS: dict[str, str] = {
    "KEY": "키",
    "ACCOUNT": "계정",
}

# ---------------------------------------------------------------------------
# 자산관리 (ASSET-1, specs/ASSET-1/) — ASSET_CATEGORIES 는 위 PURCHASE-1 것을 재사용
# ---------------------------------------------------------------------------
ASSET_STATUS_IDLE = "IDLE"          # 미사용
ASSET_STATUS_IN_USE = "IN_USE"      # 사용 중
ASSET_STATUS_DISPOSED = "DISPOSED"  # 폐기(soft delete)

ASSET_STATUS_LABELS: dict[str, str] = {
    ASSET_STATUS_IDLE: "미사용",
    ASSET_STATUS_IN_USE: "사용 중",
    ASSET_STATUS_DISPOSED: "폐기",
}

# 자산관리 화면의 유형 표기(C6: 구매관리 라벨 "교육자산"은 그대로 두고 여기서만 "교육").
ASSET_MENU_CATEGORY_LABELS: dict[str, str] = {"SW": "SW", "HW": "HW", "EDU": "교육"}

# 소분류 — 임시 결정 P7(초기 목록). 유형별 {코드: 라벨}. EDU 는 소분류 없음.
ASSET_SUBCATEGORIES: dict[str, dict[str, str]] = {
    "SW": {"LICENSE": "라이선스", "AI_SUB": "AI 구독", "ETC": "기타"},
    "HW": {
        "LAPTOP": "노트북", "MONITOR": "모니터", "MOUSE": "마우스", "KEYBOARD": "키보드",
        "HUB": "허브", "ROUTER": "라우터", "ETC": "기타",
    },
    "EDU": {},
}

ASSET_DISPOSED_REASON_DISPOSED = "DISPOSED"
ASSET_DISPOSED_REASON_IMPORT_CANCELLED = "IMPORT_CANCELLED"
ASSET_DISPOSED_REASON_LABELS: dict[str, str] = {
    ASSET_DISPOSED_REASON_DISPOSED: "폐기",
    ASSET_DISPOSED_REASON_IMPORT_CANCELLED: "가져오기 취소",
}

# 구매 유닛 → 자산 연결 종류(COORDINATION C3). asset_units.asset_link_kind 값.
ASSET_LINK_IMPORTED = "IMPORTED"
ASSET_LINK_RENEWED = "RENEWED"
ASSET_LINK_LABELS: dict[str, str] = {
    ASSET_LINK_IMPORTED: "자산 등록됨",
    ASSET_LINK_RENEWED: "갱신에 사용됨",
}

ASSET_NO_SEQ_MAX = 999        # 연·유형당 순번 3자리(D6)
ASSET_EXPIRING_DAYS = 30      # "만료 임박" 배지 / 대시보드 D-30
ASSET_RENEWAL_KPI_FAR_DAYS = 90
ASSET_BULK_MAX = 100          # 수량 N 등록 상한 — 임시 결정 P8
ASSET_TZ_OFFSET_HOURS = 9     # "오늘"·"올해" 기준 KST(D45). DST 없음 → 고정 오프셋
