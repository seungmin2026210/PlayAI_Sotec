import { Icon } from "./Icon";
import type { User } from "../types";

/** 상단바 — 검색 / 알림 / 아바타. Dashboard.dc.html 상단바를 React 로 이식. */

function Avatar({ name, size = 36 }: { name: string; size?: number }) {
  const initials = name.trim().split(/\s+/).slice(0, 2).map((w) => w[0]?.toUpperCase()).join("");
  return (
    <div
      style={{
        width: size,
        height: size,
        borderRadius: "var(--radius-round)",
        overflow: "hidden",
        flexShrink: 0,
        backgroundColor: "var(--grey-100)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <span style={{ fontFamily: "var(--font-sans)", fontWeight: 600, fontSize: size * 0.35, color: "var(--slate-700)" }}>
        {initials}
      </span>
    </div>
  );
}

function SearchInput({ placeholder }: { placeholder: string }) {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 8,
        borderRadius: "var(--radius-sm)",
        boxShadow: "var(--shadow-inset-border)",
        padding: "10px 16px",
        width: 300,
        maxWidth: "100%",
      }}
    >
      <Icon name="Search" size={20} style={{ color: "var(--text-muted)", flexShrink: 0 }} />
      <input
        placeholder={placeholder}
        style={{ border: "none", outline: "none", flex: 1, background: "transparent", fontFamily: "var(--font-sans)", fontSize: 14, color: "var(--slate-600)" }}
      />
    </div>
  );
}

export interface TopBarProps {
  isMobile: boolean;
  onToggleMobileNav: () => void;
  user: User;
  onLogout: () => void;
}

export function TopBar({ isMobile, onToggleMobileNav, user, onLogout }: TopBarProps) {
  const roleLabel = user.role === "SUPER_ADMIN" ? "전체관리자" : `그룹관리자 ${user.group_code ?? ""}`;

  return (
    <div
      style={{
        height: 100,
        minHeight: 100,
        background: "var(--surface-card)",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "0 28px",
        gap: 16,
        boxSizing: "border-box",
        fontFamily: "var(--font-sans)",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 16, minWidth: 0, flex: 1 }}>
        {isMobile && (
          <div
            onClick={onToggleMobileNav}
            style={{ display: "flex", flexDirection: "column", gap: 4, padding: 10, cursor: "pointer", flexShrink: 0 }}
          >
            <span style={{ display: "block", width: 20, height: 2, background: "var(--text-heading-alt)" }} />
            <span style={{ display: "block", width: 20, height: 2, background: "var(--text-heading-alt)" }} />
            <span style={{ display: "block", width: 20, height: 2, background: "var(--text-heading-alt)" }} />
          </div>
        )}
        <SearchInput placeholder="SW명 · 사용자 · 자산번호 검색" />
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 20, flexShrink: 0 }}>
        <Icon name="FiRrBell" size={22} style={{ color: "var(--text-muted)" }} />
        <div style={{ display: "flex", alignItems: "center", gap: 10, height: "100%" }}>
          <Avatar name={user.display_name} size={36} />
          <div>
            <div style={{ fontSize: 13.5, fontWeight: 700, color: "var(--text-heading-alt)", whiteSpace: "nowrap" }}>
              {user.display_name}
            </div>
            <div style={{ fontSize: 11.5, color: "var(--text-muted)", whiteSpace: "nowrap" }}>{roleLabel}</div>
          </div>
        </div>
        <button
          onClick={onLogout}
          style={{
            border: "1px solid var(--border-default)",
            background: "transparent",
            borderRadius: "var(--radius-sm)",
            padding: "7px 14px",
            fontFamily: "var(--font-sans)",
            fontSize: 12.5,
            fontWeight: 600,
            color: "var(--text-muted)",
            cursor: "pointer",
          }}
        >
          로그아웃
        </button>
      </div>
    </div>
  );
}
