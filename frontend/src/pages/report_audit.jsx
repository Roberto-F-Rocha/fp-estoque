import {
  React,
  useEffect,
  useState,
  api,
  fmtDate,
  getError,
  Button,
  DataTable,
  Field,
  Pagination,
  StatusBadge,
  Eye,
  FileDown,
  FileText,
  RefreshCw,
  Search,
} from "../shared.jsx";
import { MetricCard, PageHeader } from "../layout.jsx";

const PAGE_SIZE = 20;
const EMPTY_FILTERS = { search: "", status: "", format: "" };

function filterSummary(filters) {
  if (!filters || typeof filters !== "object") return "Sem filtros adicionais";
  const labels = {
    date: "Data",
    start_date: "Início",
    end_date: "Fim",
    product: "Produto",
    category: "Categoria",
    supplier: "Fornecedor",
    movement_type: "Movimentação",
    user: "Usuário",
    lot: "Lote",
    stock_status: "Estoque",
    brand: "Marca",
  };
  const parts = Object.entries(filters)
    .filter(([key, value]) => key !== "type" && value !== "" && value !== null && value !== undefined)
    .map(([key, value]) => `${labels[key] || key}: ${value}`);
  return parts.length ? parts.join(" • ") : "Sem filtros adicionais";
}

function fileSize(value) {
  const bytes = Number(value || 0);
  if (!bytes) return "-";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function statusTone(status) {
  if (status === "SUCCESS") return "done";
  if (status === "FAILED" || status === "FILE_MISSING") return "cancelled";
  if (status === "REQUESTED" || status === "PROCESSING") return "waiting";
  return status;
}

export function ReportAuditPage({ notify }) {
  const [rows, setRows] = useState([]);
  const [summary, setSummary] = useState({ total: 0, success: 0, failed: 0, pdf: 0, xlsx: 0 });
  const [count, setCount] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [opening, setOpening] = useState(null);
  const [filters, setFilters] = useState(EMPTY_FILTERS);

  async function load(targetPage = page, appliedFilters = filters) {
    setLoading(true);
    try {
      const response = await api.get("reports/history/", {
        params: {
          page: targetPage,
          page_size: PAGE_SIZE,
          search: appliedFilters.search,
          status: appliedFilters.status,
          format: appliedFilters.format,
        },
      });
      setRows(response.data.results || []);
      setCount(response.data.count || 0);
      setSummary(response.data.summary || {});
      setPage(response.data.page || targetPage);
    } catch (error) {
      notify(getError(error), "error");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load(1, EMPTY_FILTERS);
  }, []);

  async function openFile(record) {
    setOpening(record.id);
    try {
      const response = await api.post(`reports/history/${record.id}/open/`);
      notify(response.data.detail || "Arquivo aberto no aplicativo padrão.");
      await load(page, filters);
    } catch (error) {
      notify(getError(error), "error");
    } finally {
      setOpening(null);
    }
  }

  function applyFilters(event) {
    event.preventDefault();
    setPage(1);
    load(1, filters);
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS);
    setPage(1);
    load(1, EMPTY_FILTERS);
  }

  const columns = [
    {
      key: "created_at",
      label: "Solicitado em",
      render: (row) => <span className="audit-date">{fmtDate(row.created_at)}</span>,
    },
    { key: "user_name", label: "Usuário" },
    {
      key: "report_name",
      label: "Relatório",
      render: (row) => <div className="audit-report-name"><strong>{row.report_name}</strong></div>,
    },
    {
      key: "format",
      label: "Formato",
      render: (row) => <StatusBadge value={row.format} label={row.format} />,
    },
    {
      key: "status",
      label: "Situação",
      render: (row) => <StatusBadge value={statusTone(row.status)} label={row.status_label} />,
    },
    {
      key: "filters",
      label: "Filtros utilizados",
      render: (row) => <span className="audit-filters" title={filterSummary(row.filters)}>{filterSummary(row.filters)}</span>,
    },
    {
      key: "filename",
      label: "Arquivo",
      render: (row) => row.file_exists ? (
        <button className="table-link audit-file-link" onClick={() => openFile(row)} disabled={opening === row.id}>
          <strong>{row.filename}</strong>
          <small>{fileSize(row.file_size)} • abrir arquivo</small>
        </button>
      ) : (
        <div className="audit-missing-file"><strong>{row.filename || "Sem arquivo"}</strong><small>{row.error || "Arquivo não encontrado na máquina."}</small></div>
      ),
    },
    {
      key: "open_count",
      label: "Aberturas",
      render: (row) => <div><strong>{row.open_count || 0}</strong><small className="audit-open-date">{row.last_opened_at ? fmtDate(row.last_opened_at) : "Nunca aberto"}</small></div>,
    },
    {
      key: "actions",
      label: "Ação",
      render: (row) => (
        <Button
          variant="secondary"
          icon={Eye}
          className="audit-open-button"
          disabled={!row.file_exists || opening === row.id}
          onClick={() => openFile(row)}
        >
          {opening === row.id ? "Abrindo..." : "Abrir"}
        </Button>
      ),
    },
  ];

  return (
    <>
      <PageHeader
        actions={
          <Button variant="secondary" icon={RefreshCw} onClick={() => load(page, filters)} disabled={loading}>
            Atualizar histórico
          </Button>
        }
      />

      <div className="metrics-grid audit-metrics">
        <MetricCard label="Solicitações registradas" value={summary.total || 0} icon={FileDown} tone="gold" />
        <MetricCard label="Concluídas" value={summary.success || 0} icon={FileText} tone="success" />
        <MetricCard label="Falhas" value={summary.failed || 0} icon={FileText} tone="danger" />
        <MetricCard label="Arquivos PDF" value={summary.pdf || 0} icon={FileText} />
        <MetricCard label="Planilhas Excel" value={summary.xlsx || 0} icon={FileDown} />
      </div>

      <form className="filters-bar audit-filter-bar" onSubmit={applyFilters}>
        <div className="search-box">
          <Search size={18} />
          <input
            value={filters.search}
            onChange={(event) => setFilters({ ...filters, search: event.target.value })}
            placeholder="Pesquisar usuário, relatório, arquivo ou erro"
          />
        </div>
        <Field label="Situação">
          <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
            <option value="">Todas</option>
            <option value="SUCCESS">Concluído</option>
            <option value="FAILED">Falhou</option>
            <option value="REQUESTED">Solicitado</option>
            <option value="PROCESSING">Processando</option>
            <option value="FILE_MISSING">Arquivo não encontrado</option>
          </select>
        </Field>
        <Field label="Formato">
          <select value={filters.format} onChange={(event) => setFilters({ ...filters, format: event.target.value })}>
            <option value="">Todos</option>
            <option value="PDF">PDF</option>
            <option value="XLSX">Excel (XLSX)</option>
          </select>
        </Field>
        <Button icon={Search}>Pesquisar</Button>
        <Button type="button" variant="secondary" onClick={clearFilters}>Limpar filtros</Button>
      </form>

      <section className="panel audit-history-panel">
        <div className="panel-title">
          <div>
            <h3>Ouvidoria de relatórios</h3>
            <p>Registro de cada solicitação de PDF ou Excel, incluindo usuário, filtros, resultado e acesso direto ao arquivo.</p>
          </div>
        </div>
        <DataTable
          columns={columns}
          rows={rows}
          loading={loading}
          emptyText="Nenhuma solicitação de relatório foi registrada com os filtros selecionados."
        />
        <Pagination
          page={page}
          count={count}
          pageSize={PAGE_SIZE}
          onChange={(nextPage) => load(nextPage, filters)}
        />
      </section>
    </>
  );
}
