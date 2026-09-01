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
#   데모용 더미값. 실제 사업자정보로 교체.
# ---------------------------------------------------------------------------
COMPANY: dict[str, str] = {
    "name": "(주)스마트기술개발",
    "biz_no": "000-00-00000",       # 사업자등록번호
    "ceo_name": "대표자명",
    "address": "서울특별시 ...",
    "tel": "02-0000-0000",
}

# PDF/엑셀 견적서 출력물에 삽입하는 자사 로고. 파일 없으면 각 export 서비스가
# 조용히 로고 없이 출력한다(PDF_UNAVAILABLE 과 동일하게 export 자체는 항상 성공).
LOGO_PATH: Path = Path(__file__).resolve().parent / "assets" / "sotec-logo.png"

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
