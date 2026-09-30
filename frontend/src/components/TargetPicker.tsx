import { useEffect, useState } from "react";
import { listMembers } from "../api/members";
import type { AssignTarget, Member } from "../types";

type Kind = "MEMBER" | "SHARED" | "EXTERNAL";

function kindOf(v: AssignTarget): Kind {
  if (v.shared_label !== null) return "SHARED";
  if (v.external_label !== null) return "EXTERNAL";
  return "MEMBER";
}

/** 배정/이관 대상: 팀원(재직자만) · 공용(장소/용도, D33) · 타업체 제공 중 하나. 교육 자산은 공용 불가. */
export function TargetPicker({
  value,
  onChange,
  allowShared,
}: {
  value: AssignTarget;
  onChange: (t: AssignTarget) => void;
  allowShared: boolean;
}) {
  const [members, setMembers] = useState<Member[]>([]);
  const kind = kindOf(value);

  useEffect(() => {
    listMembers()
      .then((r) => setMembers(r.items.filter((m) => m.active)))
      .catch(() => setMembers([]));
  }, []);

  return (
    <>
      {allowShared && (
        <div className="vat-row">
          <label className="inline">
            <input
              type="radio"
              checked={kind === "MEMBER"}
              onChange={() => onChange({ member_id: "", shared_label: null, external_label: null })}
            />
            팀원
          </label>
          <label className="inline">
            <input
              type="radio"
              checked={kind === "SHARED"}
              onChange={() => onChange({ member_id: null, shared_label: "", external_label: null })}
            />
            공용
          </label>
          <label className="inline">
            <input
              type="radio"
              checked={kind === "EXTERNAL"}
              onChange={() => onChange({ member_id: null, shared_label: null, external_label: "" })}
            />
            타업체 제공
          </label>
        </div>
      )}
      {kind === "SHARED" && (
        <label>
          장소 / 용도 *
          <input
            value={value.shared_label ?? ""}
            placeholder="예: 3층 회의실"
            onChange={(e) => onChange({ member_id: null, shared_label: e.target.value, external_label: null })}
          />
        </label>
      )}
      {kind === "EXTERNAL" && (
        <label>
          제공처 *
          <input
            value={value.external_label ?? ""}
            placeholder="예: OO주식회사"
            onChange={(e) => onChange({ member_id: null, shared_label: null, external_label: e.target.value })}
          />
        </label>
      )}
      {kind === "MEMBER" && (
        <label>
          팀원 *
          <select
            value={value.member_id ?? ""}
            onChange={(e) => onChange({ member_id: e.target.value, shared_label: null, external_label: null })}
          >
            <option value="">선택</option>
            {members.map((m) => (
              <option key={m.employee_no} value={m.employee_no}>
                {m.name} ({m.employee_no} · {m.group_name})
              </option>
            ))}
          </select>
        </label>
      )}
    </>
  );
}
