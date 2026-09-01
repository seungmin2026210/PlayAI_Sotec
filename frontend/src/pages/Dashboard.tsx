import type { CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "../design/Icon";
import { useAuth } from "../auth";

/**
 * 대시보드 — Claude Design "로그인 및 대시보드 시스템 구축" 프로젝트의 Dashboard.dc.html 을
 * React 로 이식. 갱신 캘린더/예산 집행/자산 현황은 CLAUDE.md 범위 밖(향후 단계) 항목이라
 * 백엔드 연동 없이 디자인 원본의 목업 데이터를 그대로 표시하는 자리표시 화면이다.
 * 실제 데이터가 붙는 화면은 계약관리 > 견적관리(견적서 목록, /quotes)뿐이다.
 */

const thStyle: CSSProperties = { textAlign: "left", fontSize: 12, color: "var(--text-muted)", fontWeight: 700, padding: "6px 10px", borderBottom: "1px solid var(--border-default)" };
const tdStyle: CSSProperties = { padding: "10px 10px", borderBottom: "1px solid var(--border-default)", fontSize: 12.5, whiteSpace: "nowrap", color: "var(--text-body)" };
const cardStyle: CSSProperties = { background: "var(--surface-card)", borderRadius: "var(--radius-md)", boxShadow: "var(--shadow-card)" };

const STATS = [
  { label: "전체 자산", icon: "FiRrBox", value: "260", sub: "2026년 신규", highlight: "+38" },
  { label: "사용중", icon: "FiRrCheckbox", value: "214", sub: "배정률 82%", highlight: "" },
  { label: "미배정", icon: "FiRrUser", value: "31", sub: "재배정 검토 대상", highlight: "" },
  { label: "갱신 임박 (D-30)", icon: "FiRrCalendar", value: "3", sub: "90일 내 예정 15건", highlight: "", primary: true },
];

const RENEWALS = [
  { dday: "D-11", urgent: true, name: "Minitab 21", who: "최다영 · 품질그룹", date: "2026-08-25", cost: "1,540,000" },
  { dday: "D-18", urgent: true, name: "MATLAB R2025a", who: "이수진 · 공정그룹", date: "2026-09-01", cost: "3,300,000" },
  { dday: "D-25", urgent: true, name: "SolidWorks Premium", who: "박준호 · 설비그룹", date: "2026-09-08", cost: "5,940,000" },
  { dday: "D-35", urgent: false, name: "JMP 17", who: "한지훈 · 기술개발그룹", date: "2026-09-18", cost: "2,180,000" },
  { dday: "D-61", urgent: false, name: "AutoCAD LT 2025", who: "김민서 · 기술개발그룹", date: "2026-10-14", cost: "650,000" },
];

const BUDGET_GROUPS = [
  { name: "기술개발그룹", pct: 71 },
  { name: "공정그룹", pct: 58 },
  { name: "설비그룹", pct: 66 },
  { name: "품질그룹", pct: 44 },
  { name: "생산기술그룹", pct: 52 },
];

const GROUP_TABLE = [
  { name: "기술개발그룹", total: 86, inUse: 74, unassigned: 9, dueSoon: 0, boughtThisYear: 14 },
  { name: "공정그룹", total: 54, inUse: 46, unassigned: 6, dueSoon: 1, boughtThisYear: 8 },
  { name: "설비그룹", total: 48, inUse: 41, unassigned: 5, dueSoon: 1, boughtThisYear: 7 },
  { name: "품질그룹", total: 42, inUse: 33, unassigned: 7, dueSoon: 1, boughtThisYear: 5 },
  { name: "생산기술그룹", total: 30, inUse: 20, unassigned: 4, dueSoon: 0, boughtThisYear: 4 },
];

const CAL_DAYS: Array<[number, boolean, boolean, boolean]> = [
  [26, true, false, false], [27, true, false, false], [28, true, false, false], [29, true, false, false], [30, true, false, false], [31, true, false, false], [1, false, false, false],
  [2, false, false, false], [3, false, false, false], [4, false, false, false], [5, false, false, false], [6, false, false, false], [7, false, false, false], [8, false, false, false],
  [9, false, false, false], [10, false, false, false], [11, false, false, false], [12, false, false, false], [13, false, false, false], [14, false, true, false], [15, false, false, false],
  [16, false, false, false], [17, false, false, false], [18, false, false, false], [19, false, false, false], [20, false, false, false], [21, false, false, false], [22, false, false, false],
  [23, false, false, false], [24, false, false, false], [25, false, false, true], [26, false, false, false], [27, false, false, false], [28, false, false, false], [29, false, false, false],
  [30, false, false, false], [31, false, false, false], [1, true, false, false], [2, true, false, false], [3, true, false, false], [4, true, false, false], [5, true, false, false],
];

const UPCOMING = [
  { when: "8월 25일 (화)", what: "Minitab 21 갱신마감", dday: "D-11", primary: true },
  { when: "9월 1일 (화)", what: "MATLAB R2025a 갱신마감", dday: "D-18", primary: true },
  { when: "9월 8일 (화)", what: "SolidWorks Premium 갱신마감", dday: "D-25", primary: true },
  { when: "9월 18일 (금)", what: "JMP 17 갱신마감", dday: "D-35", primary: false },
  { when: "9월 15일 (화)", what: "2027 예산 수립 마감", dday: "", primary: false },
];

const BUDGET_PCT = 62;
const budgetDashArray = `${((BUDGET_PCT / 100) * 314.159).toFixed(1)} 314.159`;

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  return (
    <div style={{ fontFamily: "var(--font-sans)" }}>
      <section
        style={{
          position: "relative", overflow: "hidden", borderRadius: "var(--radius-lg)", color: "var(--text-on-primary)",
          background: "var(--color-primary)", padding: "18px 28px", marginBottom: 18, boxSizing: "border-box",
          width: "100%", minHeight: 149, display: "flex", flexDirection: "column", justifyContent: "center",
        }}
      >
        <i style={{ position: "absolute", border: "1.5px solid rgba(255,255,255,.22)", borderRadius: "50%", width: 130, height: 130, right: 40, top: -40 }} />
        <i style={{ position: "absolute", border: "1.5px dashed rgba(255,255,255,.22)", borderRadius: "50%", width: 70, height: 70, right: 140, bottom: -20 }} />
        <h2 style={{ margin: "0 0 6px", fontSize: 21, letterSpacing: "-.01em", fontWeight: 700 }}>
          안녕하세요, {user?.display_name ?? ""}님
        </h2>
        <p style={{ margin: 0, fontSize: 15, color: "rgba(255,255,255,.85)" }}>
          이번 분기 갱신 예정 자산이 <b style={{ color: "var(--text-on-primary)" }}>4건</b> 있습니다. 가장 가까운 갱신은{" "}
          <b style={{ color: "var(--text-on-primary)" }}>Minitab (D-11)</b> 입니다.
        </p>
      </section>

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ flex: "3 1 640px", minWidth: 0 }}>
          <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14, marginBottom: 18 }}>
            {STATS.map((s) => (
              <div key={s.label} style={{ ...cardStyle, padding: "16px 18px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                  <span style={{ fontSize: 18, letterSpacing: ".04em", color: "var(--text-muted)", fontWeight: 700 }}>{s.label}</span>
                  <span style={{ width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--color-primary-tint)", border: "1px solid var(--color-primary-tint)" }}>
                    <Icon name={s.icon} size={16} style={{ color: "var(--color-primary)" }} />
                  </span>
                </div>
                <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", color: s.primary ? "var(--color-primary)" : "var(--text-heading)" }}>{s.value}</div>
                <span style={{ fontSize: 13, marginTop: 4, display: "inline-block", borderRadius: "var(--radius-sm)", padding: "2px 8px", fontWeight: 500, background: "var(--grey-100)", color: "var(--text-muted)" }}>
                  {s.sub}
                  {s.highlight && <> <b style={{ color: "var(--color-error)", fontWeight: 700 }}>{s.highlight}</b></>}
                </span>
              </div>
            ))}
          </section>

          <section style={{ display: "flex", gap: 16, marginBottom: 18, flexWrap: "wrap", alignItems: "stretch" }}>
            <div style={{ ...cardStyle, flex: "1.25 1 380px", minWidth: 0, padding: "18px 20px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: "var(--text-heading-alt)" }}>갱신 임박 자산</h3>
                <a href="#" onClick={(e) => e.preventDefault()} style={{ fontSize: 12, fontWeight: 700 }}>전체 보기 ›</a>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <tbody>
                    <tr>
                      <th style={thStyle}>D-DAY</th><th style={thStyle}>SW명</th><th style={thStyle}>사용자</th>
                      <th style={thStyle}>갱신마감일</th><th style={thStyle}>예상 비용</th><th style={thStyle} />
                    </tr>
                    {RENEWALS.map((r) => (
                      <tr key={r.name}>
                        <td style={tdStyle}>
                          <span style={{ fontSize: 10.5, fontWeight: 700, borderRadius: 7, padding: "3px 9px", background: r.urgent ? "var(--color-primary)" : "var(--color-primary-tint)", color: r.urgent ? "var(--text-on-primary)" : "var(--color-primary)" }}>
                            {r.dday}
                          </span>
                        </td>
                        <td style={{ fontWeight: 400, fontSize: 12 }}>{r.name}</td>
                        <td style={{ ...tdStyle, color: "var(--text-muted)", fontSize: 12 }}>{r.who}</td>
                        <td style={tdStyle}>{r.date}</td>
                        <td style={tdStyle}>{r.cost}</td>
                        <td style={tdStyle}>
                          <span style={{ fontSize: 11, fontWeight: 700, color: "var(--color-primary)", border: "1px solid var(--color-primary-tint)", borderRadius: 7, padding: "3px 10px" }}>자산 보기</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div style={{ ...cardStyle, flex: "1 1 300px", minWidth: 0, padding: "18px 20px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: "var(--text-heading-alt)" }}>2026 예산 집행</h3>
                <a href="#" onClick={(e) => e.preventDefault()} style={{ fontSize: 12, fontWeight: 700 }}>예산 관리 ›</a>
              </div>
              <div style={{ display: "flex", gap: 22, alignItems: "center" }}>
                <div style={{ position: "relative", width: 118, height: 118, flexShrink: 0 }}>
                  <svg viewBox="0 0 120 120" width={118} height={118}>
                    <circle cx={60} cy={60} r={50} fill="none" stroke="var(--border-default)" strokeWidth={13} />
                    <circle cx={60} cy={60} r={50} fill="none" stroke="var(--color-primary)" strokeWidth={13} strokeLinecap="round" strokeDasharray={budgetDashArray} transform="rotate(-90 60 60)" />
                  </svg>
                  <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", textAlign: "center", flexDirection: "column" }}>
                    <b style={{ fontSize: 22, letterSpacing: "-.02em", color: "var(--text-heading)" }}>{BUDGET_PCT}%</b>
                    <span style={{ fontSize: 10, color: "var(--text-muted)", letterSpacing: ".06em" }}>집행률</span>
                  </div>
                </div>
                <div style={{ flex: 1, minWidth: 0 }}>
                  {BUDGET_GROUPS.map((b) => (
                    <div key={b.name} style={{ marginBottom: 10 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 12, marginBottom: 4, color: "var(--text-body)" }}>
                        <span>{b.name}</span><b style={{ fontWeight: 700, color: "var(--text-heading-alt)" }}>{b.pct}%</b>
                      </div>
                      <div style={{ height: 7, borderRadius: 4, background: "var(--border-default)", overflow: "hidden" }}>
                        <i style={{ display: "block", height: "100%", borderRadius: 4, background: "var(--color-primary)", width: `${b.pct}%` }} />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              <div style={{ marginTop: 14, paddingTop: 12, borderTop: "1px solid var(--border-default)", display: "flex", justifyContent: "space-between", fontSize: 12, color: "var(--text-muted)" }}>
                <span>총 예산 <b style={{ color: "var(--text-heading-alt)" }}>128,000,000</b></span>
                <span>잔여 <b style={{ color: "var(--color-primary)" }}>48,600,000</b></span>
              </div>
            </div>
          </section>

          <section style={{ ...cardStyle, padding: "18px 20px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: "var(--text-heading-alt)" }}>그룹별 자산 현황</h3>
              <a href="#" onClick={(e) => e.preventDefault()} style={{ fontSize: 12, fontWeight: 700 }}>자산대장 ›</a>
            </div>
            <div style={{ overflowX: "auto" }}>
              <table style={{ width: "100%", borderCollapse: "collapse" }}>
                <tbody>
                  <tr>
                    <th style={thStyle}>그룹</th><th style={thStyle}>전체</th><th style={thStyle}>사용중</th>
                    <th style={thStyle}>미배정</th><th style={thStyle}>갱신 임박(D-30)</th><th style={thStyle}>올해 구매</th>
                  </tr>
                  {GROUP_TABLE.map((g) => (
                    <tr key={g.name}>
                      <td style={{ ...tdStyle, fontWeight: 700 }}>{g.name}</td>
                      <td style={tdStyle}>{g.total}</td>
                      <td style={tdStyle}>{g.inUse}</td>
                      <td style={tdStyle}>{g.unassigned}</td>
                      <td style={{ ...tdStyle, color: g.dueSoon > 0 ? "var(--color-primary)" : "var(--text-heading)", fontWeight: 700 }}>{g.dueSoon}</td>
                      <td style={tdStyle}>{g.boughtThisYear}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <div style={{ flex: "1 1 280px", minWidth: 260, maxWidth: 300, display: "flex", flexDirection: "column", gap: 16 }}>
          <div style={{ ...cardStyle, padding: "16px 18px" }}>
            <div style={{ background: "var(--color-primary)", color: "var(--text-on-primary)", borderRadius: "var(--radius-md)", padding: "10px 14px", display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12, fontWeight: 700, fontSize: 13 }}>
              <span>갱신 캘린더</span><span style={{ fontWeight: 500, fontSize: 12, color: "rgba(255,255,255,.8)" }}>2026년 8월 ▾</span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 2, textAlign: "center" }}>
              {["일", "월", "화", "수", "목", "금", "토"].map((d) => (
                <div key={d} style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700, padding: "3px 0" }}>{d}</div>
              ))}
              {CAL_DAYS.map(([day, dim, today, mark], i) => (
                <div
                  key={i}
                  style={{
                    fontSize: 11.5, padding: "6px 0", borderRadius: 8, position: "relative",
                    color: today ? "var(--text-on-primary)" : dim ? "var(--text-caption)" : "var(--text-heading-alt)",
                    background: today ? "var(--color-primary)" : "transparent",
                    fontWeight: today ? 800 : 400,
                    boxShadow: mark ? "inset 0 -2px 0 var(--color-primary)" : undefined,
                  }}
                >
                  {day}
                </div>
              ))}
            </div>
          </div>

          <div style={{ ...cardStyle, padding: "16px 18px", flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <h3 style={{ margin: "0 0 10px", fontSize: 14.5, fontWeight: 600, color: "var(--text-heading-alt)" }}>다가오는 갱신 일정</h3>
            <ul style={{ listStyle: "none", margin: 0, padding: 0, flex: 1 }}>
              {UPCOMING.map((u) => (
                <li key={u.what} style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "9px 0", borderBottom: "1px dashed var(--border-default)" }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", marginTop: 5, flexShrink: 0, background: u.primary ? "var(--color-primary)" : "var(--grey-200)" }} />
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 10.5, color: "var(--text-muted)" }}>{u.when}</div>
                    <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-heading-alt)" }}>{u.what}</div>
                  </div>
                  {u.dday && <span style={{ marginLeft: "auto", fontSize: 10.5, fontWeight: 700, color: u.primary ? "var(--color-primary)" : "var(--text-muted)" }}>{u.dday}</span>}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>

      <p style={{ marginTop: 18, fontSize: 12, color: "var(--text-muted)" }}>
        위 통계·캘린더·예산 수치는 디자인 목업 데이터입니다. 실제 데이터가 연동된 화면은{" "}
        <a href="#" onClick={(e) => { e.preventDefault(); navigate("/quotes"); }} style={{ fontWeight: 700 }}>
          계약관리 › 견적관리
        </a>{" "}
        입니다.
      </p>
    </div>
  );
}
