# Sistema de Senhas

Aplicação local para armazenar senhas em um arquivo criptografado, com API FastAPI e interface React.

## Stack

- Backend: Python + FastAPI
- Frontend: React + TypeScript + Vite
- Persistência: arquivo local criptografado em `%APPDATA%\SistemaDeSenhas\vault.senhas`
- Criptografia: Argon2id para derivar uma chave a partir da senha do usuário e AES-GCM para proteger o cofre
- Distribuição: PyInstaller para gerar `.exe`; um MSI pode ser criado posteriormente com WiX Toolset usando o `.exe`

## Modelo de acesso

- `admin`: cria, edita, exclui, revela e copia senhas
- `user`: lista, revela e copia senhas, sem funções CRUD
- pelo login `admin`, é possível alterar a senha de login dos perfis `admin` e `user`

Na primeira abertura, a tela de configuração inicial cria os dois usuários e o cofre local. O arquivo `vault.senhas` não depende de MySQL, PostgreSQL, SQLite ou servidor remoto.

## Desenvolvimento

```powershell
.\scripts\run_dev.ps1
```

URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8777`
- Documentação da API: `http://127.0.0.1:8777/docs`

## Testes

```powershell
cd backend
.\.venv\Scripts\python -m pytest
```

## Build do EXE

```powershell
.\scripts\build_exe.ps1
```

O executável final fica em:

```text
backend\dist\SistemaDeSenhas.exe
```

Ao abrir o `.exe`, ele:

- inicia o backend FastAPI embutido;
- serve o frontend React já compilado;
- usa `127.0.0.1`, sem expor o app na rede;
- tenta a porta `8777` e, se estiver ocupada, escolhe outra porta local;
- abre o navegador automaticamente;
- grava logs em `%APPDATA%\SistemaDeSenhas\logs\desktop.log`.

## Observações de segurança

- O backend escuta em `127.0.0.1`, não em `0.0.0.0`.
- As senhas salvas no cofre não ficam em texto puro no disco.
- As sessões ficam apenas em memória e expiram automaticamente.
- O arquivo local deve ser incluído em backup se você quiser preservar o cofre entre reinstalações.
