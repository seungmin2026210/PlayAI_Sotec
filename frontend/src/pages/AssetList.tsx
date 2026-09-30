import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, Navigate, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { downloadAssetList, listAssets, listImportable, renewAssets } from "../api/assets";
import { listMembers } from "../api/members";
import { ApiError } from "../api/client";
import { useAuth } from "../auth";
import { useMeta } from "../hooks/useMeta";
import { useToast } from "../components/Toast";
import { SuperAdminOnly } from "../components/RoleGate";
import { AssetTabs, CATEGORY_LABEL, categoryPath, slugToCategory } from "../components/AssetTabs";
import { AssetStateBadge, ExpiryBadgeView } from "../components/AssetBadges";
import { Modal } from "../components/Modal";
import { addDays } from "../lib/date";
import type { AssetCategory, AssetListItem, AssetListResponse, AssetUnit, Member } from "../types";

const FILTER_KEYS = ["subcategory", "member_id", "group", "status", "expiry", "year", "name", "valid_to", "q"] as const;
type FilterKey = (typeof FILTER_KEYS)[number];
type Filters = Record<FilterKey, string>;

function fromParams(sp: URLSearchParams): Filters {
  return Object.fromEntries(FILTER_KEYS.map((k) => [k, sp.get(k) ?? ""])) as Filters;
}

export function AssetList() {
  const { category: slug } = useParams();
  const category = slugToCategory(slug);
  if (!category) return <Navigate to="/assets/sw" replace />;
  return <AssetListInner key={category} category={category} />;
}

