import { useEffect, useState, type CSSProperties } from "react";
import { useNavigate } from "react-router-dom";
import { Icon } from "../design/Icon";
import { useAuth } from "../auth";
import { fetchRenewals } from "../api/dashboard";
import { categoryPath } from "../components/AssetTabs";
import { addDays, daysBetween, todayKst } from "../lib/date";
import type { RenewalCalendar, RenewalGroup } from "../types";

/**
 * 대시보드 — Claude Design "로그인 및 대시보드 시스템 구축" 프로젝트의 Dashboard.dc.html 을
 * React 로 이식. ASSET-1(D28)부터 갱신 임박(D-30) KPI·갱신 캘린더·다가오는 갱신 일정은
 * `/api/dashboard/renewals` 실데이터(자산 유효기간 종료일, 같은 날·같은 품명 묶음).
 * 나머지 통계·예산·갱신 임박 자산 표·그룹별 현황은 목업 그대로("예시" 표시 — P6).
 */

const thStyle: CSSProperties = { textAlign: "left", fontSize: 12, color: "var(--text-muted)", fontWeight: 700, padding: "6px 10px", borderBottom: "1px solid var(--border-default)" };
const tdStyle: CSSProperties = { padding: "10px 10px", borderBottom: "1px solid var(--border-default)", fontSize: 12.5, whiteSpace: "nowrap", color: "var(--text-body)" };
const cardStyle: CSSProperties = { background: "var(--surface-card)", borderRadius: "var(--radius-md)", boxShadow: "var(--shadow-card)" };

// 목업(예시 데이터) — 실데이터는 갱신 임박 KPI·갱신 캘린더·다가오는 갱신 일정뿐(ASSET-1 D28).
// 목업 위젯엔 "예시" 표시를 단다(임시 결정 P6).
const STATS = [
  { label: "전체 자산", icon: "FiRrBox", value: "260", sub: "2026년 신규", highlight: "+38" },
  { label: "사용중", icon: "FiRrCheckbox", value: "214", sub: "배정률 82%", highlight: "" },
  { label: "미배정", icon: "FiRrUser", value: "31", sub: "재배정 검토 대상", highlight: "" },
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

const BUDGET_PCT = 62;
const budgetDashArray = `${((BUDGET_PCT / 100) * 314.159).toFixed(1)} 314.159`;
const WEEKDAYS = ["일", "월", "화", "수", "목", "금", "토"];

const sampleTag = (
  <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-muted)", background: "var(--grey-100)", borderRadius: 6, padding: "2px 7px", marginLeft: 8 }}>
    예시
  </span>
);

/** 달력 6주(42칸): [ISO 날짜, 이번 달 여부]. */
function monthCells(year: number, month0: number): Array<[string, boolean]> {
  const first = new Date(Date.UTC(year, month0, 1));
  const start = addDays(first.toISOString().slice(0, 10), -first.getUTCDay());
  return Array.from({ length: 42 }, (_, i) => {
    const iso = addDays(start, i);
    return [iso, Number(iso.slice(5, 7)) === month0 + 1];
  });
}

function whenLabel(iso: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  return `${d.getUTCMonth() + 1}월 ${d.getUTCDate()}일 (${WEEKDAYS[d.getUTCDay()]})`;
}

function listLink(g: RenewalGroup): string {
  return `${categoryPath(g.category)}?name=${encodeURIComponent(g.name)}&valid_to=${g.date}`;
}

