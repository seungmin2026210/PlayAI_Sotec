import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { listAssetProducts, listAssetUnits } from "../api/purchase";
import { ApiError } from "../api/client";
import { useAuth } from "../auth";
import { useMeta } from "../hooks/useMeta";
import { useToast } from "../components/Toast";
import { SuperAdminOnly } from "../components/RoleGate";
import { AssetLinkBadge, AssetStatusBadge } from "../components/StatusBadge";
import { formatWon } from "../lib/money";
import type { AssetProduct, AssetUnitListFilters, AssetUnitListResponse } from "../types";

const EMPTY: AssetUnitListFilters = { product_id: "", status: "", group_code: "", page: 1, size: 20 };

export function PurchaseList() {
  const { user } = useAuth();
  const meta = useMeta();
  const toast = useToast();
  const navigate = useNavigate();

  const [products, setProducts] = useState<AssetProduct[]>([]);
  const [filters, setFilters] = useState<AssetUnitListFilters>(EMPTY);
  const [applied, setApplied] = useState<AssetUnitListFilters>(EMPTY);
  const [data, setData] = useState<AssetUnitListResponse | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listAssetProducts()
      .then((r) => setProducts(r.items))
      .catch(() => {
        /* 필터용 — 실패해도 목록 자체는 계속 보여줌 */
      });
  }, []);

  const load = useCallback(
    async (f: AssetUnitListFilters) => {
      setLoading(true);
      try {
        setData(await listAssetUnits(f));
      } catch (err) {
        toast.show(err instanceof ApiError ? err.message : "목록을 불러오지 못했습니다.", "error");
      } finally {
        setLoading(false);
      }
    },
    [toast],
  );

  useEffect(() => {
    load(applied);
  }, [applied, load]);

  function search(e: React.FormEvent) {
    e.preventDefault();
    setApplied({ ...filters, page: 1 });
  }
  function reset() {
    setFilters(EMPTY);
    setApplied(EMPTY);
  }
  function gotoPage(p: number) {
    setApplied((a) => ({ ...a, page: p }));
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / (applied.size ?? 20))) : 1;
  const curPage = applied.page ?? 1;

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>구매관리</h1>
          <p className="muted">
            {user?.role === "GROUP_MANAGER"
              ? `그룹관리자 · 본인 그룹(${user.group_code}) 자산만 조회`
              : "전체관리자 · 전체 그룹 조회"}
          </p>
        </div>
        <div className="row-gap">
          <button className="ghost" onClick={() => navigate("/purchase/products")}>
            상품 관리
          </button>
          <SuperAdminOnly>
            <button className="primary" onClick={() => navigate("/purchase/new")}>
              + 신규 구매 등록
            </button>
          </SuperAdminOnly>
        </div>
      </div>

      <form className="card filter-bar" onSubmit={search}>
        <label>
          상품
          <select
            value={filters.product_id}
            onChange={(e) => setFilters({ ...filters, product_id: e.target.value })}
          >
            <option value="">전체</option>
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          상태
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">전체</option>
            <option value="AVAILABLE">재고</option>
            <option value="ASSIGNED">배정됨</option>
            <option value="EXPIRED">만료</option>
          </select>
        </label>
        <label>
          그룹
          <select
            value={filters.group_code}
            disabled={user?.role === "GROUP_MANAGER"}
            onChange={(e) => setFilters({ ...filters, group_code: e.target.value })}
          >
            <option value="">전체</option>
            {meta?.groups.map((g) => (
              <option key={g.code} value={g.code}>
                {g.code} · {g.name}
              </option>
            ))}
          </select>
        </label>
        <div className="filter-actions">
          <button type="submit">검색</button>
          <button type="button" className="ghost" onClick={reset}>
            초기화
          </button>
        </div>
      </form>

      <div className="card">
        <table className="list-table">
          <thead>
            <tr>
              <th className="center">유닛번호</th>
              <th className="center">상품</th>
              <th className="center">자산 유형</th>
              <th className="center">그룹</th>
              <th className="center">구매일자</th>
              <th className="num">금액</th>
              <th className="center">상태</th>
              <th className="center">자산 등록</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={8} className="empty">
                  불러오는 중…
                </td>
              </tr>
            )}
            {!loading && data?.items.length === 0 && (
              <tr>
                <td colSpan={8} className="empty">
                  조회된 자산이 없습니다.
                </td>
              </tr>
            )}
            {!loading &&
              data?.items.map((u) => (
                <tr key={u.id} onClick={() => navigate(`/purchase/${u.id}`)} className="clickable">
                  <td>
                    <Link to={`/purchase/${u.id}`}>{u.unit_no}</Link>
                  </td>
                  <td>{u.product_name}</td>
                  <td>{u.asset_category_label}</td>
                  <td>
                    {u.group_code} · {u.group_name}
                  </td>
                  <td>{u.purchase_date}</td>
                  <td className="num">{formatWon(u.price)}</td>
                  <td>
                    <AssetStatusBadge status={u.status} />
                  </td>
                  <td>{u.asset_link_label ? <AssetLinkBadge unit={u} /> : "-"}</td>
                </tr>
              ))}
          </tbody>
        </table>

        <div className="pager">
          <button disabled={curPage <= 1} onClick={() => gotoPage(curPage - 1)}>
            이전
          </button>
          <span>
            {curPage} / {totalPages} (총 {data?.total ?? 0}건)
          </span>
          <button disabled={curPage >= totalPages} onClick={() => gotoPage(curPage + 1)}>
            다음
          </button>
        </div>
      </div>
    </div>
  );
}
