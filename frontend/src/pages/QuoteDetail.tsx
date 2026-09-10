import { useCallback, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import {
  approveQuote,
  cancelQuote,
  deleteQuote,
  downloadQuotePdf,
  downloadQuoteXlsx,
  getQuote,
  purchaseLockQuote,
  rejectQuote,
  sendQuote,
} from "../api/quotes";
import { ApiError } from "../api/client";
import { useToast } from "../components/Toast";
import { SuperAdminOnly } from "../components/RoleGate";
import { LockBadge, StatusBadge } from "../components/StatusBadge";
import { formatWon } from "../lib/money";
import type { Quote } from "../types";

export function QuoteDetail() {
  const { id } = useParams();
  const quoteId = id ?? ""; // Firestore 문서ID(mgmt_no) 문자열 그대로 사용
  const navigate = useNavigate();
  const toast = useToast();

  const [quote, setQuote] = useState<Quote | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setQuote(await getQuote(quoteId));
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "불러오기 실패", "error");
      if (err instanceof ApiError && err.status === 404) navigate("/quotes", { replace: true });
    } finally {
      setLoading(false);
    }
  }, [quoteId, navigate, toast]);

  useEffect(() => {
    reload();
  }, [reload]);

  async function run(fn: () => Promise<unknown>, okMsg: string) {
    setBusy(true);
    try {
      await fn();
      toast.show(okMsg, "success");
      await reload();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "처리 실패", "error");
    } finally {
      setBusy(false);
    }
  }

  async function onReject() {
    const reason = window.prompt("반려 사유를 입력하세요 (필수)");
    if (reason === null) return;
    if (!reason.trim()) {
      toast.show("반려 사유는 필수입니다.", "error");
      return;
    }
    await run(() => rejectQuote(quoteId, reason.trim()), "반려 처리했습니다.");
  }

  async function onDelete() {
    if (!window.confirm("삭제하면 해당 관리번호는 결번 처리되어 재사용되지 않습니다. 계속할까요?"))
      return;
    setBusy(true);
    try {
      const r = await deleteQuote(quoteId);
      toast.show(r.message, "success");
      navigate("/quotes", { replace: true });
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "삭제 실패", "error");
      setBusy(false);
    }
  }

  async function onSend() {
    try {
      const r = await sendQuote(quoteId);
      toast.show(r.message, "info");
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "처리 실패", "error");
    }
  }

  async function dl(fn: () => Promise<void>) {
    try {
      await fn();
    } catch (err) {
      toast.show(err instanceof ApiError ? err.message : "다운로드 실패", "error");
    }
  }

  if (loading) return <div className="page">불러오는 중…</div>;
  if (!quote) return <div className="page">견적서를 찾을 수 없습니다.</div>;

  const canApproveReject = quote.status === "SUBMITTED" && !quote.purchase_locked;
  const canCancel = quote.status === "SUBMITTED" && !quote.purchase_locked;
  const canEditDelete = !quote.read_only;
  const isApproved = quote.status === "APPROVED";

  return (
    <div className="page page-full">
      <div className="page-head">
        <div>
          <h1>
            {quote.title} ({quote.mgmt_no}) <StatusBadge status={quote.status} />{" "}
            {quote.purchase_locked && <LockBadge />}
          </h1>
          <p className="muted">
            {quote.group_code} · {quote.group_name} / 등록자 {quote.created_by} /{" "}
            {new Date(quote.created_at).toLocaleString("ko-KR")}
            {quote.updated_at && ` / 수정 ${new Date(quote.updated_at).toLocaleString("ko-KR")}`}
          </p>
        </div>
        <div className="head-actions">
          {isApproved && (
            <>
              <button onClick={() => dl(() => downloadQuoteXlsx(quoteId))}>엑셀</button>
              <button onClick={() => dl(() => downloadQuotePdf(quoteId))}>PDF</button>
            </>
          )}
          <SuperAdminOnly>
            {isApproved && <button onClick={onSend}>개인메일 발송</button>}
            {canEditDelete && (
              <button disabled={busy} onClick={() => navigate(`/quotes/${quoteId}/edit`)}>
                수정
              </button>
            )}
          </SuperAdminOnly>
          <button className="ghost" onClick={() => navigate("/quotes")}>
            목록으로
          </button>
        </div>
      </div>

      {quote.status === "REJECTED" && quote.reject_reason && (
        <div className="card reject-box">
          <strong>반려 사유</strong>
          <p>{quote.reject_reason}</p>
          <p className="muted">
            반려된 견적서는 읽기전용으로 보존됩니다. 재제출은 새 관리번호로 신규 등록하세요.
          </p>
        </div>
      )}

      <div className="detail-grid">
        <div className="card">
          <h2>공급자 (자사)</h2>
          <dl>
            <dt>회사명</dt>
            <dd>{quote.company.name}</dd>
            <dt>사업자등록번호</dt>
            <dd>{quote.company.biz_no}</dd>
            <dt>대표자명</dt>
            <dd>{quote.company.ceo_name}</dd>
            <dt>주소</dt>
            <dd>{quote.company.address}</dd>
            <dt>연락처</dt>
            <dd>{quote.company.tel}</dd>
          </dl>
        </div>

        <div className="card">
          <h2>수신처 (고객사)</h2>
          <dl>
            <dt>고객사명</dt>
            <dd>{quote.customer_name}</dd>
            <dt>담당자</dt>
            <dd>{quote.customer_contact_name || "-"}</dd>
            <dt>연락처</dt>
            <dd>{quote.customer_contact_phone || "-"}</dd>
          </dl>
        </div>

        <div className="card">
          <h2>견적 정보</h2>
          <dl>
            <dt>견적서명</dt>
            <dd>{quote.title}</dd>
            <dt>발행일자</dt>
            <dd>{quote.issue_date}</dd>
            <dt>발행 담당자</dt>
            <dd>{quote.issuer_name}</dd>
            <dt>부가세</dt>
            <dd>{quote.vat_included ? "포함" : "미포함(별도)"}</dd>
          </dl>
        </div>
      </div>

      <div className="card">
        <h2>견적 항목</h2>
        <table className="list-table quote-items">
          <thead>
            <tr>
              <th>No</th>
              <th>품목</th>
              <th className="num">갯수</th>
              <th className="num">단가(공급가액)</th>
              <th className="num">금액</th>
            </tr>
          </thead>
          <tbody>
            {quote.items.map((it) => (
              <tr key={it.line_no}>
                <td>{it.line_no}</td>
                <td>{it.name}</td>
                <td className="num">{it.qty.toLocaleString("ko-KR")}</td>
                <td className="num">{formatWon(it.unit_price)}</td>
                <td className="num">{formatWon(it.line_amount)}</td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3} />
              <th>공급가액 합계 (십만단위 절사)</th>
              <td className="num">{formatWon(quote.supply_amount)}</td>
            </tr>
            <tr>
              <td colSpan={3} />
              <th>세액 (10%)</th>
              <td className="num">{formatWon(quote.vat_amount)}</td>
            </tr>
            <tr className="total">
              <td colSpan={3} />
              <th>합계금액</th>
              <td className="num">{formatWon(quote.total_with_vat)}</td>
            </tr>
            <tr className="foot-note">
              <td colSpan={5}>
                항목 합계 {formatWon(quote.items_raw_total)} · 합계는 총액 기준 십만단위 절사 ·{" "}
                {quote.vat_included
                  ? "부가세 포함 견적(고객 실지불액 = 합계금액)"
                  : "부가세 미포함(별도) 견적"}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      <SuperAdminOnly>
        <div className="detail-actions">
          {canApproveReject && (
            <button
              className="primary"
              disabled={busy}
              onClick={() => run(() => approveQuote(quoteId), "승인했습니다.")}
            >
              승인
            </button>
          )}
          {canApproveReject && (
            <button className="warn" disabled={busy} onClick={onReject}>
              반려
            </button>
          )}
          {canCancel && (
            <button
              disabled={busy}
              onClick={() => run(() => cancelQuote(quoteId), "취소 처리했습니다.")}
            >
              취소
            </button>
          )}
          {isApproved && (
            <button
              disabled={quote.purchase_locked || busy}
              title="구매관리 데이터 반영(자리표시) — 반영 시 읽기전용 잠금"
              onClick={() =>
                run(() => purchaseLockQuote(quoteId), "구매관리 반영으로 잠금되었습니다.")
              }
            >
              구매관리 반영(잠금)
            </button>
          )}
          {canEditDelete && (
            <button className="danger" disabled={busy} onClick={onDelete}>
              삭제
            </button>
          )}
        </div>
      </SuperAdminOnly>
    </div>
  );
}
