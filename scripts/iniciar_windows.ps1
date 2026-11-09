$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
if (-not (Test-Path '.env')) {
    throw 'Arquivo .env do PostgreSQL ausente. Restaure seu backup privado antes de iniciar; nao gere novas senhas sobre volumes existentes.'
}
$pasta = Join-Path $HOME 'Documents\UBS-Backup\migracao-n8n'
$composeN8n = Join-Path $pasta 'compose.yaml'
if (-not (Test-Path $composeN8n)) {
    throw "Compose do novo n8n ausente em $composeN8n. Consulte docs/MIGRACAO_N8N.md; nao reative o n8n antigo."
}
if (-not (Test-Path (Join-Path $pasta '.env'))) {
    throw 'Chave nova ausente na pasta privada de migracao. Restaure o .env novo de seu backup; nao substitua a chave por outra.'
}
Write-Host 'Iniciando banco e FastAPI, sem o n8n legado...'
docker compose up -d --build db api
if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar db/api' }
Write-Host 'Iniciando n8n migrado no Compose privado...'
docker compose -f $composeN8n up -d
if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar n8n migrado' }
Write-Host 'Iniciando proxy Nginx...'
docker compose up -d web
if ($LASTEXITCODE -ne 0) { throw 'Falha ao iniciar Nginx' }
docker compose ps
if ($LASTEXITCODE -ne 0) { throw 'Falha ao conferir o Compose' }
Write-Host 'Concluido: http://localhost:8080 (chat) e http://localhost:5679 (n8n novo).'
Write-Host 'Execute python scripts/validar_execucao.py para teste de ponta a ponta.'
