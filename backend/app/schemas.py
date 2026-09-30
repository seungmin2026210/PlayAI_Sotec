"""Pydantic 스키마 — 전송 형태. 유효성: 기획서 9장."""
from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .config import ASSET_CATEGORIES, GROUP_CODES


# --------------------------------------------------------------------------- auth
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    username: str
    role: str
    group_code: str | None
    display_name: str


class LoginResponse(BaseModel):
    token: str
    user: UserOut


# --------------------------------------------------------------------------- meta
class GroupOut(BaseModel):
    code: str
    name: str


class MetaResponse(BaseModel):
    groups: list[GroupOut]
    company: dict
    vat_rate: float
    truncate_unit: int
    statuses: list[dict]
    asset_categories: list[dict]  # PURCHASE-1: [{"code": "SW", "label": "소프트웨어"}, ...]
    asset_subcategories: dict[str, list[dict]]  # ASSET-1: {"SW": [{"code","label"}], ...}
    asset_statuses: list[dict]


# --------------------------------------------------------------------------- items
class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    qty: int
    unit_price: int  # 공급가액 기준(위탁계약형은 항목별 공급가액 직접 입력 — qty=1 고정, unit_price=그 금액)
    period_start: date | None = None  # 용역(계약) 기간 — 위탁계약형 전용, 선택입력
    period_end: date | None = None

    @field_validator("qty")
    @classmethod
    def _qty_pos(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("갯수는 1 이상이어야 합니다.")
        return v

    @field_validator("unit_price")
    @classmethod
    def _price_pos(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("금액은 0보다 커야 합니다.")
        return v


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    line_no: int
    name: str
    qty: int
    unit_price: int
    line_amount: int
    period_start: date | None
    period_end: date | None


# --------------------------------------------------------------------------- quote
class QuoteCreate(BaseModel):
    group_code: str
    title: str = Field(min_length=1, max_length=200)
    issue_date: date
    issuer_name: str = Field(min_length=1, max_length=80)
    customer_name: str = Field(min_length=1, max_length=200)
    customer_department: str | None = Field(default=None, max_length=100)  # 수신처 부서명
    customer_contact_name: str | None = Field(default=None, max_length=80)
    customer_contact_phone: str | None = Field(default=None, max_length=40)
    customer_cc: str | None = Field(default=None, max_length=80)  # C.C 참조인(선택)
    vat_included: bool
    items: list[ItemIn] = Field(min_length=1)

    @field_validator("group_code")
    @classmethod
    def _group_valid(cls, v: str) -> str:
        if v not in GROUP_CODES:
            raise ValueError(f"그룹코드는 {', '.join(GROUP_CODES)} 중 하나여야 합니다.")
        return v


class QuoteUpdate(QuoteCreate):
    """수정 — open-10 임시결정: 전체 필드 수정 허용, 상태값 유지."""


class RejectRequest(BaseModel):
    reason: str = Field(min_length=1)

    @field_validator("reason")
    @classmethod
    def _reason_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("반려 사유를 입력해야 합니다.")
        return v.strip()


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str  # Firestore 문서ID == mgmt_no (12-firestore-migration.md § 1, § 7)
    mgmt_no: str
    seq_year: int
    group_code: str
    group_name: str
    seq_no: int

    title: str
    issue_date: date
    issuer_name: str

    customer_name: str
    customer_department: str | None
    customer_contact_name: str | None
    customer_contact_phone: str | None
    customer_cc: str | None

    vat_included: bool
    supply_amount: int
    vat_amount: int
    total_with_vat: int
    items_raw_total: int

    status: str
    status_label: str
    reject_reason: str | None
    purchase_locked: bool
    read_only: bool  # 파생: 잠금 또는 종료상태 → 편집 불가

    created_by: str
    created_at: datetime
    updated_at: datetime | None
    approved_at: datetime | None
    rejected_at: datetime | None
    cancelled_at: datetime | None
    locked_at: datetime | None

    company: dict
    items: list[ItemOut]


class QuoteListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    mgmt_no: str
    group_code: str
    group_name: str
    title: str
    customer_name: str
    issue_date: date
    issuer_name: str
    supply_amount: int
    vat_amount: int
    total_with_vat: int
    vat_included: bool
    status: str
    status_label: str
    purchase_locked: bool
    created_at: datetime


class QuoteListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[QuoteListItem]


class MessageResponse(BaseModel):
    message: str


# --------------------------------------------------------------------------- PURCHASE-1: 상품 마스터
class AssetProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    vendor: str | None = Field(default=None, max_length=100)
    asset_category: str

    @field_validator("asset_category")
    @classmethod
    def _category_valid(cls, v: str) -> str:
        if v not in ASSET_CATEGORIES:
            raise ValueError(f"자산 유형은 {', '.join(ASSET_CATEGORIES)} 중 하나여야 합니다.")
        return v

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("상품명을 입력해야 합니다.")
        return v.strip()


class AssetProductPatch(BaseModel):
    """부분 수정 — 이름/벤더/사용여부만. 자산 유형은 바꾸지 않는다(이미 만들어진 유닛과 불일치 방지)."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    vendor: str | None = Field(default=None, max_length=100)
    is_active: bool | None = None


class AssetProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    vendor: str | None
    asset_category: str
    asset_category_label: str
    is_active: bool
    created_at: datetime


class AssetProductListResponse(BaseModel):
    items: list[AssetProductRead]


# --------------------------------------------------------------------------- PURCHASE-1: 구매관리(유닛)
class AssetUnitCreate(BaseModel):
    product_id: str
    purchase_date: date
    purchased_from: str | None = Field(default=None, max_length=100)
    price: int
    unit_type: str | None = None  # "KEY" | "ACCOUNT" (SW만 해당, HW는 None)
    key_value: str | None = Field(default=None, max_length=200)
    expire_date: date | None = None  # None = 무기한
    group_code: str
    source_quote_id: str | None = None  # 견적 연동 시, 그 견적서를 자동 잠금

    @field_validator("price")
    @classmethod
    def _price_pos(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("금액은 0보다 커야 합니다.")
        return v

    @field_validator("unit_type")
    @classmethod
    def _unit_type_valid(cls, v: str | None) -> str | None:
        if v is not None and v not in ("KEY", "ACCOUNT"):
            raise ValueError("유닛 타입은 KEY 또는 ACCOUNT 여야 합니다.")
        return v

    @field_validator("group_code")
    @classmethod
    def _group_valid(cls, v: str) -> str:
        if v not in GROUP_CODES:
            raise ValueError(f"그룹코드는 {', '.join(GROUP_CODES)} 중 하나여야 합니다.")
        return v


class AssetUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str  # == unit_no == Firestore 문서 ID
    unit_no: str
    product_id: str
    product_name: str
    asset_category: str
    asset_category_label: str

    purchase_date: date
    purchased_from: str | None
    price: int

    unit_type: str | None
    unit_type_label: str | None
    key_value: str | None

    expire_date: date | None
    status: str
    status_label: str

    source_quote_id: str | None
    group_code: str
    group_name: str

    created_at: datetime
    updated_at: datetime | None
    retired_at: datetime | None

    # ASSET-1 C3: 자산 연결 역참조(자산관리 트랜잭션만 씀)
    asset_link_kind: str | None = None
    asset_link_label: str | None = None
    asset_nos: list[str] = []


class AssetUnitListItem(BaseModel):
    """목록용 — 키/계정 값은 보안상 상세 조회에서만 노출."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    unit_no: str
    product_name: str
    asset_category: str
    asset_category_label: str
    purchase_date: date
    price: int
    status: str
    status_label: str
    group_code: str
    group_name: str
    asset_link_kind: str | None = None
    asset_link_label: str | None = None
    asset_nos: list[str] = []


class AssetUnitListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[AssetUnitListItem]


# --------------------------------------------------------------------------- ASSET-1: 자산
def _check_group(v: str | None) -> str | None:
    if v is not None and v not in GROUP_CODES:
        raise ValueError(f"그룹코드는 {', '.join(GROUP_CODES)} 중 하나여야 합니다.")
    return v


class AssetFieldsIn(BaseModel):
    """등록/수정 공통 입력. `password` 는 write-only — 없음/null/"" = 변경 없음(D42).
    응답 스키마엔 `password`/`password_enc` 가 아예 없다(has_password 만)."""

    subcategory: str | None = None
    name: str | None = Field(default=None, max_length=200)
    group_code: str | None = None
    purchase_date: date | None = None
    price: int | None = Field(default=None, ge=0)
    purchased_from: str | None = Field(default=None, max_length=100)
    quote_no: str | None = Field(default=None, max_length=40)
    contract_no: str | None = Field(default=None, max_length=60)
    valid_from: date | None = None
    valid_to: date | None = None
    version: str | None = Field(default=None, max_length=60)
    license_key: str | None = Field(default=None, max_length=300)
    account_id: str | None = Field(default=None, max_length=200)
    password: str | None = Field(default=None, max_length=300)
    manufacturer: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_no: str | None = Field(default=None, max_length=100)
    mac_address: str | None = Field(default=None, max_length=40)
    course_title: str | None = Field(default=None, max_length=200)
    course_url: str | None = Field(default=None, max_length=500)
    note: str | None = Field(default=None, max_length=1000)

    @field_validator("group_code")
    @classmethod
    def _group_valid(cls, v: str | None) -> str | None:
        return _check_group(v)


class AssetCreate(AssetFieldsIn):
    category: str
    name: str = Field(min_length=1, max_length=200)
    group_code: str
    quantity: int = 1  # 1~ASSET_BULK_MAX — 범위 밖은 400(서비스에서 검사, PRODUCT 예외표)

    @field_validator("category")
    @classmethod
    def _category_valid(cls, v: str) -> str:
        if v not in ASSET_CATEGORIES:
            raise ValueError(f"자산 유형은 {', '.join(ASSET_CATEGORIES)} 중 하나여야 합니다.")
        return v


class AssetImport(AssetFieldsIn):
    """구매에서 가져오기 — 비워 둔 칸은 구매 유닛 값으로(C5). `price` = 구매 총액(N으로 나눔)."""

    unit_no: str
    quantity: int = 1


class AssetUpdate(AssetFieldsIn):
    """수정 — 보낸 필드만 반영(PATCH). `category` 는 보내면 400(D41) — 라우터에서 검사."""

    category: str | None = None


class UnitNoRequest(BaseModel):
    unit_no: str


class AssetDeleteRequest(BaseModel):
    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def _strip(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("삭제 사유를 입력하세요.")
        return v


class RenewRequest(BaseModel):
    asset_nos: list[str] = Field(min_length=1)
    new_valid_to: date
    new_valid_from: date | None = None
    unit_no: str | None = None


class AssignRequest(BaseModel):
    member_id: str | None = None
    shared_label: str | None = Field(default=None, max_length=100)
    start_date: date
    note: str | None = Field(default=None, max_length=500)


class TransferRequest(BaseModel):
    member_id: str | None = None
    shared_label: str | None = Field(default=None, max_length=100)
    date: date
    note: str | None = Field(default=None, max_length=500)


class ReturnRequest(BaseModel):
    end_date: date
    note: str | None = Field(default=None, max_length=500)


class AssignmentPatch(BaseModel):
    start_date: date | None = None
    end_date: date | None = None
    note: str | None = Field(default=None, max_length=500)


class RevealRequest(BaseModel):
    action: str = "REVEAL"

    @field_validator("action")
    @classmethod
    def _action_valid(cls, v: str) -> str:
        if v not in ("REVEAL", "COPY"):
            raise ValueError("action 은 REVEAL 또는 COPY 여야 합니다.")
        return v


class RevealResponse(BaseModel):
    password: str


class AssignmentRead(BaseModel):
    id: str
    asset_no: str
    category: str
    asset_name: str
    member_id: str | None
    member_name: str | None
    shared_label: str | None
    start_date: date
    end_date: date | None
    note: str | None
    created_by: str | None
    updated_at: datetime | None
    updated_by: str | None


class RenewalRead(BaseModel):
    id: str
    prev_valid_to: date
    new_valid_from: date | None
    new_valid_to: date
    unit_no: str | None
    count: int
    created_at: datetime | None
    created_by: str | None


class AssetListItem(BaseModel):
    asset_no: str
    category: str
    category_label: str
    subcategory: str | None
    subcategory_label: str | None
    name: str
    status: str
    status_label: str
    group_code: str
    group_name: str
    scope_group_code: str
    scope_group_name: str
    current_member_id: str | None
    current_member_name: str | None
    current_shared_label: str | None
    current_start_date: date | None
    purchase_date: date | None
    price: int | None
    valid_from: date | None
    valid_to: date | None
    expiry_badge: str | None  # "EXPIRED" | "EXPIRING" | None
    version: str | None
    license_key: str | None  # 그룹관리자면 마스킹(D38)
    account_id: str | None
    has_password: bool
    manufacturer: str | None
    model: str | None
    serial_no: str | None
    mac_address: str | None
    course_title: str | None
    course_url: str | None
    quote_no: str | None
    contract_no: str | None
    source_unit_no: str | None
    purchased_from: str | None
    note: str | None
    disposed_reason: str | None
    disposed_reason_label: str | None
    read_only: bool


class AssetRead(AssetListItem):
    disposed_at: datetime | None
    deleted_at: datetime | None
    deleted_by: str | None
    deleted_reason: str | None
    created_at: datetime | None
    created_by: str | None
    updated_at: datetime | None
    updated_by: str | None
    assignments: list[AssignmentRead]
    renewals: list[RenewalRead]


class AssetListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[AssetListItem]


class AssetCreateResponse(BaseModel):
    asset_nos: list[str]


class AssetUploadIssue(BaseModel):
    """엑셀 업로드 검증 결과 1건 — row/column 이 None 이면 시트(또는 파일) 단위."""

    sheet: str
    row: int | None = None
    column: str | None = None
    message: str


class AssetUploadRow(BaseModel):
    sheet: str
    row: int
    category: str
    name: str | None
    group_name: str | None
    subcategory_label: str | None
    user_label: str | None  # 팀원 이름(사번) / "공용 · 장소" / None(미사용)
    start_date: str | None
    start_auto: bool  # 사용 시작일을 구매일·오늘로 자동 채움
    has_password: bool


class AssetUploadPreview(BaseModel):
    total: int
    counts: dict[str, int]  # 유형별 건수
    rows: list[AssetUploadRow]
    errors: list[AssetUploadIssue]
    warnings: list[AssetUploadIssue]


class AssetUploadResponse(BaseModel):
    batch_id: str
    asset_nos: list[str]
    counts: dict[str, int]


# --------------------------------------------------------------------------- ASSET-1: 팀원
class MemberCreate(BaseModel):
    employee_no: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=40)
    group_code: str

    @field_validator("group_code")
    @classmethod
    def _group_valid(cls, v: str | None) -> str | None:
        return _check_group(v)

    @field_validator("employee_no", "name")
    @classmethod
    def _strip(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("빈 값은 입력할 수 없습니다.")
        return v.strip()


class MemberPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=40)
    group_code: str | None = None
    active: bool | None = None

    @field_validator("group_code")
    @classmethod
    def _group_valid(cls, v: str | None) -> str | None:
        return _check_group(v)


class MemberRead(BaseModel):
    employee_no: str
    name: str
    group_code: str
    group_name: str
    active: bool
    counts: dict[str, int]  # {"SW": n, "HW": n, "EDU": n} — 현재 사용 중
    warning: str | None = None  # 퇴사 처리 시 사용 중 자산 경고(P2)


class MemberListResponse(BaseModel):
    items: list[MemberRead]


class MemberHistoryRow(AssignmentRead):
    linkable: bool  # D37: False = 지금 다른 그룹에서 사용 중 → 상세 링크 없음


class MemberDetail(MemberRead):
    assignments: list[MemberHistoryRow]


# --------------------------------------------------------------------------- ASSET-1: 대시보드
class RenewalGroup(BaseModel):
    date: date
    name: str
    category: str
    count: int
    asset_nos: list[str]


class RenewalKpi(BaseModel):
    expired: int
    d30: int
    d90: int


class RenewalCalendarResponse(BaseModel):
    items: list[RenewalGroup]
    kpi: RenewalKpi
