import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { createQuote, getQuote, updateQuote } from "../api/quotes";
import { ApiError } from "../api/client";
import { useMeta } from "../hooks/useMeta";
import { useToast } from "../components/Toast";
import { ItemsEditor } from "../components/ItemsEditor";
import { computePreview } from "../lib/vat";
import { formatWon } from "../lib/money";
import type { ItemInput, QuotePayload } from "../types";

const todayIso = () => new Date().toISOString().slice(0, 10);

const BLANK: QuotePayload = {
  group_code: "A",
  title: "",
  issue_date: todayIso(),
  issuer_name: "",
  customer_name: "",
  customer_contact_name: "",
  customer_contact_phone: "",
  vat_included: true,
  items: [{ name: "", qty: 1, unit_price: 0 }],
};

export function QuoteForm({ mode }: { mode: "create" | "edit" }) {
  const { id } = useParams();
  const navigate = useNavigate();
  const meta = useMeta();
  const toast = useToast();

  const [form, setForm] = useState<QuotePayload>(BLANK);
  const [loading, setLoading] = useState(mode === "edit");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode !== "edit" || !id) return;
    let alive = true;
    getQuote(Number(id))
      .then((q) => {
        if (!alive) return;
        if (q.read_only) {
          toast.show("읽기전용 견적서는 수정할 수 없습니다.", "error");
          navigate(`/quotes/${q.id}`, { replace: true });
          return;
        }
        setForm({
          group_code: q.group_code,
          title: q.title,
          issue_date: q.issue_date,
          issuer_name: q.issuer_name,
          customer_name: q.customer_name,
          customer_contact_name: q.customer_contact_name ?? "",
          customer_contact_phone: q.customer_contact_phone ?? "",
          vat_included: q.vat_included,
          items: q.items.map((it) => ({
            name: it.name,
            qty: it.qty,
            unit_price: it.unit_price,
          })),
        });
      })
      .catch((err) =>
        toast.show(err instanceof ApiError ? err.message : "불러오기 실패", "error"),
      )
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [mode, id, navigate, toast]);

  const preview = useMemo(() => computePreview(form.items), [form.items]);

  function set<K extends keyof QuotePayload>(key: K, value: QuotePayload[K]) {
    setForm((f) => ({ ...f, [key]: value }));
  }

  function validate(): string | null {
    if (!form.title.trim()) return "견적서명을 입력하세요.";
    if (!form.issuer_name.trim()) return "발행 담당자명을 입력하세요.";
    if (!form.customer_name.trim()) return "수신처(고객사)명을 입력하세요.";
    if (form.items.length === 0) return "항목을 최소 1개 입력하세요.";
    for (const [i, it] of form.items.entries()) {
      if (!it.name.trim()) return `${i + 1}번 항목의 품목명을 입력하세요.`;
      if (!(it.qty > 0)) return `${i + 1}번 항목의 갯수는 1 이상이어야 합니다.`;
      if (!(it.unit_price > 0)) return `${i + 1}번 항목의 금액은 0보다 커야 합니다.`;
    }
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
    const payload: QuotePayload = {
      ...form,
      customer_contact_name: form.customer_contact_name || null,
      customer_contact_phone: form.customer_contact_phone || null,
      items: form.items.map((it) => ({
        name: it.name.trim(),
        qty: Number(it.qty),
        unit_price: Number(it.unit_price),
      })),
    };
    try {
      const q =
        mode === "create"
          ? await createQuote(payload)
          : await updateQuote(Number(id), payload);
      toast.show(
        mode === "create"
          ? `등록 완료 · 관리번호 ${q.mgmt_no}`
          : "수정 완료",
        "success",
      );
      navigate(`/quotes/${q.id}`, { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "저장에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  if (loading) return <div className="page">불러오는 중…</div>;

  return (
    <div className="page page-full">
      <div className="page-head">
        <h1>{mode === "create" ? "견적서 신규 등록" : "견적서 수정"}</h1>
        {mode === "edit" && (
          <button className="ghost" onClick={() => navigate(-1)}>
            취소
          </button>
        )}
      </div>

      <form onSubmit={submit}>
        <div className="card">
          <h2>기본 정보</h2>
          <div className="grid-2">
            <label>
              그룹 *
              <select
                value={form.group_code}
                onChange={(e) => set("group_code", e.target.value)}
              >
                {meta?.groups.map((g) => (
                  <option key={g.code} value={g.code}>
                    {g.code} · {g.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              견적서명 *
              <input value={form.title} onChange={(e) => set("title", e.target.value)} />
            </label>
            <label>
              견적 발행일자 *
              <input
                type="date"
                value={form.issue_date}
                onChange={(e) => set("issue_date", e.target.value)}
              />
            </label>
            <label>
              발행 담당자명 *
              <input
                value={form.issuer_name}
                onChange={(e) => set("issuer_name", e.target.value)}
              />
            </label>
          </div>
        </div>

        <div className="card">
          <h2>수신처 (고객사)</h2>
          <div className="grid-2">
            <label>
              고객사명 *
              <input
                value={form.customer_name}
                onChange={(e) => set("customer_name", e.target.value)}
              />
            </label>
            <label>
              담당자명
              <input
                value={form.customer_contact_name ?? ""}
                onChange={(e) => set("customer_contact_name", e.target.value)}
              />
            </label>
            <label>
              연락처
              <input
                value={form.customer_contact_phone ?? ""}
                onChange={(e) => set("customer_contact_phone", e.target.value)}
              />
            </label>
          </div>
          {meta && (
            <p className="muted">
              자사 정보(사업자등록번호 {meta.company.biz_no} · 대표자 {meta.company.ceo_name})는
              저장 시 자동 반영됩니다.
            </p>
          )}
        </div>

        <div className="card">
          <h2>견적 항목</h2>
          <p className="muted">금액은 공급가액(부가세 제외) 기준으로 입력합니다.</p>
          <ItemsEditor items={form.items} onChange={(items: ItemInput[]) => set("items", items)} />

          <div className="vat-row">
            <label className="inline vat-option">
              <input
                type="radio"
                checked={form.vat_included}
                onChange={() => set("vat_included", true)}
              />
              <span className="vat-option-text">
                <span>부가세 포함</span>
                <span className="vat-option-sub">(고객에게 부가세 포함가 함께 명시)</span>
              </span>
            </label>
            <label className="inline vat-option">
              <input
                type="radio"
                checked={!form.vat_included}
                onChange={() => set("vat_included", false)}
              />
              <span className="vat-option-text">
                <span>부가세 미포함</span>
                <span className="vat-option-sub">(공급가액 기준, 부가세 별도)</span>
              </span>
            </label>
          </div>

          <table className="preview preview-wide">
            <tbody>
              <tr>
                <th>항목 합계</th>
                <td>{formatWon(preview.rawTotal)}</td>
              </tr>
              <tr>
                <th>공급가액 합계 (십만단위 절사)</th>
                <td>{formatWon(preview.supplyAmount)}</td>
              </tr>
              <tr>
                <th>부가세 (10%)</th>
                <td>{formatWon(preview.vatAmount)}</td>
              </tr>
              <tr className="total">
                <th>부가세 포함가</th>
                <td>{formatWon(preview.totalWithVat)}</td>
              </tr>
            </tbody>
          </table>
        </div>

        {error && <div className="form-error">{error}</div>}

        <div className="row-gap" style={{ marginTop: 15, justifyContent: "flex-end" }}>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "저장 중…" : mode === "create" ? "등록 (상태: 제출됨)" : "수정 저장"}
          </button>
          <button type="button" className="ghost" onClick={() => navigate(-1)}>
            취소
          </button>
        </div>
      </form>
    </div>
  );
}
