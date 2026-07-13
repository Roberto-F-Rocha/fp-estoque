import { React, useEffect, useMemo, useState, api, unwrap, fmtMoney, fmtQty, fmtDate, today, getError, Logo, Button, Modal, Toast, Field, EmptyState, Pagination, DataTable, StatusBadge, AlertTriangle, Archive, ArrowDownToLine, ArrowUpFromLine, BarChart3, Bell, Boxes, Check, ChevronDown, CircleDollarSign, ClipboardCheck, Eye, EyeOff, FileDown, FileText, Gauge, History, Layers3, LogOut, Menu, Package, Pencil, Plus, RefreshCw, Search, Settings, ShieldCheck, SlidersHorizontal, Trash2, Truck, UserCog, Users, Warehouse, X, Bar, BarChart, CartesianGrid, Legend, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "./shared.jsx";
const menuItems = [
  ["dashboard", Gauge, "Dashboard"],
  ["products", Package, "Produtos"],
  ["categories", Layers3, "Categorias"],
  ["suppliers", Truck, "Fornecedores"],
  ["entries", ArrowDownToLine, "Entradas"],
  ["outputs", ArrowUpFromLine, "Saídas"],
  ["lots", Boxes, "Lotes e validade"],
  ["movements", History, "Movimentações"],
  ["adjustments", SlidersHorizontal, "Ajustes", "admin"],
  ["inventories", ClipboardCheck, "Inventários"],
  ["alerts", AlertTriangle, "Alertas"],
  ["reports", FileText, "Relatórios"],
  ["users", Users, "Usuários", "admin"],
  ["settings", Settings, "Configurações", "admin"],
];

export function Shell({ me, page, setPage, onLogout, children, notifications, onRefreshNotifications }) {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const visibleItems = menuItems.filter((item) => item[3] !== "admin" || me?.permissions?.is_admin);
  return (
    <div className={`shell ${collapsed ? "sidebar-collapsed" : ""}`}>
      <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
        <div className="sidebar-top">
          <Logo compact={collapsed} />
          <button className="icon-btn sidebar-collapse" onClick={() => setCollapsed(!collapsed)}><Menu size={20} /></button>
        </div>
        <nav>
          {visibleItems.map(([id, Icon, label]) => (
            <button key={id} className={page === id ? "active" : ""} onClick={() => { setPage(id); setMobileOpen(false); }} title={collapsed ? label : undefined}>
              <Icon size={19} /> {!collapsed && <span>{label}</span>}
            </button>
          ))}
        </nav>
        <button className="sidebar-logout" onClick={onLogout}><LogOut size={19} /> {!collapsed && "Sair"}</button>
      </aside>
      {mobileOpen && <div className="mobile-overlay" onClick={() => setMobileOpen(false)} />}
      <main className="content">
        <header className="topbar">
          <button className="icon-btn mobile-menu" onClick={() => setMobileOpen(true)}><Menu size={22} /></button>
          <div className="topbar-title">
            <h1>{menuItems.find(([id]) => id === page)?.[2] || "FP Estoque"}</h1>
            <small>Controle interno • dados em tempo real</small>
          </div>
          <div className="topbar-actions">
            <div className="notification-wrap">
              <button className="icon-btn bell" onClick={() => setShowNotifications(!showNotifications)}>
                <Bell size={20} />
                {notifications?.filter((n) => !n.read).length > 0 && <span>{notifications.filter((n) => !n.read).length}</span>}
              </button>
              {showNotifications && (
                <div className="notification-popover">
                  <div className="popover-header"><strong>Notificações</strong><button onClick={onRefreshNotifications}><RefreshCw size={15} /></button></div>
                  {notifications?.length ? notifications.slice(0, 8).map((n) => (
                    <div key={n.id} className={`notification-item ${n.read ? "read" : ""}`}>
                      <StatusBadge value={n.level} label={n.title} />
                      <p>{n.message}</p>
                      <small>{fmtDate(n.created_at)}</small>
                    </div>
                  )) : <p className="muted padded">Nenhuma notificação.</p>}
                </div>
              )}
            </div>
            <div className="user-chip">
              <div>{(me?.profile?.full_name || me?.username || "U").slice(0, 1).toUpperCase()}</div>
              <span><strong>{me?.profile?.full_name || me?.username}</strong><small>{me?.permissions?.role === "ADMIN" ? "Administrador" : "Operador"}</small></span>
            </div>
          </div>
        </header>
        <div className="page-container">{children}</div>
      </main>
    </div>
  );
}

export function PageHeader({ title, description, actions }) {
  return (
    <div className="page-header">
      <div><h2>{title}</h2><p>{description}</p></div>
      <div className="page-actions">{actions}</div>
    </div>
  );
}

export function MetricCard({ label, value, icon: Icon, tone = "default", detail }) {
  return (
    <div className={`metric-card metric-${tone}`}>
      <div className="metric-icon"><Icon size={21} /></div>
      <div><span>{label}</span><strong>{value}</strong>{detail && <small>{detail}</small>}</div>
    </div>
  );
}
