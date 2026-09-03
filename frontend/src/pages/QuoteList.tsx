import { useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { downloadListXlsx, listQuotes } from "../api/quotes";
import { ApiError } from "../api/client";
import { useAuth } from "../auth";
import { useMeta } from "../hooks/useMeta";
import { useToast } from "../components/Toast";
import { SuperAdminOnly } from "../components/RoleGate";
import { StatusBadge } from "../components/StatusBadge";
import { formatWon } from "../lib/money";
import type { ListFilters, QuoteListResponse } from "../types";

const EMPTY: ListFilters = {
  mgmt_no: "",
  title: "",
  group_code: "",
  status: "",
  issue_date_from: "",
  issue_date_to: "",
  issuer_name: "",
  page: 1,
  size: 20,
};

export function QuoteList() {
  const { user } = useAuth();
  const meta = useMeta();
  const toast = useToast();
  const navigate = useNavigate();

  const [filters, setFilters] = useState<ListFilters>(EMPTY);
  const [applied, setApplied] = useState<ListFilters>(EMPTY);
  const [data, setData] = useState<QuoteListResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async (f: ListFilters) => {
    setLoading(true);
    try {
      setData(await listQuotes(f));
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "목록을 불러오지 못했습니다.", "error");
    } finally {
      setLoading(false);
    }
  }, [toast]);

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

  async function exportList() {
    try {
      await downloadListXlsx(applied);
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "엑셀 추출 실패", "error");
    }
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / (applied.size ?? 20))) : 1;
  const curPage = applied.page ?? 1;

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>견적서 목록</h1>
          <p className="muted">
            {user?.role === "GROUP_MANAGER"
              ? `그룹관리자 · 본인 그룹(${user.group_code}) 견적만 조회`
              : "전체관리자 · 전체 그룹 조회"}
          </p>
        </div>
        <div className="row-gap">
          <button onClick={exportList}>목록 엑셀</button>
          <SuperAdminOnly>
            <button className="primary" onClick={() => navigate("/quotes/new")}>
              + 신규 등록
            </button>
          </SuperAdminOnly>
        </div>
      </div>

      <form className="card filter-bar" onSubmit={search}>
        <label>
          관리번호
          <input
            value={filters.mgmt_no}
            onChange={(e) => setFilters({ ...filters, mgmt_no: e.target.value })}
            placeholder="26-A-001"
          />
        </label>
        <label>
          견적서명
          <input
            value={filters.title}
            onChange={(e) => setFilters({ ...filters, title: e.target.value })}
          />
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
        <label>
          상태
          <select
            value={filters.status}
            onChange={(e) => setFilters({ ...filters, status: e.target.value })}
          >
            <option value="">전체</option>
            {meta?.statuses.map((s) => (
              <option key={s.code} value={s.code}>
                {s.label}
              </option>
            ))}
          </select>
        </label>
        <label>
          발행일자 (from)
          <input
            type="date"
            value={filters.issue_date_from}
            onChange={(e) => setFilters({ ...filters, issue_date_from: e.target.value })}
          />
        </label>
        <label>
          발행일자 (to)
          <input
            type="date"
            value={filters.issue_date_to}
            onChange={(e) => setFilters({ ...filters, issue_date_to: e.target.value })}
          />
        </label>
        <label>
          담당자명
          <input
            value={filters.issuer_name}
            onChange={(e) => setFilters({ ...filters, issuer_name: e.target.value })}
          />
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
              <th>관리번호</th>
              <th>그룹</th>
              <th>견적서명</th>
              <th>수신처</th>
              <th>발행일자</th>
              <th className="num">공급가액</th>
              <th>부가세</th>
              <th>상태</th>
              <th>등록시간</th>
            </tr>
          </thead>
          <tbody>
            {loading && (
              <tr>
                <td colSpan={9} className="empty">
                  불러오는 중…
                </td>
              </tr>
            )}
            {!loading && data?.items.length === 0 && (
              <tr>
                <td colSpan={9} className="empty">
                  조회된 견적서가 없습니다.
                </td>
              </tr>
            )}
            {!loading &&
              data?.items.map((q) => (
                <tr key={q.id} onClick={() => navigate(`/quotes/${q.id}`)} className="clickable">
                  <td>
                    <Link to={`/quotes/${q.id}`}>{q.mgmt_no}</Link>
                  </td>
                  <td>
                    {q.group_code} · {q.group_name}
                  </td>
                  <td>{q.title}</td>
                  <td>{q.customer_name}</td>
                  <td>{q.issue_date}</td>
                  <td className="num">{formatWon(q.supply_amount)}</td>
                  <td className="num">
                    {q.vat_included ? "포함" : "별도"} / {formatWon(q.vat_amount)}
                  </td>
                  <td>
                    <StatusBadge status={q.status} />
                    {q.purchase_locked && <span className="badge badge-lock">잠금</span>}
                  </td>
                  <td>{new Date(q.created_at).toLocaleString("ko-KR")}</td>
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
