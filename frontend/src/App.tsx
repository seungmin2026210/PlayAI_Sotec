import { Navigate, Route, Routes, Link, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { Login } from "./pages/Login";
import { QuoteList } from "./pages/QuoteList";
import { QuoteDetail } from "./pages/QuoteDetail";
import { QuoteForm } from "./pages/QuoteForm";
import type { ReactNode } from "react";

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="page">세션 확인 중…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <>{children}</>;
}

function Shell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <>
      <header className="app-bar">
        <Link to="/quotes" className="brand">
          SW 자산 견적서 관리
        </Link>
        <div className="app-bar-right">
          {user && (
            <span className="who">
              {user.display_name}
              <span className="role-tag">
                {user.role === "SUPER_ADMIN" ? "전체관리자" : `그룹관리자 ${user.group_code ?? ""}`}
              </span>
            </span>
          )}
          <button className="ghost" onClick={logout}>
            로그아웃
          </button>
        </div>
      </header>
      <main>{children}</main>
    </>
  );
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/quotes"
        element={
          <Protected>
            <Shell>
              <QuoteList />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/quotes/new"
        element={
          <Protected>
            <Shell>
              <QuoteForm mode="create" />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/quotes/:id"
        element={
          <Protected>
            <Shell>
              <QuoteDetail />
            </Shell>
          </Protected>
        }
      />
      <Route
        path="/quotes/:id/edit"
        element={
          <Protected>
            <Shell>
              <QuoteForm mode="edit" />
            </Shell>
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/quotes" replace />} />
    </Routes>
  );
}
