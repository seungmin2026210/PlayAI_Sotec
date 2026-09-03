import { useState, type CSSProperties } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Icon } from "./Icon";
import sotecLogo from "../assets/sotec-logo.png";
import sotecMark from "../assets/sotec-mark.png";

/**
 * 왼쪽 사이드바 — Claude Design "로그인 및 대시보드 시스템 구축" 프로젝트의
 * Dashboard.dc.html 사이드바를 React 로 이식. 원본은 컴포넌트 내부 상태(view)로
 * 화면을 전환했지만, 여기서는 실제 라우팅(useLocation/useNavigate)에 맞춰 활성 상태를 계산한다.
 */

const CONTRACT_CHILDREN = [
  { key: "quote", icon: "FiRrEnvelope", label: "견적관리", path: "/quotes" },
  { key: "purchase", icon: "FiRrShoppingCart", label: "구매관리", path: "/purchase" },
  { key: "contract", icon: "FiRrUser", label: "계약관리", path: "/contract" },
] as const;

const navRowBase: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 14,
  padding: "12px 12px",
  borderRadius: "var(--radius-md)",
  cursor: "pointer",
};
const onStyle: CSSProperties = { background: "var(--color-primary-tint)", color: "var(--color-primary)" };
const offStyle: CSSProperties = { color: "var(--text-body)" };

export interface SidebarProps {
  collapsed: boolean;
  onToggleCollapsed: () => void;
  isMobile: boolean;
  mobileOpen: boolean;
  onCloseMobile: () => void;
}

export function Sidebar({ collapsed: collapsedProp, onToggleCollapsed, isMobile, mobileOpen, onCloseMobile }: SidebarProps) {
  const [groupOpen, setGroupOpen] = useState(true);
  const location = useLocation();
  const navigate = useNavigate();

  const collapsed = !isMobile && collapsedProp;
  const showLabels = !collapsed;

  const isDashboard = location.pathname === "/dashboard" || location.pathname === "/";
  const activeChildKey = CONTRACT_CHILDREN.find((c) => location.pathname.startsWith(c.path))?.key;
  const groupActive = Boolean(activeChildKey);

  function goTo(path: string) {
    navigate(path);
    if (isMobile) onCloseMobile();
  }

  function toggleGroup() {
    if (collapsed) {
      onToggleCollapsed();
      setGroupOpen(true);
    } else {
      setGroupOpen((v) => !v);
    }
  }

  const sidebarBase: CSSProperties = {
    background: "var(--surface-card)",
    display: "flex",
    flexDirection: "column",
    justifyContent: "space-between",
    boxSizing: "border-box",
    borderRadius: 0,
    flexShrink: 0,
    padding: collapsed ? "24px 12px 20px" : "24px 20px 20px",
    fontFamily: "var(--font-sans)",
  };
  const sidebarStyle: CSSProperties = isMobile
    ? {
        ...sidebarBase,
        width: 260,
        minWidth: 260,
        height: "100vh",
        position: "fixed",
        top: 0,
        left: 0,
        transform: mobileOpen ? "translateX(0)" : "translateX(-100%)",
        transition: "transform .2s ease",
        boxShadow: "0 0 28px rgba(20,24,35,.18)",
        zIndex: 50,
      }
    : {
        ...sidebarBase,
        width: collapsed ? 84 : 260,
        minWidth: collapsed ? 84 : 260,
        position: "static",
        transition: "width .18s ease",
        boxShadow: "none",
        zIndex: 1,
      };

  return (
    <>
      {isMobile && mobileOpen && (
        <div
          onClick={onCloseMobile}
          style={{ position: "fixed", inset: 0, background: "rgba(20,24,35,0.45)", zIndex: 40 }}
        />
      )}

      <aside style={sidebarStyle}>
        <div style={{ display: "flex", flexDirection: "column", gap: 28, overflow: "hidden" }}>
          <div
            onClick={() => goTo("/dashboard")}
            style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: 4, cursor: "pointer", minHeight: 32 }}
          >
            {showLabels ? (
              <img src={sotecLogo} alt="SOTEC 쏘테크(주)" style={{ height: 28, width: "auto" }} />
            ) : (
              <img src={sotecMark} alt="SOTEC" style={{ height: 28, width: "auto", flexShrink: 0 }} />
            )}
          </div>

          <nav style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <div
              onClick={() => goTo("/dashboard")}
              style={{ ...navRowBase, ...(isDashboard ? onStyle : offStyle), justifyContent: collapsed ? "center" : "flex-start" }}
            >
              <Icon name="FiRrHome" size={22} style={{ color: isDashboard ? "var(--color-primary)" : "var(--text-muted)", flexShrink: 0 }} />
              {showLabels && (
                <span style={{ fontSize: 15, fontWeight: isDashboard ? 700 : 500, whiteSpace: "nowrap" }}>대시보드</span>
              )}
            </div>

            <div
              onClick={toggleGroup}
              style={{ ...navRowBase, ...(groupActive ? onStyle : offStyle), justifyContent: collapsed ? "center" : "flex-start" }}
            >
              <Icon name="FiRrChartHistogram" size={22} style={{ color: groupActive ? "var(--color-primary)" : "var(--text-muted)", flexShrink: 0 }} />
              {showLabels && (
                <span style={{ fontSize: 15, fontWeight: groupActive ? 700 : 500, flex: 1, whiteSpace: "nowrap" }}>계약관리</span>
              )}
            </div>

            {showLabels && groupOpen && (
              <>
                {CONTRACT_CHILDREN.map((item) => {
                  const active = activeChildKey === item.key;
                  return (
                    <div
                      key={item.key}
                      onClick={() => goTo(item.path)}
                      style={{ ...navRowBase, paddingLeft: collapsed ? 12 : 44, ...(active ? onStyle : offStyle) }}
                    >
                      <Icon name={item.icon} size={20} style={{ color: active ? "var(--color-primary)" : "var(--text-muted)", flexShrink: 0 }} />
                      <span style={{ fontSize: 15, fontWeight: active ? 700 : 500, whiteSpace: "nowrap" }}>{item.label}</span>
                    </div>
                  );
                })}
              </>
            )}
          </nav>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          {!isMobile && (
            <div
              onClick={onToggleCollapsed}
              style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: 8, padding: 10, borderRadius: "var(--radius-md)", cursor: "pointer", color: "var(--text-muted)" }}
            >
              <Icon name="FiRrAngleUp" size={16} style={{ color: "var(--text-muted)", transform: collapsed ? "rotate(90deg)" : "rotate(-90deg)" }} />
              {showLabels && <span style={{ fontSize: 13.5, fontWeight: 600 }}>접기</span>}
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
