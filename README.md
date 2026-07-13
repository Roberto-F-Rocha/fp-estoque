# FP Estoque

Sistema web responsivo para controle interno de estoque do **FP Depósito de Bebidas**.

## Tecnologias

- React + Vite no front-end;
- Django REST Framework no back-end;
- autenticação JWT;
- PostgreSQL hospedado no Supabase;
- geração de relatório diário em PDF;
- documentação OpenAPI/Swagger.

## Supabase configurado

O projeto já foi criado e o schema inicial já foi aplicado no Supabase.

| Configuração | Valor |
|---|---|
| Projeto | `fp-estoque` |
| Project ID | `rstfrilzzybdaelinmzb` |
| Região | `sa-east-1` — São Paulo |
| URL | `https://rstfrilzzybdaelinmzb.supabase.co` |

As tabelas do Django e do módulo de estoque já existem no banco. As migrações SQL aplicadas estão versionadas em:

```text
supabase/migrations/20260712205806_django_inventory_initial_schema.sql
supabase/migrations/20260712212000_deny_direct_postgrest_inventory_access.sql
```

Nenhuma senha, chave privada ou credencial administrativa é armazenada no GitHub.

## Requisitos locais

Instale:

- Python 3.12 ou superior;
- Node.js 22 ou superior;
- Git.

Não é necessário instalar PostgreSQL nem Docker.

## 1. Baixar a branch do projeto

```powershell
git clone -b feat/sistema-completo https://github.com/Roberto-F-Rocha/fp-estoque.git
cd fp-estoque
```

Caso o projeto já esteja clonado:

```powershell
git switch feat/sistema-completo
git pull origin feat/sistema-completo
```

## 2. Configurar as variáveis de ambiente

Crie o arquivo `.env` na raiz:

```powershell
Copy-Item .env.example .env
```

No painel do Supabase, acesse **Project Settings → Database** e copie ou redefina a senha do banco. Depois, substitua `SUA_SENHA_DO_BANCO` no arquivo `.env`:

```env
DJANGO_SECRET_KEY=gere-uma-chave-secreta-forte
DEBUG=true

SUPABASE_PROJECT_ID=rstfrilzzybdaelinmzb
SUPABASE_URL=https://rstfrilzzybdaelinmzb.supabase.co
DATABASE_URL=postgresql://postgres:SUA_SENHA_DO_BANCO@db.rstfrilzzybdaelinmzb.supabase.co:5432/postgres?sslmode=require

ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173
VITE_API_URL=http://localhost:8000/api/
```

Caso a senha possua caracteres especiais, faça URL encoding. Outra opção é copiar a URI completa exibida pelo Supabase em **Connect** e utilizá-la como `DATABASE_URL`.

O arquivo `.env` está ignorado pelo Git e não deve ser enviado ao repositório.

## 3. Preparar e executar o back-end

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python manage.py migrate
python manage.py bootstrap_admin
python manage.py runserver
```

O comando `bootstrap_admin` solicitará a senha sem exibi-la no terminal. Também é possível informar o usuário e o e-mail:

```powershell
python manage.py bootstrap_admin --username admin --email seuemail@exemplo.com
```

Endereços do back-end:

- API: `http://localhost:8000/api/`
- Django Admin: `http://localhost:8000/admin/`
- Swagger: `http://localhost:8000/api/docs/`
- OpenAPI: `http://localhost:8000/api/schema/`

## 4. Preparar e executar o front-end

Abra outro PowerShell na raiz do projeto:

```powershell
cd frontend
npm install
npm run dev
```

Acesse:

```text
http://localhost:5173
```

Entre com o usuário e a senha criados pelo comando `bootstrap_admin`.

## Estrutura principal

```text
fp-estoque/
├── backend/
│   ├── config/
│   ├── inventory/
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   └── package.json
├── supabase/
│   └── migrations/
├── .env.example
└── README.md
```

## Banco de dados

O fluxo da aplicação é:

```text
React → Django REST Framework → PostgreSQL do Supabase
```

O front-end não acessa o banco diretamente. Todas as validações e operações de estoque passam pela API Django.

## Segurança

- a conexão PostgreSQL exige SSL;
- as tabelas de estoque estão com Row Level Security habilitada;
- foram criadas políticas explícitas de bloqueio para `anon` e `authenticated`;
- os privilégios públicos das tabelas e sequências foram revogados;
- o acesso aos dados ocorre exclusivamente pela API Django;
- o estoque não pode ficar negativo;
- as movimentações são registradas com usuário, data e quantidade anterior/final;
- a verificação de segurança do Supabase não apresenta alertas ativos.

## Relatório diário

Na opção **Relatório diário**, selecione a data atual ou uma data anterior. O sistema gera um PDF contendo as movimentações, entradas, saídas, ajustes, responsáveis, quantidades e valores relevantes do dia escolhido.
