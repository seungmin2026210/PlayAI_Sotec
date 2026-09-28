import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { getMember } from "../api/members";
import { ApiError } from "../api/client";
import { useToast } from "../components/Toast";
import { AssetTabs, CATEGORY_LABEL } from "../components/AssetTabs";
import type { MemberDetail as MemberDetailT, MemberHistoryRow } from "../types";

/** 한 사람이 지금 쓰는 자산 전체 + 과거 이력. 다른 그룹 스코프 자산은 링크 없음(D37). */
export function MemberDetail() {
  const { employeeNo = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [m, setM] = useState<MemberDetailT | null>(null);

  useEffect(() => {
    getMember(employeeNo)
      .then(setM)
      .catch((err) => {
        toast.show(err instanceof ApiError ? err.message : "불러오기 실패", "error");
        navigate("/assets/members", { replace: true });
      });
  }, [employeeNo, navigate, toast]);

  if (!m) return <div className="page">불러오는 중…</div>;
  const current = m.assignments.filter((a) => a.end_date === null);
  const past = m.assignments.filter((a) => a.end_date !== null);

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>
            {m.name} {!m.active && <span className="badge badge-a-disposed">퇴사</span>}
          </h1>
          <p className="muted">
            {m.employee_no} · {m.group_name} · SW {m.counts.SW} / HW {m.counts.HW} / 교육 {m.counts.EDU}
          </p>
        </div>
        <button className="ghost" onClick={() => navigate("/assets/members")}>
          목록으로
        </button>
      </div>

      <AssetTabs />

      <HistoryTable title="지금 쓰는 자산" rows={current} empty="사용 중인 자산이 없습니다." showEnd={false} />
      <HistoryTable title="과거에 썼던 자산" rows={past} empty="과거 이력이 없습니다." showEnd />
    </div>
  );
}

function HistoryTable({ title, rows, empty, showEnd }: { title: string; rows: MemberHistoryRow[]; empty: string; showEnd: boolean }) {
  const cols = showEnd ? 6 : 5;
  return (
    <div className="card">
      <h2>{title}</h2>
      <table className="list-table">
        <thead>
          <tr>
            <th>자산번호</th>
            <th>유형</th>
            <th>품명</th>
            <th>시작일</th>
            {showEnd && <th>종료일</th>}
            <th>비고</th>
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={cols} className="empty">
                {empty}
              </td>
            </tr>
          )}
          {rows.map((r) => (
            <tr key={r.id}>
              <td>
                {r.linkable ? (
                  <Link to={`/assets/item/${r.asset_no}`}>{r.asset_no}</Link>
                ) : (
                  <>
                    {r.asset_no} <span className="muted">(현재 다른 그룹 사용 중)</span>
                  </>
                )}
              </td>
              <td>{CATEGORY_LABEL[r.category]}</td>
              <td>{r.asset_name}</td>
              <td>{r.start_date}</td>
              {showEnd && <td>{r.end_date}</td>}
              <td>{r.note ?? ""}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
