import {
  React,
  useEffect,
  useState,
  api,
  unwrap,
  fmtMoney,
  fmtQty,
  getError,
  Button,
  Modal,
  Field,
  Pagination,
  DataTable,
  StatusBadge,
  Package,
  Pencil,
  Plus,
  Trash2,
} from "../shared.jsx";
import { PageHeader } from "../layout.jsx";
import { useList, SearchBar } from "./listing.jsx";

const productInitial = {
  name: "",
  description: "",
  category: "",
  supplier: "",
  brand: "",
  package_type: "",
  volume: "1",
  volume_unit: "L",
  cost_price: "0",
  sale_price: "0",
  minimum_stock: "0",
  maximum_stock: "0",
  active: true,
};

function presentation(product) {
  const volume = product.volume_label || `${product.volume || "-"} ${product.volume_unit === "ML" ? "mL" : "L"}`;
  return [product.package_type, volume].filter(Boolean).join(" • ");
}

export function ProductsPage({ notify, me }) {
  const list = useList("products/");
  const [search, setSearch] = useState("");
  const [categories, setCategories] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [form, setForm] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get("categories/?page_size=200"),
      api.get("suppliers/?page_size=200"),
    ]).then(([categoryData, supplierData]) => {
      setCategories(unwrap(categoryData.data));
      setSuppliers(unwrap(supplierData.data));
    });
  }, []);

  function change(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function save(event) {
    event.preventDefault();
    try {
      const payload = {
        name: form.name.trim(),
        description: form.description || "",
        category: Number(form.category),
        supplier: form.supplier ? Number(form.supplier) : null,
        brand: form.brand || "",
        package_type: form.package_type || "",
        volume: form.volume,
        volume_unit: form.volume_unit,
        cost_price: form.cost_price,
        sale_price: form.sale_price,
        minimum_stock: form.minimum_stock,
        maximum_stock: form.maximum_stock,
        active: Boolean(form.active),
      };

      if (form.id) await api.put(`products/${form.id}/`, payload);
      else await api.post("products/", payload);

      notify("Produto salvo com sucesso.");
      setForm(null);
      list.reload();
    } catch (error) {
      notify(getError(error), "error");
    }
  }

  async function deactivate(row) {
    if (!confirm(`Inativar ${row.name}?`)) return;
    try {
      await api.delete(`products/${row.id}/`);
      notify("Produto inativado.");
      list.reload();
    } catch (error) {
      notify(getError(error), "error");
    }
  }

  function editProduct(row) {
    setForm({
      ...productInitial,
      ...row,
      category: row.category || "",
      supplier: row.supplier || "",
      volume: row.volume || "1",
      volume_unit: row.volume_unit || "L",
    });
  }

  return (
    <>
      <PageHeader
        actions={
          me.permissions.is_admin && (
            <Button icon={Plus} onClick={() => setForm({ ...productInitial })}>
              Novo produto
            </Button>
          )
        }
      />

      <div className="filters-bar">
        <SearchBar
          value={search}
          onChange={(value) => {
            setSearch(value);
            list.setParams({ ...list.params, search: value, page: 1 });
          }}
          placeholder="Nome, marca ou categoria..."
        />
        <select
          value={list.params.category || ""}
          onChange={(event) => list.setParams({ ...list.params, category: event.target.value, page: 1 })}
        >
          <option value="">Todas as categorias</option>
          {categories.map((category) => (
            <option key={category.id} value={category.id}>{category.name}</option>
          ))}
        </select>
        <select
          value={list.params.stock_level || ""}
          onChange={(event) => list.setParams({ ...list.params, stock_level: event.target.value, page: 1 })}
        >
          <option value="">Todos os níveis</option>
          <option value="normal">Normal</option>
          <option value="low">Estoque baixo</option>
          <option value="out">Sem estoque</option>
        </select>
      </div>

      <section className="panel">
        <DataTable
          loading={list.loading}
          rows={list.rows}
          columns={[
            {
              key: "name",
              label: "Produto",
              render: (row) => (
                <div className="product-cell">
                  <div className="product-placeholder"><Package size={17} /></div>
                  <span>
                    <strong>{row.name}</strong>
                    <small>{row.brand || row.category_name}</small>
                  </span>
                </div>
              ),
            },
            { key: "category_name", label: "Categoria" },
            {
              key: "presentation",
              label: "Apresentação",
              render: (row) => presentation(row) || "Não informada",
            },
            {
              key: "stock",
              label: "Estoque",
              render: (row) => <strong>{fmtQty(row.stock)} unidades</strong>,
            },
            {
              key: "level",
              label: "Situação",
              render: (row) => (
                <StatusBadge
                  value={Number(row.stock) <= 0 ? "out" : row.low_stock ? "low" : "normal"}
                  label={Number(row.stock) <= 0 ? "Sem estoque" : row.low_stock ? "Estoque baixo" : "Normal"}
                />
              ),
            },
            { key: "cost_price", label: "Custo", render: (row) => fmtMoney(row.cost_price) },
            { key: "sale_price", label: "Venda", render: (row) => fmtMoney(row.sale_price) },
            { key: "stock_value", label: "Valor em estoque", render: (row) => fmtMoney(row.stock_value) },
            {
              key: "actions",
              label: "Ações",
              render: (row) => me.permissions.is_admin ? (
                <div className="row-actions">
                  <button onClick={() => editProduct(row)} aria-label={`Editar ${row.name}`}><Pencil size={16} /></button>
                  <button className="danger" onClick={() => deactivate(row)} aria-label={`Inativar ${row.name}`}><Trash2 size={16} /></button>
                </div>
              ) : "-",
            },
          ]}
        />
        <Pagination
          page={list.params.page}
          count={list.count}
          onChange={(page) => list.setParams({ ...list.params, page })}
        />
      </section>

      {form && (
        <Modal title={form.id ? "Editar produto" : "Novo produto"} onClose={() => setForm(null)} size="xl">
          <form className="form-grid cols-3" onSubmit={save}>
            <Field label="Nome do produto" required>
              <input value={form.name} onChange={(event) => change("name", event.target.value)} required autoFocus />
            </Field>

            <Field label="Categoria" required>
              <select value={form.category} onChange={(event) => change("category", event.target.value)} required>
                <option value="">Selecione</option>
                {categories.map((category) => (
                  <option key={category.id} value={category.id}>{category.name}</option>
                ))}
              </select>
            </Field>

            <Field label="Fornecedor principal">
              <select value={form.supplier || ""} onChange={(event) => change("supplier", event.target.value)}>
                <option value="">Não informado</option>
                {suppliers.map((supplier) => (
                  <option key={supplier.id} value={supplier.id}>{supplier.name}</option>
                ))}
              </select>
            </Field>

            <Field label="Marca">
              <input value={form.brand || ""} onChange={(event) => change("brand", event.target.value)} />
            </Field>

            <Field label="Tipo de embalagem" hint="Ex.: garrafa de vidro, lata, garrafa PET ou caixa.">
              <input
                value={form.package_type || ""}
                onChange={(event) => change("package_type", event.target.value)}
                placeholder="Ex.: Garrafa de vidro"
              />
            </Field>

            <Field label="Volume" required>
              <input
                type="number"
                min="0.001"
                step="0.001"
                value={form.volume}
                onChange={(event) => change("volume", event.target.value)}
                placeholder="Ex.: 1, 350 ou 965"
                required
              />
            </Field>

            <Field label="Unidade do volume" required>
              <select value={form.volume_unit} onChange={(event) => change("volume_unit", event.target.value)} required>
                <option value="ML">Mililitro (mL)</option>
                <option value="L">Litro (L)</option>
              </select>
            </Field>

            <div className="product-presentation-preview">
              <span>Apresentação final</span>
              <strong>
                {[form.package_type, `${form.volume || "0"} ${form.volume_unit === "ML" ? "mL" : "L"}`]
                  .filter(Boolean)
                  .join(" • ")}
              </strong>
            </div>

            <Field label="Preço de custo">
              <input type="number" min="0" step="0.01" value={form.cost_price} onChange={(event) => change("cost_price", event.target.value)} />
            </Field>

            <Field label="Preço de venda">
              <input type="number" min="0" step="0.01" value={form.sale_price} onChange={(event) => change("sale_price", event.target.value)} />
            </Field>

            <Field label="Estoque mínimo">
              <input type="number" min="0" step="0.001" value={form.minimum_stock} onChange={(event) => change("minimum_stock", event.target.value)} />
            </Field>

            <Field label="Estoque máximo">
              <input type="number" min="0" step="0.001" value={form.maximum_stock} onChange={(event) => change("maximum_stock", event.target.value)} />
            </Field>

            <Field label="Descrição">
              <textarea value={form.description || ""} onChange={(event) => change("description", event.target.value)} />
            </Field>

            <Field label="Situação">
              <select value={String(form.active)} onChange={(event) => change("active", event.target.value === "true")}>
                <option value="true">Ativo</option>
                <option value="false">Inativo</option>
              </select>
            </Field>

            <div className="form-actions full">
              <Button type="button" variant="secondary" onClick={() => setForm(null)}>Cancelar</Button>
              <Button>Salvar produto</Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
