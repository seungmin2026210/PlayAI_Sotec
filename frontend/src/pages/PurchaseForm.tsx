import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { createAssetUnit, listAssetProducts } from "../api/purchase";
import { listQuotes } from "../api/quotes";
import { ApiError } from "../api/client";
import { useMeta } from "../hooks/useMeta";
import { useToast } from "../components/Toast";
import type { AssetProduct, AssetUnitPayload, AssetUnitType, QuoteListItem } from "../types";

const todayIso = () => new Date().toISOString().slice(0, 10);

const BLANK: AssetUnitPayload = {
  product_id: "",
  purchase_date: todayIso(),
  purchased_from: "",
  price: 0,
  unit_type: null,
  key_value: "",
  expire_date: null,
  group_code: "A",
  source_quote_id: null,
};

export function PurchaseForm() {
  const navigate = useNavigate();
  const meta = useMeta();
  const toast = useToast();

  const [products, setProducts] = useState<AssetProduct[]>([]);
  const [approvedQuotes, setApprovedQuotes] = useState<QuoteListItem[]>([]);
  const [form, setForm] = useState<AssetUnitPayload>(BLANK);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listAssetProducts(true)
      .then((r) => {
        setProducts(r.items);
        if (r.items.length > 0) setForm((f) => ({ ...f, product_id: f.product_id || r.items[0].id }));
      })
      .catch((err) => toast.show(err instanceof ApiError ? err.message : "상품 목록을 불러오지 못했습니다.", "error"));
    listQuotes({ status: "APPROVED", page: 1, size: 100 })
      .then((r) => setApprovedQuotes(r.items))
      .catch(() => {
        /* 견적 연동은 선택사항 — 실패해도 폼은 계속 사용 가능 */
      });
  }, [toast]);

  const selectedProduct = products.find((p) => p.id === form.product_id);
  const showUnitType = selectedProduct?.asset_category === "SW";

  function set<K extends keyof AssetUnitPayload>(key: K, value: AssetUnitPayload[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function validate(): string | null {
    if (!form.product_id) return "상품을 선택하세요.";
    if (!(form.price > 0)) return "금액은 0보다 커야 합니다.";
    return null;
  }

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const v = validate();
    if (v) {
      setError(v);
      return;
    }
    setError(null);
    setBusy(true);
    const payload: AssetUnitPayload = {
      ...form,
      price: Number(form.price),
      purchased_from: form.purchased_from || null,
      key_value: form.key_value || null,
      unit_type: showUnitType ? form.unit_type : null,
      expire_date: form.expire_date || null,
      source_quote_id: form.source_quote_id || null,
    };
    try {
      const unit = await createAssetUnit(payload);
      toast.show(`등록 완료 · 유닛번호 ${unit.unit_no}`, "success");
      navigate(`/purchase/${unit.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "저장에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="page page-full">
      <div className="page-head">
        <h1>신규 구매 등록</h1>
        <button className="ghost" onClick={() => navigate(-1)}>
          취소
        </button>
      </div>

      <form onSubmit={submit}>
        <div className="card">
          <h2>구매 정보</h2>
          <div className="grid-2">
            <label>
              상품 *
              <select value={form.product_id} onChange={(e) => set("product_id", e.target.value)}>
                {products.length === 0 && <option value="">등록된 상품 없음</option>}
                {products.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name} ({p.asset_category_label})
                  </option>
                ))}
              </select>
            </label>
            <label>
              그룹 *
              <select value={form.group_code} onChange={(e) => set("group_code", e.target.value)}>
                {meta?.groups.map((g) => (
                  <option key={g.code} value={g.code}>
                    {g.code} · {g.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              구매일자 *
              <input
                type="date"
                value={form.purchase_date}
                onChange={(e) => set("purchase_date", e.target.value)}
              />
            </label>
            <label>
              구매처
              <input
                value={form.purchased_from ?? ""}
                onChange={(e) => set("purchased_from", e.target.value)}
              />
            </label>
            <label>
              금액 (원) *
              <input
                type="number"
                min={1}
                value={form.price || ""}
                onChange={(e) => set("price", Number(e.target.value))}
              />
            </label>
            <label>
              만료일 (선택, 비우면 무기한)
              <input
                type="date"
                value={form.expire_date ?? ""}
                onChange={(e) => set("expire_date", e.target.value || null)}
              />
            </label>
          </div>

          {showUnitType && (
            <>
              <div className="vat-row">
                <label className="inline vat-option">
                  <input
                    type="radio"
                    checked={form.unit_type === "KEY"}
                    onChange={() => set("unit_type", "KEY" as AssetUnitType)}
                  />
                  <span className="vat-option-text">
                    <span>키 방식</span>
                    <span className="vat-option-sub">라이선스 키 문자열로 배정</span>
                  </span>
                </label>
                <label className="inline vat-option">
                  <input
                    type="radio"
                    checked={form.unit_type === "ACCOUNT"}
                    onChange={() => set("unit_type", "ACCOUNT" as AssetUnitType)}
                  />
                  <span className="vat-option-text">
                    <span>계정 방식</span>
                    <span className="vat-option-sub">벤더 홈페이지에서 계정으로 배정</span>
                  </span>
                </label>
              </div>
              <label>
                키 값 / 계정 값
                <input
                  value={form.key_value ?? ""}
                  onChange={(e) => set("key_value", e.target.value)}
                  placeholder={form.unit_type === "ACCOUNT" ? "배정용 계정 이메일 등" : "라이선스 키"}
                />
              </label>
            </>
          )}
        </div>

        <div className="card">
          <h2>견적 연동 (선택)</h2>
          <p className="muted">
            승인된 견적서에서 이어서 구매하는 경우 선택하세요. 선택 시 해당 견적서가 자동으로
            잠깁니다(이후 수정 불가).
          </p>
          <label>
            연동 견적서
            <select
              value={form.source_quote_id ?? ""}
              onChange={(e) => set("source_quote_id", e.target.value || null)}
            >
              <option value="">선택 안 함</option>
              {approvedQuotes.map((q) => (
                <option key={q.id} value={q.id}>
                  {q.mgmt_no} · {q.title}
                </option>
              ))}
            </select>
          </label>
        </div>

        {error && <div className="form-error">{error}</div>}

        <div className="row-gap" style={{ marginTop: 15, justifyContent: "flex-end" }}>
          <button type="submit" className="primary" disabled={busy || products.length === 0}>
            {busy ? "저장 중…" : "등록"}
          </button>
          <button type="button" className="ghost" onClick={() => navigate(-1)}>
            취소
          </button>
        </div>
      </form>
    </div>
  );
}
