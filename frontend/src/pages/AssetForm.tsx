import { useEffect, useState } from "react";
import { Navigate, useLocation, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { createAssets, deletePassword, getAsset, importAssets, listImportable, updateAsset } from "../api/assets";
import { ApiError } from "../api/client";
import { useMeta } from "../hooks/useMeta";
import { useToast } from "../components/Toast";
import { CATEGORY_LABEL, categoryPath, slugToCategory } from "../components/AssetTabs";
import { MoneyInput } from "../components/MoneyInput";
import type { Asset, AssetCategory, AssetFields, AssetUnit } from "../types";

const BLANK: AssetFields = {
  subcategory: null, name: "", group_code: "A", purchase_date: null, price: null, purchased_from: null,
  quote_no: null, contract_no: null, valid_from: null, valid_to: null, version: null, license_key: null,
  account_id: null, password: null, manufacturer: null, model: null, serial_no: null, mac_address: null,
  course_title: null, course_url: null, note: null,
};

/** 구매 유닛 → 폼 기본값(COORDINATION C5, 서버 asset_registration.unit_defaults 와 같은 매핑). */
function fromUnit(u: AssetUnit): AssetFields {
  return {
    ...BLANK,
    name: u.product_name,
    group_code: u.group_code,
    purchase_date: u.purchase_date,
    price: u.price,
    purchased_from: u.purchased_from,
    quote_no: u.source_quote_id,
    valid_to: u.expire_date,
    course_title: u.asset_category === "EDU" ? u.product_name : null,
    license_key: u.unit_type === "KEY" && u.asset_category === "SW" ? u.key_value : null,
    account_id: u.unit_type === "ACCOUNT" ? u.key_value : null,
  };
}

function fromAsset(a: Asset): AssetFields {
  const f = { ...BLANK };
  for (const k of Object.keys(BLANK) as (keyof AssetFields)[]) {
    if (k !== "password") (f as Record<string, unknown>)[k] = (a as unknown as Record<string, unknown>)[k] ?? null;
  }
  return f;
}

/** /assets/:category/new(직접 등록 · ?unit= 가져오기) 와 /assets/item/:assetNo/edit(수정) 공용. */
export function AssetForm({ mode }: { mode: "create" | "edit" }) {
  const { category: slug, assetNo } = useParams();
  const [sp] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const meta = useMeta();
  const toast = useToast();

  const unitNo = mode === "create" ? sp.get("unit") : null;
  const [category, setCategory] = useState<AssetCategory | null>(mode === "create" ? slugToCategory(slug) : null);
  const [form, setForm] = useState<AssetFields>(BLANK);
  const [quantity, setQuantity] = useState(1);
  const [unit, setUnit] = useState<AssetUnit | null>((location.state as { unit?: AssetUnit } | null)?.unit ?? null);
  const [asset, setAsset] = useState<Asset | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (mode === "edit" && assetNo) {
      getAsset(assetNo)
        .then((a) => {
          setAsset(a);
          setCategory(a.category);
          setForm(fromAsset(a));
        })
        .catch((err) => toast.show(err instanceof ApiError ? err.message : "불러오기 실패", "error"));
    }
  }, [mode, assetNo, toast]);

  useEffect(() => {
    if (!unitNo || !category) return;
    if (unit && unit.unit_no === unitNo) {
      setForm(fromUnit(unit));
      return;
    }
    listImportable(category)
      .then((us) => {
        const u = us.find((x) => x.unit_no === unitNo);
        if (u) setUnit(u);
        else setError("가져올 수 없는 구매 기록입니다(이미 가져왔거나 폐기됨).");
      })
      .catch(() => setError("구매 기록을 불러오지 못했습니다."));
  }, [unitNo, category, unit]);

  if (mode === "create" && !category) return <Navigate to="/assets/sw" replace />;
  if (!category) return <div className="page">불러오는 중…</div>;

  function set<K extends keyof AssetFields>(k: K, v: AssetFields[K]) {
    setForm((f) => ({ ...f, [k]: v }));
  }
  const text = (k: keyof AssetFields, label: string, props: Record<string, unknown> = {}) => (
    <label>
      {label}
      <input value={(form[k] as string | null) ?? ""} onChange={(e) => set(k, (e.target.value || null) as never)} {...props} />
    </label>
  );
  const dateInput = (k: keyof AssetFields, label: string) => (
    <label>
      {label}
      <input type="date" value={(form[k] as string | null) ?? ""} onChange={(e) => set(k, (e.target.value || null) as never)} />
    </label>
  );

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!form.name.trim()) return setError("품명을 입력하세요.");
    if (form.valid_from && form.valid_to && form.valid_to < form.valid_from)
      return setError("유효기간 종료일은 시작일보다 앞설 수 없습니다.");
    setError(null);
    setBusy(true);
    const payload = { ...form, password: form.password || null };
    try {
      if (mode === "edit" && asset) {
        await updateAsset(asset.asset_no, payload);
        toast.show("저장했습니다.", "success");
        navigate(`/assets/item/${asset.asset_no}`, { replace: true });
        return;
      }
      const res = unitNo
        ? await importAssets(unitNo, quantity, payload)
        : await createAssets(category!, quantity, payload);
      const nos = res.asset_nos;
      toast.show(`등록 완료 · ${nos[0]}${nos.length > 1 ? ` ~ ${nos[nos.length - 1]} (${nos.length}건)` : ""}`, "success");
      navigate(nos.length === 1 ? `/assets/item/${nos[0]}` : categoryPath(category!), { replace: true });
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "저장에 실패했습니다.");
    } finally {
      setBusy(false);
    }
  }

  async function onDeletePassword() {
    if (!asset || !window.confirm("저장된 비밀번호를 삭제할까요?")) return;
    try {
      const a = await deletePassword(asset.asset_no);
      setAsset(a);
      toast.show("비밀번호를 삭제했습니다.", "success");
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "삭제 실패", "error");
    }
  }

  const subs = meta?.asset_subcategories?.[category] ?? [];
  const title =
    mode === "edit"
      ? `${asset?.asset_no ?? ""} 수정`
      : unitNo
        ? `구매에서 가져오기 · ${unitNo}`
        : `${CATEGORY_LABEL[category]} 자산 직접 등록`;
  const hasPasswordField = category === "SW" || category === "EDU";

  return (
    <div className="page page-full">
      <div className="page-head">
        <h1>{title}</h1>
        <button className="ghost" onClick={() => navigate(-1)}>
          취소
        </button>
      </div>

      <form onSubmit={submit}>
        <div className="card">
          <h2>기본 정보</h2>
          <div className="grid-2">
            {mode === "create" && (
              <label>
                수량 *
                <input type="number" min={1} max={100} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} />
                <span className="hint">같은 내용의 자산을 수량만큼 연속 번호로 만듭니다. 시리얼·계정 등은 등록 후 각각 수정하세요.</span>
              </label>
            )}
            {subs.length > 0 && (
              <label>
                소분류
                <select value={form.subcategory ?? ""} onChange={(e) => set("subcategory", e.target.value || null)}>
                  <option value="">선택 안 함</option>
                  {subs.map((s) => (
                    <option key={s.code} value={s.code}>
                      {s.label}
                    </option>
                  ))}
                </select>
              </label>
            )}
            <label>
              품명 *
              <input value={form.name} onChange={(e) => set("name", e.target.value)} placeholder="예: GitHub Copilot Business" />
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
              <span className="hint">미사용·공용일 때의 소속 그룹</span>
            </label>
          </div>
        </div>

        <div className="card">
          <h2>구매 · 계약</h2>
          <div className="grid-2">
            <label>
              구매일
              <input
                type="date"
                value={form.purchase_date ?? ""}
                onChange={(e) => set("purchase_date", e.target.value || null)}
              />
              {mode === "create" && <span className="hint">자산번호 연도 기준(비우면 올해). 등록 후 고쳐도 번호는 그대로입니다.</span>}
            </label>
            <label>
              {unitNo ? "구매 총액 (원, 수량으로 나눠 기록)" : "금액 (원)"}
              <MoneyInput value={form.price} onChange={(v) => set("price", v || null)} />
            </label>
            {text("purchased_from", "구매처")}
            {text("quote_no", "견적번호")}
            {text("contract_no", "계약번호 (임시 자유입력)")}
          </div>
        </div>

        <div className="card">
          <h2>유효기간</h2>
          <div className="grid-2">
            {dateInput("valid_from", "시작일")}
            {dateInput("valid_to", "종료일 (갱신일)")}
          </div>
        </div>

        <div className="card">
          <h2>{CATEGORY_LABEL[category]} 정보</h2>
          <div className="grid-2">
            {category === "SW" && (
              <>
                {text("version", "버전")}
                {text("license_key", "시리얼 / 라이선스키")}
                {text("account_id", "로그인 계정(ID)")}
              </>
            )}
            {category === "HW" && (
              <>
                {text("manufacturer", "제조사")}
                {text("model", "모델명")}
                {text("serial_no", "제품 시리얼")}
                {text("mac_address", "MAC 주소")}
              </>
            )}
            {category === "EDU" && (
              <>
                {text("course_title", "강의명")}
                {text("course_url", "강의 URL")}
                {text("account_id", "인프런 계정(ID)")}
              </>
            )}
            {hasPasswordField && (
              <label>
                비밀번호
                <input
                  type="password"
                  autoComplete="new-password"
                  value={form.password ?? ""}
                  onChange={(e) => set("password", e.target.value || null)}
                  placeholder={mode === "edit" && asset?.has_password ? "비워두면 기존 비밀번호 유지" : ""}
                />
                <span className="hint">
                  암호화해서 저장합니다.
                  {mode === "edit" && asset?.has_password && (
                    <>
                      {" "}
                      <button type="button" className="link-danger" onClick={onDeletePassword}>
                        비밀번호 삭제
                      </button>
                    </>
                  )}
                </span>
              </label>
            )}
          </div>
          {text("note", "비고")}
        </div>

        {error && <div className="form-error">{error}</div>}

        <div className="row-gap" style={{ marginTop: 15, justifyContent: "flex-end" }}>
          <button type="submit" className="primary" disabled={busy || (Boolean(unitNo) && !unit)}>
            {busy ? "저장 중…" : mode === "edit" ? "저장" : "등록"}
          </button>
          <button type="button" className="ghost" onClick={() => navigate(-1)}>
            취소
          </button>
        </div>
      </form>
    </div>
  );
}