export function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const today = todayKst();
  const [cal, setCal] = useState(() => ({ y: Number(today.slice(0, 4)), m: Number(today.slice(5, 7)) - 1 }));
  const [calItems, setCalItems] = useState<RenewalGroup[]>([]);
  const [upcoming, setUpcoming] = useState<RenewalCalendar | null>(null);

  useEffect(() => {
    // 다가오는 갱신 일정(오늘~90일) + KPI(만료됨/D-30/D-90)
    fetchRenewals(today, addDays(today, 90))
      .then(setUpcoming)
      .catch(() => setUpcoming(null));
  }, [today]);

  const cells = monthCells(cal.y, cal.m);
  useEffect(() => {
    fetchRenewals(cells[0][0], cells[41][0])
      .then((r) => setCalItems(r.items))
      .catch(() => setCalItems([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cal.y, cal.m]);

  const byDate = new Map<string, RenewalGroup[]>();
  for (const g of calItems) byDate.set(g.date, [...(byDate.get(g.date) ?? []), g]);
  const kpi = upcoming?.kpi;
  const nearest = upcoming?.items[0];
  const moveMonth = (delta: number) =>
    setCal(({ y, m }) => {
      const t = y * 12 + m + delta;
      return { y: Math.floor(t / 12), m: t % 12 };
    });

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
          90일 내 갱신 예정 자산이 <b style={{ color: "var(--text-on-primary)" }}>{kpi?.d90 ?? 0}건</b> 있습니다.
          {nearest && (
            <>
              {" "}가장 가까운 갱신은{" "}
              <b style={{ color: "var(--text-on-primary)" }}>
                {nearest.name} (D-{daysBetween(today, nearest.date)})
              </b>{" "}
              입니다.
            </>
          )}
        </p>
      </section>

      <div style={{ display: "flex", gap: 20, alignItems: "flex-start", flexWrap: "wrap" }}>
        <div style={{ flex: "3 1 640px", minWidth: 0 }}>
          <section style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))", gap: 14, marginBottom: 18 }}>
            {STATS.map((s) => (
              <div key={s.label} style={{ ...cardStyle, padding: "16px 18px" }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                  <span style={{ fontSize: 18, letterSpacing: ".04em", color: "var(--text-muted)", fontWeight: 700 }}>{s.label}{sampleTag}</span>
                  <span style={{ width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--color-primary-tint)", border: "1px solid var(--color-primary-tint)" }}>
                    <Icon name={s.icon} size={16} style={{ color: "var(--color-primary)" }} />
                  </span>
                </div>
                <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", color: "var(--text-heading)" }}>{s.value}</div>
                <span style={{ fontSize: 13, marginTop: 4, display: "inline-block", borderRadius: "var(--radius-sm)", padding: "2px 8px", fontWeight: 500, background: "var(--grey-100)", color: "var(--text-muted)" }}>
                  {s.sub}
                  {s.highlight && <> <b style={{ color: "var(--color-error)", fontWeight: 700 }}>{s.highlight}</b></>}
                </span>
              </div>
            ))}
            <div style={{ ...cardStyle, padding: "16px 18px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 10 }}>
                <span style={{ fontSize: 18, letterSpacing: ".04em", color: "var(--text-muted)", fontWeight: 700 }}>갱신 임박 (D-30)</span>
                <span style={{ width: 32, height: 32, borderRadius: "50%", display: "flex", alignItems: "center", justifyContent: "center", background: "var(--color-primary-tint)" }}>
                  <Icon name="FiRrCalendar" size={16} style={{ color: "var(--color-primary)" }} />
                </span>
              </div>
              <div style={{ fontSize: 26, fontWeight: 700, letterSpacing: "-.02em", color: "var(--color-primary)" }}>{kpi?.d30 ?? "-"}</div>
              <span style={{ fontSize: 13, marginTop: 4, display: "inline-block", borderRadius: "var(--radius-sm)", padding: "2px 8px", fontWeight: 500, background: "var(--grey-100)", color: "var(--text-muted)" }}>
                90일 내 예정 {kpi?.d90 ?? 0}건
              </span>{" "}
              <a
                href="#"
                onClick={(e) => {
                  e.preventDefault();
                  navigate("/assets/sw?expiry=expired");
                }}
                style={{ fontSize: 13, fontWeight: 700, color: kpi?.expired ? "var(--color-error)" : "var(--text-muted)" }}
                title="유효기간이 지났는데 갱신·폐기하지 않은 자산"
              >
                만료됨 {kpi?.expired ?? 0}건 ›
              </a>
            </div>
          </section>

          <section style={{ display: "flex", gap: 16, marginBottom: 18, flexWrap: "wrap", alignItems: "stretch" }}>
            <div style={{ ...cardStyle, flex: "1.25 1 380px", minWidth: 0, padding: "18px 20px" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 14 }}>
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: "var(--text-heading-alt)" }}>갱신 임박 자산{sampleTag}</h3>
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
                <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: "var(--text-heading-alt)" }}>2026 예산 집행{sampleTag}</h3>
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
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 600, color: "var(--text-heading-alt)" }}>그룹별 자산 현황{sampleTag}</h3>
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
              <span>갱신 캘린더</span>
              <span style={{ fontWeight: 500, fontSize: 12, color: "rgba(255,255,255,.8)", display: "flex", gap: 8, alignItems: "center" }}>
                <span style={{ cursor: "pointer" }} onClick={() => moveMonth(-1)} aria-label="이전 달">‹</span>
                {cal.y}년 {cal.m + 1}월
                <span style={{ cursor: "pointer" }} onClick={() => moveMonth(1)} aria-label="다음 달">›</span>
              </span>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(7,1fr)", gap: 2, textAlign: "center" }}>
              {WEEKDAYS.map((d) => (
                <div key={d} style={{ fontSize: 10, color: "var(--text-muted)", fontWeight: 700, padding: "3px 0" }}>{d}</div>
              ))}
              {cells.map(([iso, inMonth]) => {
                const isToday = iso === today;
                const groups = byDate.get(iso);
                return (
                  <div
                    key={iso}
                    title={groups?.map((g) => `${g.name} ${g.count}건`).join("\n")}
                    onClick={groups ? () => navigate(listLink(groups[0])) : undefined}
                    style={{
                      fontSize: 11.5, padding: "6px 0", borderRadius: 8, position: "relative",
                      cursor: groups ? "pointer" : undefined,
                      color: isToday ? "var(--text-on-primary)" : !inMonth ? "var(--text-caption)" : "var(--text-heading-alt)",
                      background: isToday ? "var(--color-primary)" : "transparent",
                      fontWeight: isToday || groups ? 800 : 400,
                      boxShadow: groups ? "inset 0 -2px 0 var(--color-primary)" : undefined,
                    }}
                  >
                    {Number(iso.slice(8, 10))}
                  </div>
                );
              })}
            </div>
            {calItems.filter((g) => Number(g.date.slice(5, 7)) === cal.m + 1).length > 0 && (
              <ul style={{ listStyle: "none", margin: "10px 0 0", padding: 0, fontSize: 12 }}>
                {calItems
                  .filter((g) => Number(g.date.slice(5, 7)) === cal.m + 1)
                  .map((g) => (
                    <li key={`${g.date}-${g.name}-${g.category}`} style={{ padding: "3px 0", cursor: "pointer" }} onClick={() => navigate(listLink(g))}>
                      <b>{Number(g.date.slice(5, 7))}/{Number(g.date.slice(8, 10))}</b> {g.name} {g.count}건
                    </li>
                  ))}
              </ul>
            )}
          </div>

          <div style={{ ...cardStyle, padding: "16px 18px", flex: 1, display: "flex", flexDirection: "column", minHeight: 0 }}>
            <h3 style={{ margin: "0 0 10px", fontSize: 14.5, fontWeight: 600, color: "var(--text-heading-alt)" }}>다가오는 갱신 일정</h3>
            <ul style={{ listStyle: "none", margin: 0, padding: 0, flex: 1 }}>
              {upcoming && upcoming.items.length === 0 && (
                <li style={{ fontSize: 12.5, color: "var(--text-muted)", padding: "9px 0" }}>90일 내 갱신 예정 자산이 없습니다.</li>
              )}
              {upcoming?.items.slice(0, 8).map((g) => {
                const dday = daysBetween(today, g.date);
                const urgent = dday <= 30;
                return (
                  <li
                    key={`${g.date}-${g.name}-${g.category}`}
                    onClick={() => navigate(listLink(g))}
                    style={{ display: "flex", gap: 10, alignItems: "flex-start", padding: "9px 0", borderBottom: "1px dashed var(--border-default)", cursor: "pointer" }}
                  >
                    <span style={{ width: 8, height: 8, borderRadius: "50%", marginTop: 5, flexShrink: 0, background: urgent ? "var(--color-primary)" : "var(--grey-200)" }} />
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: 10.5, color: "var(--text-muted)" }}>{whenLabel(g.date)}</div>
                      <div style={{ fontSize: 12.5, fontWeight: 600, color: "var(--text-heading-alt)" }}>
                        {g.name} {g.count}건 갱신
                      </div>
                    </div>
                    <span style={{ marginLeft: "auto", fontSize: 10.5, fontWeight: 700, color: urgent ? "var(--color-primary)" : "var(--text-muted)" }}>
                      {dday === 0 ? "D-DAY" : `D-${dday}`}
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      </div>

      <p style={{ marginTop: 18, fontSize: 12, color: "var(--text-muted)" }}>
        "예시" 표시가 붙은 위젯은 디자인 목업 데이터입니다. 갱신 임박 KPI·갱신 캘린더·다가오는 갱신 일정은{" "}
        <a href="#" onClick={(e) => { e.preventDefault(); navigate("/assets"); }} style={{ fontWeight: 700 }}>
          자산관리
        </a>
        의 유효기간 종료일 실데이터입니다.
      </p>
    </div>
  );
}
