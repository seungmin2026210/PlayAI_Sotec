import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getAssetUnit, retireAssetUnit } from "../api/purchase";
import { ApiError } from "../api/client";
import { useToast } from "../components/Toast";
import { SuperAdminOnly } from "../components/RoleGate";
import { AssetLinkBadge, AssetStatusBadge } from "../components/StatusBadge";
import { formatWon } from "../lib/money";
import type { AssetUnit } from "../types";

export function PurchaseDetail() {
  const { unitNo } = useParams();
  const id = unitNo ?? "";
  const navigate = useNavigate();
  const toast = useToast();

  const [unit, setUnit] = useState<AssetUnit | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setUnit(await getAssetUnit(id));
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "불러오기 실패", "error");
      if (err instanceof ApiError && err.status === 404) navigate("/purchase", { replace: true });
    } finally {
      setLoading(false);
    }
  }, [id, navigate, toast]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function onRetire() {
    // C4: 자산으로 가져온 유닛이어도 자산은 영향 없음(가져올 때 복사) — 경고만 한다.
    const linked =
      unit?.asset_link_kind && unit.asset_nos.length
        ? `${unit.asset_link_kind === "IMPORTED" ? "자산" : "갱신"} ${unit.asset_nos[0]}${unit.asset_nos.length > 1 ? ` 외 ${unit.asset_nos.length - 1}건` : ""}에 연결된 구매 기록입니다(자산은 그대로 유지됩니다).\n`
        : "";
    if (!window.confirm(`${linked}폐기 처리하면 되돌릴 수 없습니다. 번호는 재사용되지 않습니다. 계속할까요?`))
      return;
    setBusy(true);
    try {
      await retireAssetUnit(id);
      toast.show("폐기 처리했습니다.", "success");
      await reload();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "처리 실패", "error");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="page">불러오는 중…</div>;
  if (!unit) return <div className="page">자산을 찾을 수 없습니다.</div>;

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>
            {unit.unit_no} <AssetStatusBadge status={unit.status} /> <AssetLinkBadge unit={unit} />
          </h1>
          <p className="muted">
            {unit.group_code} · {unit.group_name} / {unit.asset_category_label}
            {unit.updated_at && ` / 수정 ${new Date(unit.updated_at).toLocaleString("ko-KR")}`}
          </p>
        </div>
        <div className="head-actions">
          <SuperAdminOnly>
            {unit.status !== "EXPIRED" && (
              <>
                <button disabled={busy} onClick={() => navigate(`/purchase/${id}/edit`)}>
                  수정
                </button>
                <button className="danger" disabled={busy} onClick={onRetire}>
                  폐기 처리
                </button>
              </>
            )}
          </SuperAdminOnly>
          <button className="ghost" onClick={() => navigate("/purchase")}>
            목록으로
          </button>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h2>상품</h2>
          <dl>
            <dt>상품명</dt>
            <dd>{unit.product_name}</dd>
            <dt>자산 유형</dt>
            <dd>{unit.asset_category_label}</dd>
            {unit.unit_type_label && (
              <>
                <dt>유닛 타입</dt>
                <dd>{unit.unit_type_label}</dd>
              </>
            )}
            {unit.key_value && (
              <>
                <dt>키 / 계정 값</dt>
                <dd>{unit.key_value}</dd>
              </>
            )}
          </dl>
        </div>

        <div className="card">
          <h2>구매 정보</h2>
          <dl>
            <dt>구매일자</dt>
            <dd>{unit.purchase_date}</dd>
            <dt>구매처</dt>
            <dd>{unit.purchased_from || "-"}</dd>
            <dt>금액</dt>
            <dd>{formatWon(unit.price)}</dd>
            <dt>만료일</dt>
            <dd>{unit.expire_date || "무기한"}</dd>
          </dl>
        </div>

        <div className="card">
          <h2>연동 · 이력</h2>
          <dl>
            <dt>연동 견적서</dt>
            <dd>{unit.source_quote_id || "-"}</dd>
            <dt>등록일시</dt>
            <dd>{new Date(unit.created_at).toLocaleString("ko-KR")}</dd>
            {unit.retired_at && (
              <>
                <dt>폐기일시</dt>
                <dd>{new Date(unit.retired_at).toLocaleString("ko-KR")}</dd>
              </>
            )}
          </dl>
        </div>
      </div>

      <div className="card">
        {unit.asset_nos.length > 0 ? (
          <p>
            {unit.asset_link_label}:{" "}
            {unit.asset_nos.map((no, i) => (
              <span key={no}>
                {i > 0 && ", "}
                <Link to={`/assets/item/${no}`}>{no}</Link>
              </span>
            ))}
          </p>
        ) : (
          <p className="muted">
            자산으로 가져오지 않은 구매 기록입니다. 사내에서 쓰는 자산이면 자산관리 › 구매에서 가져오기로 등록하세요.
          </p>
        )}
      </div>
    </div>
  );
}
