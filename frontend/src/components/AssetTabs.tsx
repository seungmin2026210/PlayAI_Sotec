import { NavLink } from "react-router-dom";
import type { AssetCategory } from "../types";

/** URL 조각(sw/hw/edu) ↔ 유형 코드. 잘못된 조각이면 null. */
export function slugToCategory(slug: string | undefined): AssetCategory | null {
  const c = (slug ?? "").toUpperCase();
  return c === "SW" || c === "HW" || c === "EDU" ? c : null;
}

export function categoryPath(c: AssetCategory): string {
  return `/assets/${c.toLowerCase()}`;
}

export const CATEGORY_LABEL: Record<AssetCategory, string> = { SW: "SW", HW: "HW", EDU: "교육" };

/** 자산관리 화면 상단 탭: SW / HW / 교육 / 사용자별 (D30). */
const TABS = [
  { to: "/assets/sw", label: "SW" },
  { to: "/assets/hw", label: "HW" },
  { to: "/assets/edu", label: "교육" },
  { to: "/assets/members", label: "사용자별" },
];

export function AssetTabs() {
  return (
    <nav className="tabs">
      {TABS.map((t) => (
        <NavLink key={t.to} to={t.to} className={({ isActive }) => (isActive ? "tab active" : "tab")}>
          {t.label}
        </NavLink>
      ))}
    </nav>
  );
}
