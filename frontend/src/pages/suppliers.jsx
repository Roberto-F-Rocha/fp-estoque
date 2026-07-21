import {
  React,
  useEffect,
  useMemo,
  useState,
  api,
  fmtMoney,
  getError,
  Button,
  Modal,
  Field,
  Pagination,
  DataTable,
  Pencil,
  Plus,
  RefreshCw,
} from "../shared.jsx";
import { PageHeader } from "../layout.jsx";
import { useList, SearchBar } from "./listing.jsx";

const FALLBACK_STATES = [
  ["AC", "Acre"], ["AL", "Alagoas"], ["AP", "Amapá"], ["AM", "Amazonas"],
  ["BA", "Bahia"], ["CE", "Ceará"], ["DF", "Distrito Federal"], ["ES", "Espírito Santo"],
  ["GO", "Goiás"], ["MA", "Maranhão"], ["MT", "Mato Grosso"], ["MS", "Mato Grosso do Sul"],
  ["MG", "Minas Gerais"], ["PA", "Pará"], ["PB", "Paraíba"], ["PR", "Paraná"],
  ["PE", "Pernambuco"], ["PI", "Piauí"], ["RJ", "Rio de Janeiro"], ["RN", "Rio Grande do Norte"],
  ["RS", "Rio Grande do Sul"], ["RO", "Rondônia"], ["RR", "Roraima"], ["SC", "Santa Catarina"],
  ["SP", "São Paulo"], ["SE", "Sergipe"], ["TO", "Tocantins"],
].map(([code, name]) => ({ code, name }));

const supplierInitial = {
  name: "",
  corporate_name: "",
  document: "",
  state_registration: "",
  contact_name: "",
  phone: "",
  whatsapp: "",
  email: "",
  cep: "",
  address: "",
  address_number: "",
  district: "",
  city: "",
  city_search: "",
  state: "",
  notes: "",
  active: true,
};

const normalize = (value) => String(value || "")
  .normalize("NFD")
  .replace(/[\u0300-\u036f]/g, "")
  .toLowerCase()
  .trim();

const cityLabel = (city) => `${city.name} — ${city.state}`;

