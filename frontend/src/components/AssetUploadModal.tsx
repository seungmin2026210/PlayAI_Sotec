import { useState } from "react";
import { downloadUploadTemplate, previewAssetUpload, uploadAssets } from "../api/assets";
import { ApiError } from "../api/client";
import { useToast } from "./Toast";
import { Modal } from "./Modal";
import { CATEGORY_LABEL } from "./AssetTabs";
import type { AssetCategory, AssetUploadIssue, AssetUploadPreview } from "../types";

const CATEGORIES: AssetCategory[] = ["SW", "HW", "EDU"];

/** 엑셀 일괄 업로드(ASSET-1 D50) — 템플릿 → 파일 선택 → 미리보기(검증만) → 등록(서버가 같은 파일을 재검증). */
export function AssetUploadModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const toast = useToast();
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<AssetUploadPreview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function pick(f: File | null) {
    setFile(f);
    setPreview(null);
    setError(null);
  }

  async function run<T>(fn: () => Promise<T>): Promise<T | undefined> {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "요청 실패");
    } finally {
      setBusy(false);
    }
  }

  async function onTemplate() {
    await run(downloadUploadTemplate);
  }

  async function onPreview() {
    if (!file) return;
    const p = await run(() => previewAssetUpload(file));
    if (p) setPreview(p);
  }

  async function onSubmit() {
    if (!file) return;
    const r = await run(() => uploadAssets(file));
    if (!r) return;
    const hasPassword = preview?.rows.some((row) => row.has_password);
    toast.show(
      `${r.asset_nos.length}건 등록했습니다.${hasPassword ? " 비밀번호가 든 엑셀 파일은 삭제하세요." : ""}`,
      "success",
    );
    onDone();
  }

  const ok = preview !== null && preview.errors.length === 0;
  const hasPassword = preview?.rows.some((r) => r.has_password) ?? false;

  return (
    <Modal title="엑셀 일괄 업로드" onClose={onClose} wide>
      <div className="stack">
        <p className="muted">
          템플릿의 SW / HW / 교육 시트에 한 행에 자산 1건씩 입력해 올립니다. 오류가 한 건이라도 있으면 아무것도
          등록되지 않습니다. 사용자를 적은 자산은 사용 중으로 등록되며, 팀원 명단에 먼저 등록된 사람만 가능합니다.
        </p>
        <div className="row-gap">
          <button type="button" className="ghost" onClick={onTemplate} disabled={busy}>
            템플릿 내려받기
          </button>
          <input
            type="file"
            accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            onChange={(e) => pick(e.target.files?.[0] ?? null)}
            style={{ width: "auto", flex: 1 }}
          />
          <button type="button" onClick={onPreview} disabled={!file || busy}>
            {busy && !preview ? "확인 중…" : "미리보기"}
          </button>
        </div>

        {error && <div className="form-error">{error}</div>}

        {preview && (
          <>
            <p>
              <strong>총 {preview.total}건</strong>{" "}
              <span className="muted">
                ({CATEGORIES.map((c) => `${CATEGORY_LABEL[c]} ${preview.counts[c] ?? 0}`).join(" · ")})
              </span>
              {" · "}
              <span style={{ color: preview.errors.length ? "var(--danger)" : undefined }}>
                오류 {preview.errors.length}건
              </span>
              {" · "}경고 {preview.warnings.length}건
            </p>

            {preview.errors.length > 0 && (
              <IssueTable title="오류 — 고친 뒤 파일을 다시 선택하세요" issues={preview.errors} tone="error" />
            )}
            {preview.warnings.length > 0 && (
              <IssueTable title="경고 — 등록은 가능합니다" issues={preview.warnings} tone="warn" />
            )}

            <div className="upload-scroll">
              <table className="list-table">
                <thead>
                  <tr>
                    <th>시트·행</th>
                    <th>품명</th>
                    <th>소분류</th>
                    <th>그룹</th>
                    <th>사용자</th>
                    <th>사용 시작일</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.rows.map((r) => (
                    <tr key={`${r.sheet}-${r.row}`}>
                      <td>
                        {r.sheet} {r.row}
                      </td>
                      <td>{r.name ?? "-"}</td>
                      <td>{r.subcategory_label ?? "-"}</td>
                      <td>{r.group_name ?? "-"}</td>
                      <td>{r.user_label ?? "미사용"}</td>
                      <td>
                        {r.start_date ?? "-"}
                        {r.start_auto && <span className="muted"> (자동)</span>}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {hasPassword && (
              <div className="form-error">비밀번호가 들어 있는 파일입니다. 업로드가 끝나면 이 엑셀 파일을 삭제하세요.</div>
            )}
          </>
        )}

        <div className="row-gap" style={{ justifyContent: "flex-end" }}>
          <button type="button" className="primary" onClick={onSubmit} disabled={!ok || busy}>
            {busy && preview ? "등록 중…" : ok ? `${preview.total}건 등록` : "등록"}
          </button>
          <button type="button" className="ghost" onClick={onClose}>
            닫기
          </button>
        </div>
      </div>
    </Modal>
  );
}

function IssueTable({ title, issues, tone }: { title: string; issues: AssetUploadIssue[]; tone: "error" | "warn" }) {
  return (
    <div className={`upload-issues upload-issues-${tone}`}>
      <strong>{title}</strong>
      <ul>
        {issues.map((i, k) => (
          <li key={k}>
            {i.row != null ? `${i.sheet} ${i.row}행` : i.sheet}
            {i.column ? ` · ${i.column}` : ""} — {i.message}
          </li>
        ))}
      </ul>
    </div>
  );
}
