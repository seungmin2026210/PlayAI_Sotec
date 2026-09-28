import { useCallback, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createMember, listMembers, patchMember } from "../api/members";
import { ApiError } from "../api/client";
import { useAuth } from "../auth";
import { useMeta } from "../hooks/useMeta";
import { useToast } from "../components/Toast";
import { SuperAdminOnly } from "../components/RoleGate";
import { AssetTabs } from "../components/AssetTabs";
import { Modal } from "../components/Modal";
import type { Member } from "../types";

/** 사용자별 탭(D25): 팀원 목록 + 유형별 현재 사용 개수 + 명단 관리(등록·수정·퇴사). */
export function MemberList() {
  const { user } = useAuth();
  const toast = useToast();
  const [items, setItems] = useState<Member[] | null>(null);
  const [editing, setEditing] = useState<Member | "new" | null>(null);

  const load = useCallback(async () => {
    try {
      setItems((await listMembers()).items);
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "명단을 불러오지 못했습니다.", "error");
      setItems([]);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  async function toggleActive(m: Member) {
    const msg = m.active ? `${m.name} 님을 퇴사 처리할까요? 신규 배정이 막힙니다.` : `${m.name} 님을 재직으로 되돌릴까요?`;
    if (!window.confirm(msg)) return;
    try {
      const r = await patchMember(m.employee_no, { active: !m.active });
      toast.show(r.warning ?? (m.active ? "퇴사 처리했습니다." : "재직으로 변경했습니다."), r.warning ? "info" : "success");
      load();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "처리 실패", "error");
    }
  }

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>자산관리</h1>
          <p className="muted">
            {user?.role === "GROUP_MANAGER" ? `그룹관리자 · 본인 그룹(${user.group_code}) 팀원만` : "전체관리자 · 팀원 명단 관리"}
          </p>
        </div>
        <SuperAdminOnly>
          <button className="primary" onClick={() => setEditing("new")}>
            + 팀원 등록
          </button>
        </SuperAdminOnly>
      </div>

      <AssetTabs />

      <div className="card">
        <table className="list-table">
          <thead>
            <tr>
              <th>이름</th>
              <th>사번</th>
              <th>그룹</th>
              <th>재직</th>
              <th>SW</th>
              <th>HW</th>
              <th>교육</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {items === null && (
              <tr>
                <td colSpan={8} className="empty">
                  불러오는 중…
                </td>
              </tr>
            )}
            {items?.length === 0 && (
              <tr>
                <td colSpan={8} className="empty">
                  등록된 팀원이 없습니다.
                </td>
              </tr>
            )}
            {items?.map((m) => (
              <tr key={m.employee_no} className={m.active ? undefined : "dim"}>
                <td>
                  <Link to={`/assets/members/${m.employee_no}`}>{m.name}</Link>
                </td>
                <td>{m.employee_no}</td>
                <td>{m.group_name}</td>
                <td>{m.active ? "재직" : "퇴사"}</td>
                <td>{m.counts.SW}</td>
                <td>{m.counts.HW}</td>
                <td>{m.counts.EDU}</td>
                <td>
                  <SuperAdminOnly>
                    <span className="row-gap" style={{ justifyContent: "center" }}>
                      <button className="ghost" onClick={() => setEditing(m)}>
                        수정
                      </button>
                      <button className={m.active ? "danger" : "ghost"} onClick={() => toggleActive(m)}>
                        {m.active ? "퇴사 처리" : "재직 복귀"}
                      </button>
                    </span>
                  </SuperAdminOnly>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <MemberDialog
          member={editing === "new" ? null : editing}
          onClose={() => setEditing(null)}
          onSaved={() => {
            setEditing(null);
            load();
          }}
        />
      )}
    </div>
  );
}

function MemberDialog({ member, onClose, onSaved }: { member: Member | null; onClose: () => void; onSaved: () => void }) {
  const meta = useMeta();
  const toast = useToast();
  const [employeeNo, setEmployeeNo] = useState(member?.employee_no ?? "");
  const [name, setName] = useState(member?.name ?? "");
  const [group, setGroup] = useState(member?.group_code ?? "A");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!employeeNo.trim() || !name.trim()) return setError("사번과 이름을 입력하세요.");
    try {
      if (member) await patchMember(member.employee_no, { name: name.trim(), group_code: group });
      else await createMember({ employee_no: employeeNo.trim(), name: name.trim(), group_code: group });
      toast.show("저장했습니다.", "success");
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "저장 실패");
    }
  }

  return (
    <Modal title={member ? `팀원 수정 — ${member.employee_no}` : "팀원 등록"} onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <label>
          사번 *
          <input value={employeeNo} disabled={Boolean(member)} onChange={(e) => setEmployeeNo(e.target.value)} />
        </label>
        <label>
          이름 *
          <input value={name} onChange={(e) => setName(e.target.value)} />
        </label>
        <label>
          그룹 *
          <select value={group} onChange={(e) => setGroup(e.target.value)}>
            {meta?.groups.map((g) => (
              <option key={g.code} value={g.code}>
                {g.code} · {g.name}
              </option>
            ))}
          </select>
        </label>
        {member && (
          <p className="muted">
            이름을 고치면 지금 쓰는 자산의 "현재 사용자" 이름도 바뀝니다(과거 이력은 당시 이름 유지). 그룹을 바꾸면 지금
            쓰는 자산의 조회 그룹도 함께 바뀝니다.
          </p>
        )}
        {error && <div className="form-error">{error}</div>}
        <div className="row-gap" style={{ justifyContent: "flex-end" }}>
          <button type="submit" className="primary">
            저장
          </button>
          <button type="button" className="ghost" onClick={onClose}>
            취소
          </button>
        </div>
      </form>
    </Modal>
  );
}
