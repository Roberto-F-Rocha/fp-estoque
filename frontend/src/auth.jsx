import { React, useState, api, getError, Logo, Button, Modal, Field, Eye, EyeOff } from "./shared.jsx";

export function Setup({ onComplete }) {
  const [form, setForm] = useState({
    full_name: "",
    username: "admin",
    email: "",
    password: "",
    password_confirmation: "",
  });
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function change(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await api.post("desktop/setup/", form);
      onComplete(response.data.username);
    } catch (err) {
      setError(getError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-page">
      <div className="login-accent" />
      <section className="login-showcase" aria-label="FP Depósito de Bebidas">
        <img src={`${import.meta.env.BASE_URL}fp-logo.svg`} alt="Logomarca do FP Depósito de Bebidas" />
      </section>
      <form className="login-card setup-card" onSubmit={submit}>
        <Logo />
        <div className="login-heading">
          <p>Primeiro acesso nesta máquina</p>
          <h1>Crie o administrador</h1>
        </div>
        <Field label="Nome completo" required>
          <input value={form.full_name} onChange={(event) => change("full_name", event.target.value)} autoFocus required />
        </Field>
        <Field label="Nome de usuário" required>
          <input value={form.username} onChange={(event) => change("username", event.target.value)} autoComplete="username" required />
        </Field>
        <Field label="E-mail">
          <input type="email" value={form.email} onChange={(event) => change("email", event.target.value)} />
        </Field>
        <Field label="Senha" required>
          <div className="password-input">
            <input type={show ? "text" : "password"} minLength={8} value={form.password} onChange={(event) => change("password", event.target.value)} autoComplete="new-password" required />
            <button type="button" onClick={() => setShow(!show)} aria-label="Mostrar ou ocultar senha">{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
          </div>
        </Field>
        <Field label="Confirmar senha" required>
          <input type={show ? "text" : "password"} minLength={8} value={form.password_confirmation} onChange={(event) => change("password_confirmation", event.target.value)} autoComplete="new-password" required />
        </Field>
        <p className="muted">Os dados, usuários e imagens ficarão armazenados somente nesta máquina.</p>
        {error && <div className="form-error">{error}</div>}
        <Button disabled={busy}>{busy ? "Criando administrador..." : "Concluir configuração"}</Button>
      </form>
    </main>
  );
}

export function Login({ onLogin, initialUsername = "admin" }) {
  const [username, setUsername] = useState(initialUsername);
  const [password, setPassword] = useState("");
  const [show, setShow] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [forgot, setForgot] = useState(false);
  const [identifier, setIdentifier] = useState("");
  const [recovery, setRecovery] = useState(null);
  const [newPassword, setNewPassword] = useState("");

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await api.post("auth/login/", { username, password });
      localStorage.setItem("fp_access", response.data.access);
      localStorage.setItem("fp_refresh", response.data.refresh);
      onLogin();
    } catch (err) {
      setError(getError(err) || "Usuário ou senha inválidos.");
    } finally {
      setBusy(false);
    }
  }

  async function requestRecovery(event) {
    event.preventDefault();
    setError("");
    try {
      const response = await api.post("auth/forgot-password/", { identifier });
      setRecovery(response.data);
    } catch (err) {
      setError(getError(err));
    }
  }

  async function resetPassword(event) {
    event.preventDefault();
    try {
      await api.post("auth/reset-password/", { uid: recovery.uid, token: recovery.token, password: newPassword });
      setForgot(false);
      setRecovery(null);
      setError("");
      alert("Senha redefinida. Faça login com a nova senha.");
    } catch (err) {
      setError(getError(err));
    }
  }

  return (
    <main className="login-page">
      <div className="login-accent" />
      <section className="login-showcase" aria-label="FP Depósito de Bebidas">
        <img src={`${import.meta.env.BASE_URL}fp-logo.svg`} alt="Logomarca do FP Depósito de Bebidas" />
      </section>
      <form className="login-card" onSubmit={submit}>
        <Logo />
        <div className="login-heading">
          <p>Controle interno de estoque</p>
          <h1>Acesse o sistema</h1>
        </div>
        <Field label="E-mail ou nome de usuário" required>
          <input autoComplete="username" value={username} onChange={(event) => setUsername(event.target.value)} required />
        </Field>
        <Field label="Senha" required>
          <div className="password-input">
            <input type={show ? "text" : "password"} autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required />
            <button type="button" onClick={() => setShow(!show)} aria-label="Mostrar ou ocultar senha">{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
          </div>
        </Field>
        {error && <div className="form-error">{error}</div>}
        <Button disabled={busy}>{busy ? "Entrando..." : "Entrar"}</Button>
        <button type="button" className="link-button" onClick={() => { setForgot(true); setError(""); }}>Esqueci minha senha</button>
      </form>
      {forgot && (
        <Modal title="Recuperação de senha" onClose={() => setForgot(false)}>
          {!recovery?.uid ? (
            <form className="form-grid" onSubmit={requestRecovery}>
              <Field label="E-mail ou usuário" required><input value={identifier} onChange={(event) => setIdentifier(event.target.value)} required /></Field>
              <p className="muted full">Como o sistema é local, a recuperação é gerada diretamente nesta máquina.</p>
              {error && <div className="form-error full">{error}</div>}
              <div className="form-actions full"><Button>Gerar recuperação</Button></div>
            </form>
          ) : (
            <form className="form-grid" onSubmit={resetPassword}>
              <Field label="Nova senha" required><input type="password" minLength={8} value={newPassword} onChange={(event) => setNewPassword(event.target.value)} required /></Field>
              <div className="form-actions full"><Button>Redefinir senha</Button></div>
            </form>
          )}
        </Modal>
      )}
    </main>
  );
}
