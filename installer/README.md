# Instalador

O caminho recomendado e gerar primeiro o `.exe` com:

```powershell
.\scripts\build_exe.ps1
```

Depois, para um MSI, use WiX Toolset apontando para:

```text
backend\dist\SistemaDeSenhas.exe
```

Para um instalador `.exe` simples, Inno Setup tambem funciona bem. O aplicativo nao precisa instalar banco de dados, servico Windows ou servidor remoto.
