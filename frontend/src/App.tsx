import { Navigate, Route, Routes, useLocation } from "react-router-dom";
import { useAuth } from "./auth";
import { Login } from "./pages/Login";
import { Dashboard } from "./pages/Dashboard";
import { Placeholder } from "./pages/Placeholder";
import { QuoteList } from "./pages/QuoteList";
import { QuoteDetail } from "./pages/QuoteDetail";
import { QuoteForm } from "./pages/QuoteForm";
import { PurchaseList } from "./pages/PurchaseList";
import { PurchaseForm } from "./pages/PurchaseForm";
import { PurchaseDetail } from "./pages/PurchaseDetail";
import { PurchaseProductList } from "./pages/PurchaseProductList";
import { AssetList } from "./pages/AssetList";
import { AssetForm } from "./pages/AssetForm";
import { AssetImport } from "./pages/AssetImport";
import { AssetDetail } from "./pages/AssetDetail";
import { MemberList } from "./pages/MemberList";
import { MemberDetail } from "./pages/MemberDetail";
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
            <PurchaseList />
          </Protected>
        }
      />
      <Route
        path="/purchase/products"
        element={
          <Protected>
            <PurchaseProductList />
          </Protected>
        }
      />
      <Route
        path="/purchase/new"
        element={
          <Protected>
            <PurchaseForm mode="create" />
          </Protected>
        }
      />
      <Route
        path="/purchase/:unitNo/edit"
        element={
          <Protected>
            <PurchaseForm mode="edit" />
          </Protected>
        }
      />
      <Route
        path="/purchase/:unitNo"
        element={
          <Protected>
            <PurchaseDetail />
          </Protected>
        }
      />
      <Route path="/assets" element={<Navigate to="/assets/sw" replace />} />
      <Route
        path="/assets/members"
        element={
          <Protected>
            <MemberList />
          </Protected>
        }
      />
      <Route
        path="/assets/members/:employeeNo"
        element={
          <Protected>
            <MemberDetail />
          </Protected>
        }
      />
      <Route
        path="/assets/item/:assetNo"
        element={
          <Protected>
            <AssetDetail />
          </Protected>
        }
      />
      <Route
        path="/assets/item/:assetNo/edit"
        element={
          <Protected>
            <AssetForm mode="edit" />
          </Protected>
        }
      />
      <Route
        path="/assets/:category"
        element={
          <Protected>
            <AssetList />
          </Protected>
        }
      />
      <Route
        path="/assets/:category/new"
        element={
          <Protected>
            <AssetForm mode="create" />
          </Protected>
        }
      />
      <Route
        path="/assets/:category/import"
        element={
          <Protected>
            <AssetImport />
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
