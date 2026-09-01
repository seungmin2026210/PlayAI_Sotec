import type { ReactNode } from "react";
import { useAuth } from "../auth";

/**
 * open-3 격리 지점: 역할별 화면 차이.
 * 전체관리자에게만 보여줄 액션 UI 를 감싼다. (서버가 최종 방어선)
 */
export function SuperAdminOnly({ children }: { children: ReactNode }) {
  const { user } = useAuth();
  if (user?.role !== "SUPER_ADMIN") return null;
  return <>{children}</>;
}
