"""도메인 모델 — Firestore 문서 ↔ 파이썬 객체 변환. TECH 03(원 설계) / 12(Firestore) 참고.

SQLAlchemy ORM 은 더 이상 쓰지 않는다(Firestore 전환, DECISIONS.md 참고). 여기 dataclass
들은 순수 데이터 컨테이너이고, Firestore 저장/조회는 이 파일의 `to_dict()`/`from_doc()`
로만 오간다 — `services/status.py`, `services/calculation.py`, `services/export_*` 는
속성 읽기/쓰기만 하므로 ORM 이었을 때와 동일하게 무변경으로 계속 동작한다.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields
from datetime import date, datetime
from typing import Any


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


def _parse_date_opt(value: Any) -> date | None:
    return _parse_date(value) if value else None


@dataclass
class QuoteItem:
    line_no: int
    name: str
    qty: int
    unit_price: int
    line_amount: int
    period_start: date | None = None  # 용역(계약) 기간 — 위탁계약형 전용, 선택입력
    period_end: date | None = None

    def to_dict(self) -> dict:
        return {
            "line_no": self.line_no,
            "name": self.name,
            "qty": self.qty,
            "unit_price": self.unit_price,
            "line_amount": self.line_amount,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuoteItem":
        return cls(
            line_no=d["line_no"],
            name=d["name"],
            qty=d["qty"],
            unit_price=d["unit_price"],
            line_amount=d["line_amount"],
            period_start=_parse_date(d["period_start"]) if d.get("period_start") else None,
            period_end=_parse_date(d["period_end"]) if d.get("period_end") else None,
        )


@dataclass
class Quote:
    """`quotes/{mgmt_no}` 문서 1건. `id` == `mgmt_no` == Firestore 문서 ID(12-firestore-migration.md § 1).

    구조상 SQLAlchemy 시절의 `bigserial id`(정수)가 문자열로 바뀐다 — API 계약
    breaking change(같은 문서 § 7 프론트 영향 참고).
    """

    id: str
    mgmt_no: str
    seq_year: int
    group_code: str
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
    purchase_locked: bool
    active: bool  # soft delete 플래그. deleted_at 은 감사용 타임스탬프로만 별도 보관(§4)

    created_by: str
    created_at: datetime

    items: list[QuoteItem] = field(default_factory=list)
    reject_reason: str | None = None
    updated_at: datetime | None = None
    approved_at: datetime | None = None
    rejected_at: datetime | None = None
    cancelled_at: datetime | None = None
    locked_at: datetime | None = None
    deleted_at: datetime | None = None

    def to_dict(self) -> dict:
        """Firestore 문서 본문. `mgmt_no`는 문서ID와 같은 값을 필드로도 중복 저장
        (쿼리·export 편의 — 정본은 문서ID)."""
        return {
            "mgmt_no": self.mgmt_no,
            "seq_year": self.seq_year,
            "group_code": self.group_code,
            "seq_no": self.seq_no,
            "title": self.title,
            "issue_date": self.issue_date.isoformat(),
            "issuer_name": self.issuer_name,
            "customer_name": self.customer_name,
            "customer_department": self.customer_department,
            "customer_contact_name": self.customer_contact_name,
            "customer_contact_phone": self.customer_contact_phone,
            "customer_cc": self.customer_cc,
            "vat_included": self.vat_included,
            "supply_amount": self.supply_amount,
            "vat_amount": self.vat_amount,
            "total_with_vat": self.total_with_vat,
            "items_raw_total": self.items_raw_total,
            "items": [i.to_dict() for i in self.items],
            "status": self.status,
            "reject_reason": self.reject_reason,
            "purchase_locked": self.purchase_locked,
            "active": self.active,
            "created_by": self.created_by,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "approved_at": self.approved_at,
            "rejected_at": self.rejected_at,
            "cancelled_at": self.cancelled_at,
            "locked_at": self.locked_at,
            "deleted_at": self.deleted_at,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "Quote":
        return cls(
            id=doc_id,
            mgmt_no=data["mgmt_no"],
            seq_year=data["seq_year"],
            group_code=data["group_code"],
            seq_no=data["seq_no"],
            title=data["title"],
            issue_date=_parse_date(data["issue_date"]),
            issuer_name=data["issuer_name"],
            customer_name=data["customer_name"],
            customer_department=data.get("customer_department"),
            customer_contact_name=data.get("customer_contact_name"),
            customer_contact_phone=data.get("customer_contact_phone"),
            customer_cc=data.get("customer_cc"),
            vat_included=data["vat_included"],
            supply_amount=data["supply_amount"],
            vat_amount=data["vat_amount"],
            total_with_vat=data["total_with_vat"],
            items_raw_total=data["items_raw_total"],
            items=[QuoteItem.from_dict(i) for i in data.get("items", [])],
            status=data["status"],
            reject_reason=data.get("reject_reason"),
            purchase_locked=data.get("purchase_locked", False),
            active=data.get("active", True),
            created_by=data["created_by"],
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
            approved_at=data.get("approved_at"),
            rejected_at=data.get("rejected_at"),
            cancelled_at=data.get("cancelled_at"),
            locked_at=data.get("locked_at"),
            deleted_at=data.get("deleted_at"),
        )


# --------------------------------------------------------------------------- PURCHASE-1
@dataclass
class AssetProduct:
    """`asset_products/{id}` 문서 1건 — 상품 마스터. `id`는 auto-id(상품명은 바뀔 수 있어서
    문서 ID로 안 씀, specs/PURCHASE-1/tech/01-data-model.md § 1)."""

    id: str
    name: str
    vendor: str | None
    asset_category: str
    is_active: bool
    created_at: datetime

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "vendor": self.vendor,
            "asset_category": self.asset_category,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "AssetProduct":
        return cls(
            id=doc_id,
            name=data["name"],
            vendor=data.get("vendor"),
            asset_category=data["asset_category"],
            is_active=data.get("is_active", True),
            created_at=data["created_at"],
        )


@dataclass
class AssetUnit:
    """`asset_units/{unit_no}` 문서 1건 — 구매관리 탭 전용(무엇을 언제 얼마에 샀는지).
    `id` == `unit_no`(예: "인텔리제이-001") == Firestore 문서 ID(01-data-model.md § 3).

    배정 관련 필드는 여기 없다 — 자산관리 탭(`asset_assignments`, 별도 구현)의 소관이다."""

    id: str
    unit_no: str
    product_id: str
    product_name: str
    asset_category: str

    purchase_date: date
    purchased_from: str | None
    price: int

    unit_type: str | None  # "KEY" | "ACCOUNT" | None(HW)
    key_value: str | None

    expire_date: date | None
    status: str  # AVAILABLE | ASSIGNED | EXPIRED — 이 PR 범위에서는 AVAILABLE/EXPIRED만 씀

    source_quote_id: str | None
    group_code: str

    created_at: datetime
    updated_at: datetime | None = None
    retired_at: datetime | None = None
    # ASSET-1 역참조(COORDINATION C3) — 자산관리 트랜잭션만 쓴다. 기존 문서엔 없음 = None/[].
    asset_link_kind: str | None = None  # None | "IMPORTED" | "RENEWED"
    asset_nos: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "asset_link_kind": self.asset_link_kind,
            "asset_nos": list(self.asset_nos),
            "unit_no": self.unit_no,
            "product_id": self.product_id,
            "product_name": self.product_name,
            "asset_category": self.asset_category,
            "purchase_date": self.purchase_date.isoformat(),
            "purchased_from": self.purchased_from,
            "price": self.price,
            "unit_type": self.unit_type,
            "key_value": self.key_value,
            "expire_date": self.expire_date.isoformat() if self.expire_date else None,
            "status": self.status,
            "source_quote_id": self.source_quote_id,
            "group_code": self.group_code,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "retired_at": self.retired_at,
        }

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "AssetUnit":
        return cls(
            id=doc_id,
            unit_no=data["unit_no"],
            product_id=data["product_id"],
            product_name=data["product_name"],
            asset_category=data["asset_category"],
            purchase_date=_parse_date(data["purchase_date"]),
            purchased_from=data.get("purchased_from"),
            price=data["price"],
            unit_type=data.get("unit_type"),
            key_value=data.get("key_value"),
            expire_date=_parse_date_opt(data.get("expire_date")),
            status=data["status"],
            source_quote_id=data.get("source_quote_id"),
            group_code=data["group_code"],
            created_at=data["created_at"],
            updated_at=data.get("updated_at"),
            retired_at=data.get("retired_at"),
            asset_link_kind=data.get("asset_link_kind"),
            asset_nos=list(data.get("asset_nos") or []),
        )


# --------------------------------------------------------------------------- ASSET-1
# 비즈니스 날짜(구매일·유효기간·사용 시작/종료일)는 `YYYY-MM-DD` 문자열 그대로 둔다 —
# ISO 문자열은 사전순 비교 = 날짜 비교라 날짜 규칙·만료 판정이 그대로 된다
# (specs/ASSET-1/tech/01-data-model.md). 문서 필드 = dataclass 필드(평평한 구조).
def _from_fields(cls, data: dict, **extra):
    names = {f.name for f in fields(cls)}
    return cls(**{k: v for k, v in data.items() if k in names}, **extra)


@dataclass
class Asset:
    """`assets/{asset_no}` 문서 1건. 문서 ID == asset_no."""

    asset_no: str
    category: str
    name: str
    group_code: str
    scope_group_code: str
    status: str
    subcategory: str | None = None

    current_member_id: str | None = None
    current_member_name: str | None = None
    current_shared_label: str | None = None
    current_assignment_id: str | None = None
    current_start_date: str | None = None

    purchase_date: str | None = None
    price: int | None = None
    purchased_from: str | None = None
    quote_no: str | None = None
    contract_no: str | None = None
    source_unit_no: str | None = None

    valid_from: str | None = None
    valid_to: str | None = None

    version: str | None = None
    license_key: str | None = None
    account_id: str | None = None
    password_enc: str | None = None
    manufacturer: str | None = None
    model: str | None = None
    serial_no: str | None = None
    mac_address: str | None = None
    course_title: str | None = None
    course_url: str | None = None

    note: str | None = None
    disposed_at: datetime | None = None
    disposed_reason: str | None = None
    deleted_at: datetime | None = None
    deleted_by: str | None = None
    deleted_reason: str | None = None
    created_at: datetime | None = None
    created_by: str | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_doc(cls, data: dict) -> "Asset":
        return _from_fields(cls, data)


@dataclass
class AssetAssignment:
    """`asset_assignments/{auto-id}` — 사용 이력 1건. end_date None = 사용 중."""

    id: str
    asset_no: str
    category: str
    asset_name: str
    start_date: str
    member_id: str | None = None
    member_name: str | None = None
    shared_label: str | None = None
    end_date: str | None = None
    prev_assignment_id: str | None = None
    note: str | None = None
    created_at: datetime | None = None
    created_by: str | None = None
    updated_at: datetime | None = None
    updated_by: str | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d.pop("id")
        return d

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "AssetAssignment":
        return _from_fields(cls, {k: v for k, v in data.items() if k != "id"}, id=doc_id)


@dataclass
class AssetRenewal:
    """`asset_renewals/{auto-id}` — 갱신 1회(여러 자산 묶음, D32)."""

    id: str
    asset_nos: list[str]
    name: str
    prev_valid_to: str
    new_valid_from: str | None
    new_valid_to: str
    unit_no: str | None = None
    created_at: datetime | None = None
    created_by: str | None = None

    @classmethod
    def from_doc(cls, doc_id: str, data: dict) -> "AssetRenewal":
        return _from_fields(cls, {k: v for k, v in data.items() if k != "id"}, id=doc_id)


@dataclass
class Member:
    """`members/{employee_no}` — 팀원 명단(D10). 삭제 없음, active=False = 퇴사."""

    employee_no: str
    name: str
    group_code: str
    active: bool = True
    created_at: datetime | None = None
    updated_at: datetime | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_doc(cls, data: dict) -> "Member":
        return _from_fields(cls, data)
