# Sistema de Senhas

Aplicacao local para armazenar senhas em um arquivo criptografado, com API FastAPI e interface React.

## Stack

- Backend: Python + FastAPI
- Frontend: React + TypeScript + Vite
- Persistencia: arquivo local criptografado em `%APPDATA%\SistemaDeSenhas\vault.senhas`
- Criptografia: Argon2id para derivar chave de senha humana e AES-GCM para proteger o cofre
- Distribuicao: PyInstaller para gerar `.exe`; MSI pode ser criado depois com WiX Toolset usando o `.exe`

## Modelo de acesso

- `admin`: cria, edita, exclui, revela e copia senhas
- `user`: lista, revela e copia senhas, sem funcoes CRUD
- pelo login `admin`, e possivel alterar a senha de login dos perfis `admin` e `user`

Na primeira abertura, a tela de setup cria os dois usuarios e o cofre local. O arquivo `vault.senhas` nao depende de MySQL, PostgreSQL, SQLite ou servidor remoto.

## Desenvolvimento

```powershell
.\scripts\run_dev.ps1
```

URLs:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8777`
- API docs: `http://127.0.0.1:8777/docs`

## Testes

```powershell
cd backend
.\.venv\Scripts\python -m pytest
```

## Build EXE

```powershell
.\scripts\build_exe.ps1
```

O executavel final fica em:

```text
backend\dist\SistemaDeSenhas.exe
```

Ao abrir o `.exe`, ele:

- inicia o backend FastAPI embutido;
- serve o frontend React ja compilado;
- usa `127.0.0.1`, sem expor o app na rede;
- tenta a porta `8777` e, se estiver ocupada, escolhe outra porta local;
- abre o navegador automaticamente;
- grava logs em `%APPDATA%\SistemaDeSenhas\logs\desktop.log`.

## Observacoes de seguranca

- O backend escuta em `127.0.0.1`, nao em `0.0.0.0`.
- As senhas salvas no cofre nao ficam em texto puro no disco.
- As sessoes ficam apenas em memoria e expiram automaticamente.
- O arquivo local deve ser incluído em backup se voce quiser preservar o cofre entre reinstalacoes.
