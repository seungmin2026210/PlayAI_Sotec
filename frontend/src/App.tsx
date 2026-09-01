import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Placeholder } from "./pages/Placeholder";
import { QuoteList } from "./pages/QuoteList";
import { QuoteDetail } from "./pages/QuoteDetail";
import { QuoteForm } from "./pages/QuoteForm";
import { AppShell } from "./design/AppShell";
import type { ReactNode } from "react";

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <div className="page">세션 확인 중…</div>;
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />;
  return <AppShell>{children}</AppShell>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <Dashboard />
          </Protected>
        }
      />
      <Route
        path="/quotes"
        element={
          <Protected>
            <QuoteList />
          </Protected>
        }
      />
      <Route
        path="/quotes/new"
        element={
          <Protected>
            <QuoteForm mode="create" />
          </Protected>
        }
      />
      <Route
        path="/quotes/:id"
        element={
          <Protected>
            <QuoteDetail />
          </Protected>
        }
      />
      <Route
        path="/quotes/:id/edit"
        element={
          <Protected>
            <QuoteForm mode="edit" />
          </Protected>
        }
      />
      <Route
        path="/purchase"
        element={
          <Protected>
            <Placeholder icon="FiRrShoppingCart" label="구매관리" />
          </Protected>
        }
      />
      <Route
        path="/contract"
        element={
          <Protected>
            <Placeholder icon="FiRrUser" label="계약관리" />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
