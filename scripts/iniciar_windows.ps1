$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot\..
python scripts\gerar_env.py
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel preparar .env' }
Write-Host 'Para usar IA generativa, edite .env e preencha OPENAI_API_KEY. Sem chave, funcionara o modo de trechos oficiais.'
Read-Host 'Pressione ENTER quando o arquivo .env estiver pronto'
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar Docker Compose' }
Start-Process 'http://localhost:5678'
Read-Host 'Crie a conta proprietaria no n8n. Apos concluir, pressione ENTER para importar os workflows'
python scripts\instalar_workflows.py
if ($LASTEXITCODE -ne 0) { throw 'Falha ao instalar workflows; veja README.md' }
Start-Process 'http://localhost:8080'
