import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAssetProduct, listAssetProducts, patchAssetProduct } from "../api/purchase";
import { ApiError } from "../api/client";
import { useMeta } from "../hooks/useMeta";
import { useToast } from "../components/Toast";
import { SuperAdminOnly } from "../components/RoleGate";
import type { AssetCategory, AssetProduct, AssetProductPayload } from "../types";

const BLANK: AssetProductPayload = { name: "", vendor: "", asset_category: "SW" };

export function PurchaseProductList() {
  const meta = useMeta();
  const toast = useToast();
  const navigate = useNavigate();

  const [items, setItems] = useState<AssetProduct[]>([]);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState<AssetProductPayload>(BLANK);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await listAssetProducts();
      setItems(r.items);
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "상품 목록을 불러오지 못했습니다.", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) {
      toast.show("상품명을 입력하세요.", "error");
      return;
    }
    setBusy(true);
    try {
      await createAssetProduct({ ...form, vendor: form.vendor || null });
      toast.show("상품을 등록했습니다.", "success");
      setForm(BLANK);
      await load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "등록에 실패했습니다.", "error");
    } finally {
      setBusy(false);
    }
  }

  async function toggleActive(p: AssetProduct) {
    try {
      await patchAssetProduct(p.id, { is_active: !p.is_active });
      toast.show(p.is_active ? "사용 중지했습니다." : "다시 활성화했습니다.", "success");
      await load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "변경에 실패했습니다.", "error");
    }
  }

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>상품 마스터</h1>
          <p className="muted">
            구매 등록 시 선택할 상품 목록입니다. 사용 중지해도 이미 구매한 자산은 그대로 남습니다.
          </p>
        </div>
        <button className="ghost" onClick={() => navigate("/purchase")}>
          구매 목록으로
        </button>
      </div>

      <SuperAdminOnly>
        <form className="card" onSubmit={submit}>
          <h2>상품 등록</h2>
          <div className="grid-2">
            <label>
              상품명 *
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
            </label>
            <label>
              벤더
              <input
                value={form.vendor ?? ""}
                onChange={(e) => setForm({ ...form, vendor: e.target.value })}
              />
            </label>
            <label>
              자산 유형 *
              <select
                value={form.asset_category}
                onChange={(e) =>
                  setForm({ ...form, asset_category: e.target.value as AssetCategory })
                }
              >
                {meta?.asset_categories.map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="row-gap" style={{ marginTop: 10 }}>
            <button type="submit" className="primary" disabled={busy}>
              {busy ? "등록 중…" : "+ 상품 등록"}
            </button>
          </div>
        </form>
      </SuperAdminOnly>

      <div className="card">
        <table className="list-table">
          <thead>
            <tr>
              <th className="center">상품명</th>
              <th className="center">벤더</th>
              <th className="center">자산 유형</th>
              <th className="center">사용 여부</th>
              <SuperAdminOnly>
                <th className="center"></th>
              </SuperAdminOnly>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={5} className="empty">
                  불러오는 중…
                </td>
              </tr>
            )}
            {!loading && items.length === 0 && (
              <tr>
                <td colSpan={5} className="empty">
                  등록된 상품이 없습니다.
                </td>
              </tr>
            )}
            {!loading &&
              items.map((p) => (
                <tr key={p.id}>
                  <td>{p.name}</td>
                  <td>{p.vendor || "-"}</td>
                  <td>{p.asset_category_label}</td>
                  <td>
                    <span className={`badge badge-asset-${p.is_active ? "available" : "expired"}`}>
                      {p.is_active ? "사용 중" : "사용 중지"}
                    </span>
                  </td>
                  <SuperAdminOnly>
                    <td>
                      <button className="ghost" onClick={() => toggleActive(p)}>
                        {p.is_active ? "사용 중지" : "다시 활성화"}
                      </button>
                    </td>
                  </SuperAdminOnly>
                </tr>
              ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
