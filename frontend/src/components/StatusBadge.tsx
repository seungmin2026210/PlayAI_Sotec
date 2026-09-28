import type { AssetUnit, AssetUnitStatus, QuoteStatus } from "../types";

const LABEL: Record<QuoteStatus, string> = {
  SUBMITTED: "제출됨",
  APPROVED: "승인됨",
  REJECTED: "반려됨",
  CANCELLED: "취소됨",
};

export function StatusBadge({ status }: { status: QuoteStatus }) {
  return <span className={`badge badge-${status.toLowerCase()}`}>{LABEL[status]}</span>;
}

export function LockBadge() {
  return <span className="badge badge-lock">읽기전용(구매반영)</span>;
}

const ASSET_STATUS_LABEL: Record<AssetUnitStatus, string> = {
  AVAILABLE: "재고",
  ASSIGNED: "배정됨",
  EXPIRED: "만료",
};

export function AssetStatusBadge({ status }: { status: AssetUnitStatus }) {
  return <span className={`badge badge-asset-${status.toLowerCase()}`}>{ASSET_STATUS_LABEL[status]}</span>;
}

/** ASSET-1 C3: 구매 유닛이 자산으로 등록됐거나 갱신에 쓰였으면 "자산 등록됨(SW-26-001 외 9건)". */
export function AssetLinkBadge({ unit }: { unit: Pick<AssetUnit, "asset_link_label" | "asset_nos"> }) {
  if (!unit.asset_link_label) return null;
  const [first, ...rest] = unit.asset_nos;
  const suffix = first ? `(${first}${rest.length ? ` 외 ${rest.length}건` : ""})` : "";
  return (
    <span className="badge badge-link">
      {unit.asset_link_label}
      {suffix}
    </span>
  );
}
