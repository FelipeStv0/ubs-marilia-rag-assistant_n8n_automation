$ErrorActionPreference = 'Stop'
$repo = 'https://github.com/FelipeStv0/ubs-marilia-rag-assistant_n8n_automation.git'

function Run-Git {
  & git @args
  if ($LASTEXITCODE -ne 0) { throw "Comando git falhou: git $($args -join ' ')" }
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
  Write-Host 'Git nao esta instalado. Instale em https://git-scm.com/downloads/win' -ForegroundColor Red
  exit 1
}

if (-not (Test-Path 'docker-compose.yml') -or -not (Test-Path 'workflows/01-atualizacao-fontes.json')) {
  Write-Host 'Abra o PowerShell na pasta PRINCIPAL do projeto (com docker-compose.yml e workflows) e execute novamente.' -ForegroundColor Red
  exit 1
}

# Impede a inclusao acidental de arquivos locais sensiveis.
$ignoreFile = '.gitignore'
$needed = @('.env', '.env.*', '!.env.example', '__pycache__/', '.pytest_cache/', '*.pyc', '*.log', 'data/', '*.sqlite', '*.db')
$existing = if (Test-Path $ignoreFile) { @(Get-Content $ignoreFile) } else { @() }
foreach ($rule in $needed) {
  if ($existing -notcontains $rule) { Add-Content -Path $ignoreFile -Value $rule -Encoding UTF8 }
}

if (-not (Test-Path '.git')) { Run-Git init }
Run-Git add -A

$files = @(& git diff --cached --name-only)
if ($LASTEXITCODE -ne 0) { throw 'Nao foi possivel inspecionar os arquivos preparados.' }
$bad = @($files | Where-Object { $_ -match '(^|/)(\.env($|\.(?!example$))|id_rsa|id_ed25519|.*\.pem$|.*\.key$|.*\.sqlite$|.*\.db$)' })
if ($bad.Count -gt 0) {
  Write-Host 'Publicacao interrompida: arquivos potencialmente sensiveis estao preparados:' -ForegroundColor Red
  $bad | ForEach-Object { Write-Host "- $_" }
  exit 1
}

Write-Host "Arquivos preparados: $($files.Count)" -ForegroundColor Cyan
if ($files.Count -eq 0) { Write-Host 'Nenhuma alteracao nova para publicar.'; exit 0 }

# Configura identidade de commit apenas se ainda nao estiver definida.
$name = (& git config user.name)
$email = (& git config user.email)
if ([string]::IsNullOrWhiteSpace($name) -or [string]::IsNullOrWhiteSpace($email)) {
  Write-Host 'Configure nome e e-mail do Git antes de continuar:' -ForegroundColor Yellow
  Write-Host 'git config --global user.name "Seu nome"'
  Write-Host 'git config --global user.email "seu-email-do-github"'
  exit 1
}

Run-Git commit -m 'feat: publica assistente UBS Marilia com n8n, API e busca oficial'
Run-Git branch -M main
$remotes = @(& git remote)
if ($remotes -contains 'origin') {
  $current = (& git remote get-url origin).Trim()
  if ($current -ne $repo) {
    Write-Host "Origin atual: $current" -ForegroundColor Red
    Write-Host 'Nao alterei o destino automaticamente por seguranca.'
    exit 1
  }
} else { Run-Git remote add origin $repo }
Run-Git push -u origin main
Write-Host "Publicado: https://github.com/FelipeStv0/ubs-marilia-rag-assistant_n8n_automation" -ForegroundColor Green