function AssetListInner({ category }: { category: AssetCategory }) {
  const { user } = useAuth();
  const meta = useMeta();
  const toast = useToast();
  const navigate = useNavigate();
  const [sp, setSp] = useSearchParams();

  const applied = useMemo(() => fromParams(sp), [sp]);
  const page = Number(sp.get("page") ?? "1") || 1;
  const size = 20;
  const [draft, setDraft] = useState<Filters>(applied);
  const [data, setData] = useState<AssetListResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [members, setMembers] = useState<Member[]>([]);
  const [selected, setSelected] = useState<Record<string, AssetListItem>>({});
  const [renewOpen, setRenewOpen] = useState(false);

  useEffect(() => setDraft(applied), [applied]);
  useEffect(() => {
    listMembers()
      .then((r) => setMembers(r.items))
      .catch(() => setMembers([]));
  }, []);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      setData(await listAssets({ category, ...applied, page, size }));
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "목록을 불러오지 못했습니다.", "error");
    } finally {
      setLoading(false);
    }
  }, [category, applied, page, toast]);

  useEffect(() => {
    load();
  }, [load]);

  function apply(f: Filters, p = 1) {
    const next = new URLSearchParams();
    for (const k of FILTER_KEYS) if (f[k]) next.set(k, f[k]);
    if (p > 1) next.set("page", String(p));
    setSp(next);
    setSelected({});
  }

  async function onExcel() {
    try {
      await downloadAssetList({ category, ...applied });
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "다운로드 실패", "error");
    }
  }

  const sel = Object.values(selected);
  const renewable =
    sel.length > 0 &&
    sel.every((a) => a.valid_to && a.valid_to === sel[0].valid_to && a.name === sel[0].name && !a.read_only);

  function toggle(a: AssetListItem) {
    setSelected((cur) => {
      const next = { ...cur };
      if (next[a.asset_no]) delete next[a.asset_no];
      else next[a.asset_no] = a;
      return next;
    });
  }

  const subs = meta?.asset_subcategories?.[category] ?? [];
  const totalPages = data ? Math.max(1, Math.ceil(data.total / size)) : 1;
  const isAdmin = user?.role === "SUPER_ADMIN";
  const typedCol = category === "SW" ? "버전" : category === "HW" ? "모델명" : "강의명";
  const typedVal = (a: AssetListItem) => (category === "SW" ? a.version : category === "HW" ? a.model : a.course_title);
  const colCount = 10 + (isAdmin ? 1 : 0);
  const yearNow = new Date().getFullYear();

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>자산관리</h1>
          <p className="muted">
            {user?.role === "GROUP_MANAGER"
              ? `그룹관리자 · 본인 그룹(${user.group_code}) 자산만 조회`
              : "전체관리자 · 전체 그룹 조회"}
          </p>
        </div>
        <div className="row-gap">
          <button className="ghost" onClick={onExcel}>
            엑셀 다운로드
          </button>
          <SuperAdminOnly>
            <button onClick={() => navigate(`${categoryPath(category)}/import`)}>구매에서 가져오기</button>
            <button className="primary" onClick={() => navigate(`${categoryPath(category)}/new`)}>
              + 직접 등록
            </button>
          </SuperAdminOnly>
        </div>
      </div>

      <AssetTabs />

      <form
        className="card filter-bar"
        onSubmit={(e) => {
          e.preventDefault();
          apply(draft);
        }}
      >
        {category !== "EDU" && (
          <label>
            소분류
            <select value={draft.subcategory} onChange={(e) => setDraft({ ...draft, subcategory: e.target.value })}>
              <option value="">전체</option>
              {subs.map((s) => (
                <option key={s.code} value={s.code}>
                  {s.label}
                </option>
              ))}
            </select>
          </label>
        )}
        <label>
          사용자
          <select value={draft.member_id} onChange={(e) => setDraft({ ...draft, member_id: e.target.value })}>
            <option value="">전체</option>
            {category !== "EDU" && <option value="SHARED">공용</option>}
            {members.map((m) => (
              <option key={m.employee_no} value={m.employee_no}>
                {m.name} ({m.employee_no}){m.active ? "" : " · 퇴사"}
              </option>
            ))}
          </select>
        </label>
        <label>
          그룹
          <select
            value={draft.group}
            disabled={user?.role === "GROUP_MANAGER"}
            onChange={(e) => setDraft({ ...draft, group: e.target.value })}
          >
            <option value="">전체</option>
            {meta?.groups.map((g) => (
              <option key={g.code} value={g.code}>
                {g.code} · {g.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          상태
          <select value={draft.status} onChange={(e) => setDraft({ ...draft, status: e.target.value })}>
            <option value="">전체(폐기·삭제 제외)</option>
            <option value="IDLE">미사용</option>
            <option value="IN_USE">사용 중</option>
            <option value="DISPOSED">폐기</option>
            {isAdmin && <option value="DELETED">삭제됨</option>}
          </select>
        </label>
        <label>
          만료 여부
          <select value={draft.expiry} onChange={(e) => setDraft({ ...draft, expiry: e.target.value })}>
            <option value="">전체</option>
            <option value="expired">만료</option>
            <option value="expiring">30일 내</option>
            <option value="ok">정상</option>
          </select>
        </label>
        <label>
          구매 연도
          <select value={draft.year} onChange={(e) => setDraft({ ...draft, year: e.target.value })}>
            <option value="">전체</option>
            {Array.from({ length: 8 }, (_, i) => yearNow - i).map((y) => (
              <option key={y} value={y}>
                {y}
              </option>
            ))}
          </select>
        </label>
        <label style={{ gridColumn: "span 2" }}>
          키워드
          <input
            value={draft.q}
            placeholder={isAdmin ? "자산번호·품명·시리얼/키·계정·모델·강의명·견적/계약번호·비고" : "자산번호·품명·시리얼·계정·모델·강의명·견적/계약번호·비고"}
            onChange={(e) => setDraft({ ...draft, q: e.target.value })}
          />
        </label>
        {(applied.name || applied.valid_to) && (
          <div className="filter-actions">
            <span className="chip">
              품명 "{applied.name}" · 종료일 {applied.valid_to}
              <button type="button" className="link-danger" onClick={() => apply({ ...applied, name: "", valid_to: "" })}>
                ✕
              </button>
            </span>
          </div>
        )}
        <div className="filter-actions" style={{ justifyContent: "flex-end" }}>
          <button type="submit">검색</button>
          <button type="button" className="ghost" onClick={() => apply(fromParams(new URLSearchParams()))}>
            초기화
          </button>
        </div>
      </form>

      <div className="card">
        <SuperAdminOnly>
          <div className="row-gap" style={{ justifyContent: "flex-end", alignItems: "center", marginBottom: 10 }}>
            <span className="muted">
              {sel.length ? `${sel.length}건 선택됨` : "같은 품명·같은 종료일 자산을 체크하면 한꺼번에 갱신할 수 있습니다."}
            </span>
            <button
              type="button"
              className="primary"
              disabled={!renewable}
              title={sel.length && !renewable ? "품명과 종료일이 같은 자산끼리만 갱신할 수 있습니다." : undefined}
              onClick={() => setRenewOpen(true)}
            >
              갱신{sel.length ? ` (${sel.length}건)` : ""}
            </button>
          </div>
        </SuperAdminOnly>
        <table className="list-table">
          <thead>
            <tr>
              {isAdmin && <th />}
              <th>자산번호</th>
              <th>소분류</th>
              <th>품명</th>
              <th>{typedCol}</th>
              <th>현재 사용자</th>
              <th>사용 시작일</th>
              <th>유효기간 종료</th>
              <th>그룹</th>
              <th>상태</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={colCount} className="empty">
                  불러오는 중…
                </td>
              </tr>
            )}
            {!loading && data?.items.length === 0 && (
              <tr>
                <td colSpan={colCount} className="empty">
                  조회된 {CATEGORY_LABEL[category]} 자산이 없습니다.
                </td>
              </tr>
            )}
            {!loading &&
              data?.items.map((a) => (
                <tr key={a.asset_no} className={a.read_only ? "dim" : undefined}>
                  {isAdmin && (
                    <td>
                      <input
                        type="checkbox"
                        style={{ width: "auto" }}
                        checked={Boolean(selected[a.asset_no])}
                        disabled={!a.valid_to || a.read_only}
                        onChange={() => toggle(a)}
                      />
                    </td>
                  )}
                  <td>
                    <Link to={`/assets/item/${a.asset_no}`}>{a.asset_no}</Link>
                  </td>
                  <td>{a.subcategory_label ?? "-"}</td>
                  <td>{a.name}</td>
                  <td>{typedVal(a) ?? "-"}</td>
                  <td>{a.current_member_name ?? (a.current_shared_label ? `공용 · ${a.current_shared_label}` : "-")}</td>
                  <td>{a.current_start_date ?? "-"}</td>
                  <td>
                    {a.valid_to ?? "-"} <ExpiryBadgeView badge={a.expiry_badge} />
                  </td>
                  <td>{a.scope_group_name}</td>
                  <td>
                    <AssetStateBadge status={a.status} />
                  </td>
                  <td>
                    <Link to={`/assets/item/${a.asset_no}`}>상세</Link>
                  </td>
                </tr>
              ))}
          </tbody>
        </table>

        <div className="pager">
          <button disabled={page <= 1} onClick={() => apply(applied, page - 1)}>
            이전
          </button>
          <span>
            {page} / {totalPages} (총 {data?.total ?? 0}건)
          </span>
          <button disabled={page >= totalPages} onClick={() => apply(applied, page + 1)}>
            다음
          </button>
        </div>
      </div>

      {renewOpen && (
        <RenewModal
          category={category}
          assets={sel}
          onClose={() => setRenewOpen(false)}
          onDone={() => {
            setRenewOpen(false);
            setSelected({});
            load();
          }}
        />
      )}
    </div>
  );
}

