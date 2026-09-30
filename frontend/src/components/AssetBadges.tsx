import type { AssetStatus, ExpiryBadge } from "../types";

const STATUS_LABEL: Record<AssetStatus, string> = { IDLE: "미사용", IN_USE: "사용 중", DISPOSED: "폐기", DELETED: "삭제됨" };

export function AssetStateBadge({ status }: { status: AssetStatus }) {
  return <span className={`badge badge-a-${status.toLowerCase()}`}>{STATUS_LABEL[status]}</span>;
}

/** 만료는 상태가 아니라 배지(D21). 서버가 KST 기준으로 계산한 expiry_badge 를 그대로 표시. */
export function ExpiryBadgeView({ badge }: { badge: ExpiryBadge | null }) {
  if (!badge) return null;
  return badge === "EXPIRED" ? (
    <span className="badge badge-expired">만료</span>
  ) : (
    <span className="badge badge-expiring">만료 임박</span>
  );
}
