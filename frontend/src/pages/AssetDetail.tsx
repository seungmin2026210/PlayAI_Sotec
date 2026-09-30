import { useCallback, useEffect, useState, type ReactNode } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  assignAsset,
  cancelAssignment,
  cancelImport,
  disposeAsset,
  editAssignment,
  getAsset,
  returnAsset,
  revealPassword,
  transferAsset,
} from "../api/assets";
import { ApiError } from "../api/client";
import { useToast } from "../components/Toast";
import { SuperAdminOnly } from "../components/RoleGate";
import { AssetStateBadge, ExpiryBadgeView } from "../components/AssetBadges";
import { categoryPath } from "../components/AssetTabs";
import { Modal } from "../components/Modal";
import { TargetPicker } from "../components/TargetPicker";
import { formatWon } from "../lib/money";
import { todayKst } from "../lib/date";
import type { Asset, AssetAssignment, AssignTarget } from "../types";

type Dialog = null | "assign" | "transfer" | "return" | { edit: AssetAssignment };

export function AssetDetail() {
  const { assetNo = "" } = useParams();
  const navigate = useNavigate();
  const toast = useToast();
  const [asset, setAsset] = useState<Asset | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [dialog, setDialog] = useState<Dialog>(null);
  const [revealed, setRevealed] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setAsset(await getAsset(assetNo));
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "불러오기 실패", "error");
      if (err instanceof ApiError && err.status === 404) navigate("/assets", { replace: true });
    } finally {
      setLoading(false);
    }
  }, [assetNo, navigate, toast]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function run(fn: () => Promise<Asset | unknown>, ok: string) {
    setBusy(true);
    try {
      const r = await fn();
      if (r && typeof r === "object" && "asset_no" in r) setAsset(r as Asset);
      else await reload();
      toast.show(ok, "success");
      return true;
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "처리 실패", "error");
      return false;
    } finally {
      setBusy(false);
    }
  }

  async function onPassword(action: "REVEAL" | "COPY") {
    try {
      const { password } = await revealPassword(assetNo, action);
      if (action === "COPY") {
        await navigator.clipboard.writeText(password);
        toast.show("비밀번호를 복사했습니다.", "success");
      } else {
        setRevealed(password);
      }
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "열람 실패", "error");
    }
  }

  if (loading && !asset) return <div className="page">불러오는 중…</div>;
  if (!asset) return <div className="page">자산을 찾을 수 없습니다.</div>;

  const a = asset;
  const disposed = a.status === "DISPOSED";
  const currentUser =
    a.current_member_name ??
    (a.current_shared_label
      ? `공용 · ${a.current_shared_label}`
      : a.current_external_label
        ? `타업체 제공 · ${a.current_external_label}`
        : null);
  const row = (label: string, value: ReactNode) => (
    <>
      <dt>{label}</dt>
      <dd>{value ?? "-"}</dd>
    </>
  );

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>
            {a.asset_no} <AssetStateBadge status={a.status} /> <ExpiryBadgeView badge={a.expiry_badge} />
          </h1>
          <p className="muted">
            {a.category_label}
            {a.subcategory_label && ` · ${a.subcategory_label}`} / {a.name} / {a.scope_group_name}
            {disposed && a.disposed_reason_label && ` / ${a.disposed_reason_label}`}
          </p>
        </div>
        <div className="head-actions">
          <SuperAdminOnly>
            {!disposed && <button onClick={() => navigate(`/assets/item/${a.asset_no}/edit`)}>수정</button>}
            {a.status === "IDLE" && (
              <button
                className="danger"
                disabled={busy}
                onClick={() =>
                  window.confirm("폐기하면 되돌릴 수 없습니다. 번호·이력은 보존되고 목록에서 숨겨집니다. 계속할까요?") &&
                  run(() => disposeAsset(a.asset_no), "폐기했습니다.")
                }
              >
                폐기
              </button>
            )}
            {a.source_unit_no && !disposed && (
              <button
                className="warn"
                disabled={busy}
                onClick={() =>
                  window.confirm(
                    `구매 기록 ${a.source_unit_no}에서 가져온 자산 전체가 폐기(가져오기 취소)되고, 구매 기록은 다시 가져올 수 있게 됩니다. 계속할까요?`,
                  ) && run(() => cancelImport(a.source_unit_no!), "가져오기를 취소했습니다.")
                }
              >
                가져오기 취소
              </button>
            )}
          </SuperAdminOnly>
          <button className="ghost" onClick={() => navigate(categoryPath(a.category))}>
            목록으로
          </button>
        </div>
      </div>

      <div className="card">
        <h2>현재 사용</h2>
        <div className="use-row">
          <div>
            {a.status === "IN_USE" ? (
              <>
                <b>{currentUser}</b>
                {a.current_member_id && <span className="muted"> ({a.current_member_id})</span>} · {a.current_start_date}부터 사용 중
              </>
            ) : disposed ? (
              <span className="muted">폐기된 자산입니다.</span>
            ) : (
              <span className="muted">미사용</span>
            )}
          </div>
          <SuperAdminOnly>
            <div className="row-gap">
              {a.status === "IDLE" && (
                <button className="primary" onClick={() => setDialog("assign")}>
                  사용자 배정
                </button>
              )}
              {a.status === "IN_USE" && (
                <>
                  <button onClick={() => setDialog("transfer")}>사용자 변경</button>
                  <button onClick={() => setDialog("return")}>회수</button>
                  <button
                    className="warn"
                    disabled={busy}
                    onClick={() =>
                      window.confirm("현재 배정 이력을 삭제하고 직전 상태로 되돌립니다(사람을 잘못 골랐을 때). 계속할까요?") &&
                      run(() => cancelAssignment(a.asset_no), "배정을 취소했습니다.")
                    }
                  >
                    배정 취소
                  </button>
                </>
              )}
            </div>
          </SuperAdminOnly>
        </div>
      </div>

      <div className="detail-grid">
        <div className="card">
          <h2>구매 · 계약</h2>
          <dl>
            {row("구매일", a.purchase_date)}
            {row("금액", a.price != null ? formatWon(a.price) : null)}
            {row("구매처", a.purchased_from)}
            {row("견적번호", a.quote_no ? <Link to={`/quotes/${a.quote_no}`}>{a.quote_no}</Link> : null)}
            {row("계약번호", a.contract_no)}
            {row("연결 구매", a.source_unit_no ? <Link to={`/purchase/${a.source_unit_no}`}>{a.source_unit_no}</Link> : null)}
          </dl>
        </div>
        <div className="card">
          <h2>유효기간</h2>
          <dl>
            {row("시작일", a.valid_from)}
            {row("종료일", a.valid_to ?? "무기한")}
            {row("등록 그룹", a.group_name)}
            {row("비고", a.note)}
          </dl>
        </div>
        <div className="card">
          <h2>{a.category_label} 정보</h2>
          <dl>
            {a.category === "SW" && (
              <>
                {row("버전", a.version)}
                {row("라이선스키", a.license_key)}
                {row("계정(ID)", a.account_id)}
              </>
            )}
            {a.category === "HW" && (
              <>
                {row("제조사", a.manufacturer)}
                {row("모델명", a.model)}
                {row("시리얼", a.serial_no)}
                {row("MAC", a.mac_address)}
              </>
            )}
            {a.category === "EDU" && (
              <>
                {row("강의명", a.course_title)}
                {row(
                  "강의 URL",
                  a.course_url ? (
                    <a href={a.course_url} target="_blank" rel="noreferrer">
                      {a.course_url}
                    </a>
                  ) : null,
                )}
                {row("인프런 계정", a.account_id)}
              </>
            )}
            {a.category !== "HW" && (
              <SuperAdminOnly>
                {row(
                  "비밀번호",
                  a.has_password ? (
                    <span className="row-gap" style={{ alignItems: "center" }}>
                      <code>{revealed ?? "●●●●●●"}</code>
                      {revealed ? (
                        <button type="button" className="ghost" onClick={() => setRevealed(null)}>
                          숨기기
                        </button>
                      ) : (
                        <button type="button" className="ghost" onClick={() => onPassword("REVEAL")}>
                          보기
                        </button>
                      )}
                      <button type="button" className="ghost" onClick={() => onPassword("COPY")}>
                        복사
                      </button>
                    </span>
                  ) : (
                    "없음"
                  ),
                )}
              </SuperAdminOnly>
            )}
          </dl>
        </div>
      </div>

      <div className="card">
        <h2>사용 이력</h2>
        <table className="list-table">
          <thead>
            <tr>
              <th>사용자</th>
              <th>시작일</th>
              <th>종료일</th>
              <th>비고</th>
              <th>수정</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {a.assignments.length === 0 && (
              <tr>
                <td colSpan={6} className="empty">
                  사용 이력이 없습니다.
                </td>
              </tr>
            )}
            {a.assignments.map((h) => (
              <tr key={h.id}>
                <td>
                  {h.member_id ? (
                    <Link to={`/assets/members/${h.member_id}`}>{h.member_name}</Link>
                  ) : h.shared_label ? (
                    `공용 · ${h.shared_label}`
                  ) : (
                    `타업체 제공 · ${h.external_label}`
                  )}
                </td>
                <td>{h.start_date}</td>
                <td>{h.end_date ?? "사용 중"}</td>
                <td>{h.note ?? ""}</td>
                <td className="muted">
                  {h.updated_by && h.updated_at ? `${h.updated_by} · ${new Date(h.updated_at).toLocaleString("ko-KR")}` : ""}
                </td>
                <td>
                  <SuperAdminOnly>
                    {!disposed && (
                      <button className="ghost" onClick={() => setDialog({ edit: h })}>
                        날짜·비고 수정
                      </button>
                    )}
                  </SuperAdminOnly>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {a.renewals.length > 0 && (
        <div className="card">
          <h2>갱신 기록</h2>
          <table className="list-table">
            <thead>
              <tr>
                <th>이전 종료일</th>
                <th>새 기간</th>
                <th>함께 갱신</th>
                <th>연결 구매</th>
                <th>처리</th>
              </tr>
            </thead>
            <tbody>
              {a.renewals.map((r) => (
                <tr key={r.id}>
                  <td>{r.prev_valid_to}</td>
                  <td>
                    {r.new_valid_from} ~ {r.new_valid_to}
                  </td>
                  <td>{r.count}건</td>
                  <td>{r.unit_no ? <Link to={`/purchase/${r.unit_no}`}>{r.unit_no}</Link> : "-"}</td>
                  <td className="muted">
                    {r.created_by} · {r.created_at ? new Date(r.created_at).toLocaleString("ko-KR") : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {dialog === "assign" && (
        <TargetDialog
          title="사용자 배정"
          dateLabel="사용 시작일"
          allowShared={a.category !== "EDU"}
          onClose={() => setDialog(null)}
          onSubmit={(t, d, note) => run(() => assignAsset(a.asset_no, t, d, note), "배정했습니다.")}
        />
      )}
      {dialog === "transfer" && (
        <TargetDialog
          title={`사용자 변경 — 현재 ${currentUser}`}
          dateLabel="변경일"
          minDate={a.current_start_date ?? undefined}
          allowShared={a.category !== "EDU"}
          onClose={() => setDialog(null)}
          onSubmit={(t, d, note) => run(() => transferAsset(a.asset_no, t, d, note), "사용자를 변경했습니다.")}
        />
      )}
      {dialog === "return" && (
        <DateNoteDialog
          title="회수"
          dateLabel="사용 종료일"
          minDate={a.current_start_date ?? undefined}
          onClose={() => setDialog(null)}
          onSubmit={(d, note) => run(() => returnAsset(a.asset_no, d, note), "회수했습니다.")}
        />
      )}
      {dialog && typeof dialog === "object" && (
        <EditAssignmentDialog
          row={dialog.edit}
          onClose={() => setDialog(null)}
          onSubmit={(patch) => run(() => editAssignment(dialog.edit.id, patch), "이력을 수정했습니다.")}
        />
      )}
    </div>
  );
}

// --------------------------------------------------------------------------- dialogs
// 날짜 입력은 오늘(KST)까지만 — 서버도 같은 규칙으로 검사한다(D36).
function TargetDialog({
  title,
  dateLabel,
  minDate,
  allowShared,
  onClose,
  onSubmit,
}: {
  title: string;
  dateLabel: string;
  minDate?: string;
  allowShared: boolean;
  onClose: () => void;
  onSubmit: (t: AssignTarget, date: string, note: string) => Promise<boolean>;
}) {
  const [target, setTarget] = useState<AssignTarget>({ member_id: "", shared_label: null, external_label: null });
  const [date, setDate] = useState(todayKst());
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!target.member_id && !target.shared_label?.trim() && !target.external_label?.trim())
      return setError("팀원을 고르거나 공용 장소/용도, 또는 제공처를 입력하세요.");
    if (await onSubmit(target, date, note)) onClose();
  }

  return (
    <Modal title={title} onClose={onClose}>
      <form className="stack" onSubmit={submit}>
        <TargetPicker value={target} onChange={setTarget} allowShared={allowShared} />
        <label>
          {dateLabel} *
          <input type="date" value={date} min={minDate} max={todayKst()} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label>
          비고
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        {error && <div className="form-error">{error}</div>}
        <DialogButtons onClose={onClose} />
      </form>
    </Modal>
  );
}

function DateNoteDialog({
  title,
  dateLabel,
  minDate,
  onClose,
  onSubmit,
}: {
  title: string;
  dateLabel: string;
  minDate?: string;
  onClose: () => void;
  onSubmit: (date: string, note: string) => Promise<boolean>;
}) {
  const [date, setDate] = useState(todayKst());
  const [note, setNote] = useState("");
  return (
    <Modal title={title} onClose={onClose}>
      <form
        className="stack"
        onSubmit={async (e) => {
          e.preventDefault();
          if (await onSubmit(date, note)) onClose();
        }}
      >
        <label>
          {dateLabel} *
          <input type="date" value={date} min={minDate} max={todayKst()} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label>
          비고
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <DialogButtons onClose={onClose} />
      </form>
    </Modal>
  );
}

function EditAssignmentDialog({
  row,
  onClose,
  onSubmit,
}: {
  row: AssetAssignment;
  onClose: () => void;
  onSubmit: (patch: { start_date?: string; end_date?: string; note?: string | null }) => Promise<boolean>;
}) {
  const [start, setStart] = useState(row.start_date);
  const [end, setEnd] = useState(row.end_date ?? "");
  const [note, setNote] = useState(row.note ?? "");
  const who = row.member_name ?? (row.shared_label ? `공용 · ${row.shared_label}` : `타업체 제공 · ${row.external_label}`);
  return (
    <Modal title={`이력 수정 — ${who}`} onClose={onClose}>
      <form
        className="stack"
        onSubmit={async (e) => {
          e.preventDefault();
          const patch: { start_date?: string; end_date?: string; note?: string | null } = { note: note || null };
          if (start !== row.start_date) patch.start_date = start;
          if (row.end_date && end !== row.end_date) patch.end_date = end;
          if (await onSubmit(patch)) onClose();
        }}
      >
        <p className="muted">사람은 바꿀 수 없습니다. 잘못 고른 경우 [배정 취소]를 쓰세요.</p>
        <div className="grid-2">
          <label>
            시작일
            <input type="date" value={start} max={todayKst()} onChange={(e) => setStart(e.target.value)} />
          </label>
          <label>
            종료일
            <input
              type="date"
              value={end}
              max={todayKst()}
              disabled={!row.end_date}
              title={row.end_date ? "" : "사용 중인 이력의 종료일은 [회수]나 [사용자 변경]으로 입력합니다."}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
        </div>
        <label>
          비고
          <input value={note} onChange={(e) => setNote(e.target.value)} />
        </label>
        <DialogButtons onClose={onClose} />
      </form>
    </Modal>
  );
}

function DialogButtons({ onClose }: { onClose: () => void }) {
  return (
    <div className="row-gap" style={{ justifyContent: "flex-end" }}>
      <button type="submit" className="primary">
        확인
      </button>
      <button type="button" className="ghost" onClick={onClose}>
        취소
      </button>
    </div>
  );
}
