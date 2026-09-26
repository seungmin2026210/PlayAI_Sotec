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


class AssetUnitListResponse(BaseModel):
    total: int
    page: int
    size: int
    items: list[AssetUnitListItem]
