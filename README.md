# FP Estoque Desktop — Depósito de Bebidas

Versão desktop do sistema interno de estoque do **FP Depósito de Bebidas**. O programa funciona diretamente na máquina, abre em uma janela própria e não depende de navegador, servidor de hospedagem, PostgreSQL, Supabase ou qualquer banco de dados externo.

## Como os dados são armazenados

Todo o conteúdo fica em arquivos locais:

- Banco principal: `fp-estoque.sqlite3`.
- Imagens dos produtos: pasta `media/products`.
- Backups automáticos: pasta `backups`.
- Chave interna do sistema: arquivo `.secret-key`.

No Windows, a pasta padrão é:

```text
%LOCALAPPDATA%\FP Estoque
```

O banco SQLite é um arquivo único e pode ser copiado junto com a pasta `media` para realizar uma cópia de segurança completa. O aplicativo mantém automaticamente os 30 backups mais recentes do banco.

## Funcionalidades

- Login local, recuperação de senha e perfis Administrador/Operador.
- Configuração do primeiro administrador na primeira abertura.
- Cadastro e inativação de usuários, produtos, categorias e fornecedores.
- Produtos com SKU, código de barras, preços, estoque mínimo/máximo, localização e imagem local.
- Entradas em rascunho, confirmação, custo médio e cancelamento com estorno.
- Saídas em rascunho, validação de saldo, seleção de lote e consumo FEFO.
- Ajustes positivos/negativos com justificativa e permissão administrativa.
- Lotes, fabricação, validade, alertas e estoque por lote.
- Inventários físicos, divergências e ajustes controlados.
- Histórico imutável de movimentações, estornos e logs de auditoria.
- Dashboard de vendas, lucro e posição atual do estoque.
- Central de alertas e notificações.
- 18 tipos de relatórios com pré-visualização e exportação em PDF ou Excel (`.xlsx`).

## Arquitetura local

- **Interface:** React compilado e incorporado ao aplicativo.
- **Regras do sistema:** Django REST Framework executado somente em `127.0.0.1`.
- **Banco:** SQLite local.
- **Janela desktop:** PyWebView com o mecanismo nativo do Windows.
- **Executável:** PyInstaller.

O serviço interno existe apenas para a comunicação entre a janela e as regras do sistema na própria máquina. Ele não é publicado na internet e não precisa ser aberto em um navegador.

## Executar durante o desenvolvimento

Na raiz do projeto, execute:

```cmd
scripts\run_desktop_dev.bat
```

O script:

1. cria o ambiente virtual Python;
2. instala as dependências;
3. compila a interface React;
4. aplica as migrações no arquivo SQLite;
5. abre o FP Estoque em uma janela própria.

Na primeira abertura, o sistema solicitará:

- nome completo do administrador;
- nome de usuário;
- e-mail opcional;
- senha e confirmação.

Não existe senha padrão gravada no projeto.

## Gerar o executável Windows

Execute:

```cmd
scripts\build_desktop.bat
```

Ao concluir, o aplicativo estará em:

```text
dist\FP Estoque\FP Estoque.exe
```

A pasta inteira `dist\FP Estoque` deve ser mantida junto do executável. Ela pode ser copiada para outra máquina Windows.

## Configuração opcional

O sistema funciona sem arquivo `.env`. Para mudar a pasta dos dados ou a porta interna:

```cmd
copy .env.example .env
notepad .env
```

Principais opções:

```env
FP_DATA_DIR=D:\FP Estoque Dados
FP_DESKTOP_PORT=8765
DEBUG=false
```

Não adicione `DATABASE_URL`, chaves do Supabase ou credenciais de nuvem nesta versão.

## Backup e transferência para outra máquina

Para copiar todos os dados:

1. feche o FP Estoque;
2. abra `%LOCALAPPDATA%\FP Estoque`;
3. copie toda a pasta para um local seguro.

Para transferir o sistema:

1. instale ou copie o aplicativo na nova máquina;
2. execute-o uma vez e feche;
3. substitua a pasta `%LOCALAPPDATA%\FP Estoque` pela cópia anterior;
4. abra novamente o programa.

## Desenvolvimento manual

### Backend

```cmd
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements-desktop.txt
python manage.py migrate
```

### Interface desktop

```cmd
cd frontend
npm install
npm run build:desktop
```

### Abrir a janela

Na raiz do projeto:

```cmd
backend\.venv\Scripts\python.exe desktop\app.py
```

## Testes

```cmd
cd backend
.venv\Scripts\activate
python manage.py test inventory -v 2
```

```cmd
cd frontend
npm install
npm run build
npm run build:desktop
```

A integração contínua também gera um pacote Windows para validar o executável.

## Segurança local

- Senhas armazenadas com o hash nativo do Django.
- Autenticação JWT e permissões verificadas no frontend e backend.
- Serviço restrito ao endereço local `127.0.0.1`.
- Banco e imagens não são enviados para serviços externos.
- Chave interna gerada automaticamente na pasta local de dados.
- Backups automáticos mantidos na própria máquina.

Esta branch é uma alternativa local à versão conectada ao Supabase. Nenhuma alteração desta versão é aplicada à branch web original.
