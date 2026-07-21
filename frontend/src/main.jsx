import React, { useCallback, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import { api, Button, EmptyState, Logo, RefreshCw, Toast, unwrap } from "./shared.jsx";
import { Login, Setup } from "./auth.jsx";
import { Shell } from "./layout.jsx";
import { DashboardPage } from "./pages/dashboard.jsx";
import { ProductsPage } from "./pages/products.jsx";
import { SuppliersPage } from "./pages/suppliers.jsx";
import { CategoriesPage } from "./pages/categories.jsx";
import { DocumentPage } from "./pages/documents.jsx";
import { LotsPage } from "./pages/lots.jsx";
import { MovementsPage } from "./pages/movements.jsx";
import { AdjustmentsPage } from "./pages/adjustments.jsx";
import { InventoriesPage } from "./pages/inventories.jsx";
import { AlertsPage } from "./pages/alerts.jsx";
import { ReportsPage } from "./pages/reports.jsx";
import { UsersPage } from "./pages/users.jsx";
import { SettingsPage } from "./pages/settings.jsx";

function App() {
  const [booting, setBooting] = useState(true);
  const [bootError, setBootError] = useState("");
  const [setupRequired, setSetupRequired] = useState(false);
  const [initialUsername, setInitialUsername] = useState("admin");
  const [logged, setLogged] = useState(Boolean(localStorage.getItem("fp_access")));
  const [me, setMe] = useState(null);
  const [page, setPage] = useState("dashboard");
  const [toast, setToast] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const notify = (message, type = "success") => setToast({ message, type });

  const loadDesktopStatus = useCallback(async () => {
    setBooting(true);
    setBootError("");
    try {
      const response = await api.get("desktop/status/");
      setSetupRequired(Boolean(response.data.setup_required));
      if (response.data.setup_required) {
        localStorage.removeItem("fp_access");
        localStorage.removeItem("fp_refresh");
        setLogged(false);
      }
    } catch {
      setBootError("Não foi possível iniciar o serviço local do FP Estoque.");
    } finally {
      setBooting(false);
    }
  }, []);

  async function loadMe() {
    try {
      const [user, notices] = await Promise.all([
        api.get("users/me/"),
        api.get("notifications/?page_size=30"),
      ]);
      setMe(user.data);
      setNotifications(unwrap(notices.data));
    } catch {
      setLogged(false);
      localStorage.removeItem("fp_access");
      localStorage.removeItem("fp_refresh");
    }
  }

  useEffect(() => {
    loadDesktopStatus();
  }, [loadDesktopStatus]);

  useEffect(() => {
    if (logged && !setupRequired) loadMe();
  }, [logged, setupRequired]);

  function logout() {
    localStorage.removeItem("fp_access");
    localStorage.removeItem("fp_refresh");
    setLogged(false);
    setMe(null);
  }

  if (booting) {
    return <div className="app-loading"><Logo /><RefreshCw className="spin" /> Preparando arquivos locais...</div>;
  }

  if (bootError) {
    return (
      <div className="app-loading app-loading-error">
        <Logo />
        <strong>{bootError}</strong>
        <span>Feche o aplicativo, abra novamente e verifique se outro FP Estoque já está em execução.</span>
        <Button icon={RefreshCw} onClick={loadDesktopStatus}>Tentar novamente</Button>
      </div>
    );
  }

  if (setupRequired) {
    return (
      <Setup
        onComplete={(username) => {
          setInitialUsername(username || "admin");
          setSetupRequired(false);
        }}
      />
    );
  }

  if (!logged) return <Login initialUsername={initialUsername} onLogin={() => setLogged(true)} />;
  if (!me) return <div className="app-loading"><Logo /><RefreshCw className="spin" /> Carregando sistema...</div>;

  const pages = {
    dashboard: <DashboardPage />,
    products: <ProductsPage notify={notify} me={me} />,
    categories: <CategoriesPage notify={notify} me={me} />,
    suppliers: <SuppliersPage notify={notify} me={me} />,
    entries: <DocumentPage type="entries" notify={notify} me={me} />,
    outputs: <DocumentPage type="outputs" notify={notify} me={me} />,
    lots: <LotsPage />,
    movements: <MovementsPage me={me} notify={notify} />,
    adjustments: <AdjustmentsPage notify={notify} />,
    inventories: <InventoriesPage me={me} notify={notify} />,
    alerts: <AlertsPage me={me} notify={notify} />,
    reports: <ReportsPage notify={notify} />,
    users: <UsersPage notify={notify} />,
    settings: <SettingsPage notify={notify} />,
  };

  return (
    <>
      <Shell
        me={me}
        page={page}
        setPage={setPage}
        onLogout={logout}
        notifications={notifications}
        onRefreshNotifications={loadMe}
      >
        {pages[page] || <EmptyState title="Página não encontrada" text="Selecione uma opção no menu." />}
      </Shell>
      <Toast toast={toast} onClose={() => setToast(null)} />
    </>
  );
}

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
