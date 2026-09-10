"""도메인 모델 — Firestore 문서 ↔ 파이썬 객체 변환. TECH 03(원 설계) / 12(Firestore) 참고.

SQLAlchemy ORM 은 더 이상 쓰지 않는다(Firestore 전환, DECISIONS.md 참고). 여기 dataclass
들은 순수 데이터 컨테이너이고, Firestore 저장/조회는 이 파일의 `to_dict()`/`from_doc()`
로만 오간다 — `services/status.py`, `services/calculation.py`, `services/export_*` 는
속성 읽기/쓰기만 하므로 ORM 이었을 때와 동일하게 무변경으로 계속 동작한다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(value)


@dataclass
class QuoteItem:
    line_no: int
    name: str
    qty: int
    unit_price: int
    line_amount: int

    def to_dict(self) -> dict:
        return {
            "line_no": self.line_no,
            "name": self.name,
            "qty": self.qty,
            "unit_price": self.unit_price,
            "line_amount": self.line_amount,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "QuoteItem":
        return cls(
            line_no=d["line_no"],
            name=d["name"],
            qty=d["qty"],
            unit_price=d["unit_price"],
            line_amount=d["line_amount"],
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
    customer_contact_name: str | None
    customer_contact_phone: str | None

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
            "customer_contact_name": self.customer_contact_name,
            "customer_contact_phone": self.customer_contact_phone,
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
            customer_contact_name=data.get("customer_contact_name"),
            customer_contact_phone=data.get("customer_contact_phone"),
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
