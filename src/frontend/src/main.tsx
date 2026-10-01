import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Navigate, NavLink, Route, Routes } from "react-router-dom";
import { ROLE_LABEL, type Role } from "./api";
import { AuthProvider, useAuth } from "./auth";
import { Spinner } from "./components/ui";
import "./index.css";
import Audit from "./pages/Audit";
import Cases from "./pages/Cases";
import CaseView from "./pages/CaseView";
import Config from "./pages/Config";
import Login from "./pages/Login";
import Tokens from "./pages/Tokens";

const qc = new QueryClient({ defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } } });

function Shell({ children, roles }: { children: ReactNode; roles?: Role[] }) {
  const { user, loading, logout } = useAuth();
  if (loading) return <Spinner label="loading" />;
  if (!user) return <Navigate to="/login" replace />;
  if (roles && !roles.includes(user.role)) return <Navigate to="/" replace />;
  const link = ({ isActive }: { isActive: boolean }) =>
    `whitespace-nowrap rounded px-3 py-1.5 text-sm ${isActive ? "bg-white/15 text-white" : "text-indigo-100 hover:text-white"}`;
  const staff = user.role !== "product_owner";
  return (
    <div className="min-h-screen">
      <header className="bg-indigo-900 text-white">
        <div className="mx-auto flex max-w-7xl items-center gap-4 px-4 py-2">
          <span className="font-semibold whitespace-nowrap">Risk Assessment Workbench</span>
          <nav className="flex gap-1">
            <NavLink to="/" end className={link}>
              Cases
            </NavLink>
            {staff && (
              <NavLink to="/config" className={link} data-testid="nav-config">
                Config
              </NavLink>
            )}
            {staff && (
              <NavLink to="/audit" className={link} data-testid="nav-audit">
                Audit
              </NavLink>
            )}
            {staff && (
              <NavLink to="/tokens" className={link} data-testid="nav-tokens">
                AI usage
              </NavLink>
            )}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm whitespace-nowrap">
            <span data-testid="whoami">
              {user.name} <span className="text-indigo-300">- {ROLE_LABEL[user.role]}</span>
            </span>
            <button className="text-indigo-200 hover:text-white" data-testid="logout" onClick={logout}>
              Switch persona
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-7xl px-4 pb-6 text-[11px] text-slate-400">Synthetic data only. AI drafts and suggests; people decide.</footer>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={qc}>
      <AuthProvider>
        <BrowserRouter>
          <Routes>
            <Route path="/login" element={<Login />} />
            <Route path="/" element={<Shell><Cases /></Shell>} />
            <Route path="/cases/:id" element={<Shell><CaseView /></Shell>} />
            <Route path="/config" element={<Shell roles={["analyst", "committee"]}><Config /></Shell>} />
            <Route path="/audit" element={<Shell roles={["analyst", "committee"]}><Audit /></Shell>} />
            <Route path="/tokens" element={<Shell roles={["analyst", "committee"]}><Tokens /></Shell>} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  </StrictMode>,
);
