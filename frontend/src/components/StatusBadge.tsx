import type { AssetUnitStatus, QuoteStatus } from "../types";

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
