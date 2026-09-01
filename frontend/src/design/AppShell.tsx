import { useEffect, useState, type ReactNode } from "react";
import { Sidebar } from "./Sidebar";
import { TopBar } from "./TopBar";
import { useAuth } from "../auth";

/** 새 대시보드 셸(사이드바+상단바) — 기존 App.tsx 의 Shell 을 대체. */
export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const [width, setWidth] = useState(() => (typeof window !== "undefined" ? window.innerWidth : 1440));
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  useEffect(() => {
    const onResize = () => setWidth(window.innerWidth);
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const isMobile = width < 1024;

  if (!user) return null;

  return (
    <div style={{ display: "flex", minHeight: "100vh", width: "100%", background: "var(--surface-page)" }}>
      <Sidebar
        collapsed={collapsed}
        onToggleCollapsed={() => setCollapsed((v) => !v)}
        isMobile={isMobile}
        mobileOpen={mobileOpen}
        onCloseMobile={() => setMobileOpen(false)}
      />
      <main style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column" }}>
        <TopBar isMobile={isMobile} onToggleMobileNav={() => setMobileOpen((v) => !v)} user={user} onLogout={logout} />
        <div style={{ padding: isMobile ? "18px 16px" : "24px 28px", flex: 1 }}>{children}</div>
      </main>
    </div>
  );
}
