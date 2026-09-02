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

    database_url: str = "postgresql+psycopg://quote:quote@localhost:5432/quote"
    database_url_test: str = "postgresql+psycopg://quote:quote@localhost:5432/quote_test"
    cors_origins: str = "http://localhost:5173"
    token_secret: str = "dev-secret-change-me"
    token_ttl_hours: int = 12

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
    "ceo_name": "신인규",
    "address": "경남 거제 장평3로 75",
    "tel": "055-630-1263",
    "fax": "055-631-5286",
    "biz_type": "정보통신업",                        # 업태
    "biz_item": "응용 소프트웨어 개발 및 공급업",     # 종목
}

# PDF/엑셀 견적서 출력물에 삽입하는 자사 로고. 파일 없으면 각 export 서비스가
# 조용히 로고 없이 출력한다(PDF_UNAVAILABLE 과 동일하게 export 자체는 항상 성공).
LOGO_PATH: Path = Path(__file__).resolve().parent / "assets" / "sotec-logo.png"

# 승인(APPROVED) 견적서 export 에 대표자명 옆에 합성하는 직인.
#   현재는 scripts/make_seal.py 로 만든 임시 "SOTEC" 직인. 실제 직인이 오면
#   같은 경로에 파일만 교체하면 된다(크기가 달라도 SEAL_MM 으로 흡수).
SEAL_PATH: Path = Path(__file__).resolve().parent / "assets" / "sotec-seal.png"
SEAL_MM: float = 22.0            # 출력물에서 직인 한 변 길이(mm). 실제 직인 비율에 맞게 조정.

# ---------------------------------------------------------------------------
# 견적서 출력물(엑셀/PDF) 정형 문구 — 실제 견적서.jpg 에서 전사.
#   협의로 문구가 확정되면 이 블록만 수정한다(격리 지점, tech/09-export.md).
# ---------------------------------------------------------------------------
MGMT_NO_DISPLAY_PREFIX = "혁신"          # 출력용 견적NO 접두어. 저장 mgmt_no 는 26-B-008 그대로.
QUOTE_VALIDITY_NOTE = "견적일로부터 30일"  # 견적유효기간
QUOTE_AUTHOR_TEAM = "스마트혁신팀"         # 견적 작성자 정보 = 이 팀 + 견적 그룹명
QUOTE_AUTHOR_ROLE = "구성원 그룹장"

QUOTE_GREETING = "아래와 같이 견적합니다."
QUOTE_GREETING_LINES = (
    "1. 귀사의 무궁한 발전을 기원합니다.",
    "2. 귀부서의 업무 협조에 깊은 감사를 드리며, 상기와 같이 견적서를 제출합니다.",
)
QUOTE_CONDITIONS = (
    ("대금결제조건", "귀사의 결제조건에 따름."),
    ("납품조건", ""),
    ("WORK SCOPE", "귀사의 설계용역 범위내 준용."),
)
QUOTE_SIGNOFF_COLS = ("작성", "검토", "승인")   # 우측 서명란

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
