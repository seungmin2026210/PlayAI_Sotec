import { Icon } from "../design/Icon";

/** 준비 중 화면 — Dashboard.dc.html 의 isPlaceholder 상태를 이식. 구매관리/계약관리 등
 * 아직 백엔드가 없는 메뉴(CLAUDE.md 범위 밖)에 사용한다. */
export function Placeholder({ icon, label }: { icon: string; label: string }) {
  return (
    <div
      style={{
        background: "var(--surface-card)", borderRadius: "var(--radius-md)", padding: "48px 32px",
        boxShadow: "var(--shadow-card)", display: "flex", flexDirection: "column", alignItems: "center",
        gap: 14, textAlign: "center", fontFamily: "var(--font-sans)",
      }}
    >
      <span style={{ width: 52, height: 52, borderRadius: "var(--radius-md)", background: "var(--color-primary-tint)", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <Icon name={icon} size={26} style={{ color: "var(--color-primary)" }} />
      </span>
      <h3 style={{ margin: 0, fontSize: 17, fontWeight: 600, color: "var(--text-heading-alt)" }}>{label}</h3>
      <p style={{ margin: 0, fontSize: 13, color: "var(--text-muted)", maxWidth: 320 }}>
        해당 화면은 현재 준비 중입니다. 완료되는 대로 이 메뉴에서 이용하실 수 있습니다.
      </p>
    </div>
  );
}