export function SuppliersPage({ notify, me }) {
  const list = useList("suppliers/");
  const [form, setForm] = useState(null);
  const [states, setStates] = useState(FALLBACK_STATES);
  const [cities, setCities] = useState([]);
  const [loadingLocalities, setLoadingLocalities] = useState(false);
  const [localitiesLoaded, setLocalitiesLoaded] = useState(false);

  useEffect(() => {
    if (!form || localitiesLoaded || loadingLocalities) return;
    setLoadingLocalities(true);
    api.get("localidades/")
      .then((response) => {
        if (response.data.states?.length) setStates(response.data.states);
        setCities(response.data.cities || []);
        setLocalitiesLoaded(true);
      })
      .catch((error) => {
        notify(getError(error), "error");
      })
      .finally(() => setLoadingLocalities(false));
  }, [form, localitiesLoaded, loadingLocalities, notify]);

  const citySuggestions = useMemo(() => {
    if (!form) return [];
    const query = normalize(form.city_search || form.city);
    return cities
      .filter((city) => !form.state || city.state === form.state)
      .filter((city) => !query || normalize(city.name).includes(query) || normalize(cityLabel(city)).includes(query))
      .slice(0, 500);
  }, [cities, form]);

  function change(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function openNew() {
    setForm({ ...supplierInitial });
  }

  function openEdit(row) {
    setForm({
      ...supplierInitial,
      ...row,
      corporate_name: "",
      city_search: row.city ? `${row.city}${row.state ? ` — ${row.state}` : ""}` : "",
    });
  }

  function changeState(value) {
    setForm((current) => {
      const selectedCity = cities.find((city) => normalize(city.name) === normalize(current.city));
      const keepCity = selectedCity && selectedCity.state === value;
      return {
        ...current,
        state: value,
        city: keepCity ? current.city : "",
        city_search: keepCity ? `${current.city} — ${value}` : "",
      };
    });
  }

  function changeCity(value) {
    const normalizedValue = normalize(value);
    const exactLabel = cities.find((city) => normalize(cityLabel(city)) === normalizedValue);
    const exactCities = cities.filter(
      (city) => (!form.state || city.state === form.state) && normalize(city.name) === normalizedValue,
    );
    const exactCity = exactLabel || (exactCities.length === 1 ? exactCities[0] : null);

    if (exactCity) {
      setForm((current) => ({
        ...current,
        city: exactCity.name,
        city_search: cityLabel(exactCity),
        state: exactCity.state,
      }));
      return;
    }

    setForm((current) => ({
      ...current,
      city_search: value,
      city: value.split(" — ")[0].trim(),
    }));
  }

  async function save(event) {
    event.preventDefault();
    try {
      const payload = {
        name: form.name.trim(),
        corporate_name: "",
        document: form.document || null,
        state_registration: form.state_registration || "",
        contact_name: form.contact_name || "",
        phone: form.phone || "",
        whatsapp: form.whatsapp || "",
        email: form.email || "",
        cep: form.cep || "",
        address: form.address || "",
        address_number: form.address_number || "",
        district: form.district || "",
        city: form.city || "",
        state: form.state || "",
        notes: form.notes || "",
        active: Boolean(form.active),
      };

      if (form.id) await api.put(`suppliers/${form.id}/`, payload);
      else await api.post("suppliers/", payload);

      notify("Fornecedor salvo com sucesso.");
      setForm(null);
      list.reload();
    } catch (error) {
      notify(getError(error), "error");
    }
  }

  return (
    <>
      <PageHeader
        actions={
          me.permissions.is_admin && (
            <Button icon={Plus} onClick={openNew}>Novo fornecedor</Button>
          )
        }
      />

      <div className="filters-bar">
        <SearchBar
          value={list.params.search || ""}
          onChange={(search) => list.setParams({ ...list.params, search, page: 1 })}
          placeholder="Fornecedor, documento, responsável ou cidade..."
        />
      </div>

      <section className="panel">
        <DataTable
          loading={list.loading}
          rows={list.rows}
          columns={[
            { key: "name", label: "Fornecedor", render: (row) => <strong>{row.name}</strong> },
            { key: "document", label: "CNPJ/CPF" },
            { key: "contact_name", label: "Responsável" },
            { key: "phone", label: "Telefone do responsável" },
            { key: "whatsapp", label: "WhatsApp do responsável" },
            {
              key: "city",
              label: "Cidade/UF",
              render: (row) => `${row.city || "-"}${row.state ? `/${row.state}` : ""}`,
            },
            { key: "entries_count", label: "Entradas" },
            { key: "entries_value", label: "Valor recebido", render: (row) => fmtMoney(row.entries_value) },
            {
              key: "actions",
              label: "Ações",
              render: (row) => me.permissions.is_admin ? (
                <div className="row-actions">
                  <button onClick={() => openEdit(row)} aria-label={`Editar ${row.name}`}><Pencil size={16} /></button>
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
        <Modal title={form.id ? "Editar fornecedor" : "Novo fornecedor"} onClose={() => setForm(null)} size="xl">
          <form className="form-grid cols-3" onSubmit={save}>
            <Field label="Nome do fornecedor" required>
              <input value={form.name} onChange={(event) => change("name", event.target.value)} required autoFocus />
            </Field>

            <Field label="CNPJ ou CPF">
              <input value={form.document || ""} onChange={(event) => change("document", event.target.value)} />
            </Field>

            <Field label="Inscrição estadual">
              <input value={form.state_registration || ""} onChange={(event) => change("state_registration", event.target.value)} />
            </Field>

            <Field label="Nome do responsável">
              <input value={form.contact_name || ""} onChange={(event) => change("contact_name", event.target.value)} />
            </Field>

            <Field label="Telefone do responsável">
              <input value={form.phone || ""} onChange={(event) => change("phone", event.target.value)} />
            </Field>

            <Field label="WhatsApp do responsável">
              <input value={form.whatsapp || ""} onChange={(event) => change("whatsapp", event.target.value)} />
            </Field>

            <Field label="E-mail do responsável">
              <input type="email" value={form.email || ""} onChange={(event) => change("email", event.target.value)} />
            </Field>

            <Field label="CEP">
              <input value={form.cep || ""} onChange={(event) => change("cep", event.target.value)} />
            </Field>

            <Field label="Endereço">
              <input value={form.address || ""} onChange={(event) => change("address", event.target.value)} />
            </Field>

            <Field label="Número">
              <input value={form.address_number || ""} onChange={(event) => change("address_number", event.target.value)} />
            </Field>

            <Field label="Bairro">
              <input value={form.district || ""} onChange={(event) => change("district", event.target.value)} />
            </Field>

            <Field label="Estado (UF)" hint="Ao escolher a UF, a lista de cidades será filtrada automaticamente.">
              <select value={form.state || ""} onChange={(event) => changeState(event.target.value)}>
                <option value="">Selecione ou escolha primeiro a cidade</option>
                {states.map((state) => (
                  <option key={state.code} value={state.code}>{state.name} ({state.code})</option>
                ))}
              </select>
            </Field>

            <Field
              label="Cidade"
              hint={loadingLocalities ? "Carregando cidades do IBGE..." : "Digite parte do nome ou abra a lista. Ao selecionar a cidade, a UF será preenchida."}
            >
              <div className="city-input-wrap">
                <input
                  list="supplier-city-options"
                  value={form.city_search || ""}
                  onChange={(event) => changeCity(event.target.value)}
                  placeholder={loadingLocalities ? "Carregando cidades..." : "Digite ou selecione uma cidade"}
                  disabled={loadingLocalities}
                  autoComplete="off"
                />
                {loadingLocalities && <RefreshCw className="spin city-loading-icon" size={17} />}
              </div>
              <datalist id="supplier-city-options">
                {citySuggestions.map((city) => (
                  <option key={city.id} value={cityLabel(city)} />
                ))}
              </datalist>
            </Field>

            <Field label="Observações">
              <textarea value={form.notes || ""} onChange={(event) => change("notes", event.target.value)} />
            </Field>

            <Field label="Situação">
              <select value={String(form.active)} onChange={(event) => change("active", event.target.value === "true")}>
                <option value="true">Ativo</option>
                <option value="false">Inativo</option>
              </select>
            </Field>

            <div className="form-actions full">
              <Button type="button" variant="secondary" onClick={() => setForm(null)}>Cancelar</Button>
              <Button>Salvar fornecedor</Button>
            </div>
          </form>
        </Modal>
      )}
    </>
  );
}