function RenewModal({
  category,
  assets,
  onClose,
  onDone,
}: {
  category: AssetCategory;
  assets: AssetListItem[];
  onClose: () => void;
  onDone: () => void;
}) {
  const toast = useToast();
  const prevTo = assets[0].valid_to ?? "";
  const [validTo, setValidTo] = useState("");
  const [validFrom, setValidFrom] = useState(prevTo ? addDays(prevTo, 1) : "");
  const [unitNo, setUnitNo] = useState("");
  const [units, setUnits] = useState<AssetUnit[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    listImportable(category)
      .then(setUnits)
      .catch(() => setUnits([]));
  }, [category]);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!validTo) return setError("새 종료일을 입력하세요.");
    if (validTo <= prevTo) return setError(`새 종료일은 기존 종료일(${prevTo})보다 뒤여야 합니다.`);
    setBusy(true);
    try {
      await renewAssets({
        asset_nos: assets.map((a) => a.asset_no),
        new_valid_to: validTo,
        new_valid_from: validFrom || null,
        unit_no: unitNo || null,
      });
      toast.show(`${assets.length}건 갱신했습니다.`, "success");
      onDone();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "갱신 실패");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal title={`갱신 — ${assets[0].name} ${assets.length}건`} onClose={onClose}>
      <form onSubmit={submit} className="stack">
        <p className="muted">
          기존 종료일 {prevTo}. 번호·사용자는 그대로 두고 유효기간만 연장합니다.
        </p>
        <div className="grid-2">
          <label>
            새 시작일
            <input type="date" value={validFrom} onChange={(e) => setValidFrom(e.target.value)} />
          </label>
          <label>
            새 종료일 *
            <input type="date" value={validTo} min={prevTo} onChange={(e) => setValidTo(e.target.value)} />
          </label>
        </div>
        <label>
          갱신 구매 기록 연결 (선택)
          <select value={unitNo} onChange={(e) => setUnitNo(e.target.value)}>
            <option value="">연결 안 함</option>
            {units.map((u) => (
              <option key={u.unit_no} value={u.unit_no}>
                {u.unit_no} · {u.purchase_date} · {u.price.toLocaleString("ko-KR")}원
              </option>
            ))}
          </select>
        </label>
        {error && <div className="form-error">{error}</div>}
        <div className="row-gap" style={{ justifyContent: "flex-end" }}>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "처리 중…" : "갱신"}
          </button>
          <button type="button" className="ghost" onClick={onClose}>
            취소
          </button>
        </div>
      </form>
    </Modal>
  );
}
