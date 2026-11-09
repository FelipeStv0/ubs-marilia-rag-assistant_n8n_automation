# Configure uma instalacao nova do n8n migrado, SEM sobrescrever credenciais existentes.
# Execute apenas quando for criar uma instalacao nova, nunca para "consertar" erro de chave.
param(
    [string]$Destino = (Join-Path $HOME 'Documents\UBS-Backup\migracao-n8n')
)
$ErrorActionPreference = 'Stop'
$repo = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$template = Join-Path $repo 'deploy\n8n-migrado.compose.yaml'
if (-not (Test-Path $template)) { throw 'Template Compose ausente no repositorio.' }
New-Item -ItemType Directory -Path $Destino -Force | Out-Null
$envPath = Join-Path $Destino '.env'
$composePath = Join-Path $Destino 'compose.yaml'
$volumeName = 'ubs_n8n_nova_data'
$volumeExists = $false
& docker volume inspect $volumeName --format '{{.Name}}' *> $null
$volumeExists = ($LASTEXITCODE -eq 0)

if (-not (Test-Path $envPath)) {
    if ($volumeExists) {
        throw 'O volume do novo n8n ja existe, mas o .env privado esta ausente. Restaure a chave correta de backup. Nenhuma nova chave foi gerada.'
    }
    $bytes = New-Object byte[] 48
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try { $rng.GetBytes($bytes) } finally { $rng.Dispose() }
    $secret = [Convert]::ToBase64String($bytes)
    [System.IO.File]::WriteAllText($envPath, "N8N_ENCRYPTION_KEY=$secret" + [Environment]::NewLine, (New-Object System.Text.UTF8Encoding($false)))
    $secret = $null
    Write-Host 'Novo .env privado criado (chave nao exibida).'
} else {
    Write-Host '.env privado existente preservado. Nenhuma chave foi alterada.'
}
if (-not $volumeExists) {
    & docker volume create $volumeName | Out-Null
    if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel criar volume Docker.' }
}
if (-not (Test-Path $composePath)) {
    Copy-Item $template $composePath
    Write-Host 'Compose privado criado a partir do template.'
} else {
    Write-Host 'Compose privado existente preservado. Compare com deploy/n8n-migrado.compose.yaml antes de atualizar.'
}
Write-Host 'Preparacao concluida. A rede do projeto principal deve existir antes de iniciar o n8n.'
Write-Host 'Nunca publique .env ou backups. Leia docs/MIGRACAO_N8N.md.'
