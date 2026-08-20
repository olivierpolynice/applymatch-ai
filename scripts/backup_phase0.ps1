param(
    [string]$ProjectRoot = (Split-Path -Parent $PSScriptRoot),
    [string]$BackupRoot = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = (Resolve-Path $ProjectRoot).Path

if (-not $BackupRoot) {
    $BackupRoot = Join-Path (Split-Path -Parent $ProjectRoot) "applymatch-ai-backups"
}

$timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$destination = Join-Path $BackupRoot "applymatch-ai-$timestamp"
$sourceStaging = Join-Path $env:TEMP "applymatch-source-$timestamp"

New-Item -ItemType Directory -Path $destination -Force | Out-Null

Write-Host "1/4 - Sauvegarde Git"
if (-not (Test-Path (Join-Path $ProjectRoot ".git"))) {
    throw "Le dossier $ProjectRoot n'est pas un depot Git."
}

git -C $ProjectRoot status --short | Out-File (Join-Path $destination "git-status.txt") -Encoding utf8
git -C $ProjectRoot rev-parse HEAD | Out-File (Join-Path $destination "git-commit.txt") -Encoding ascii
git -C $ProjectRoot log -1 --oneline | Out-File (Join-Path $destination "git-last-commit.txt") -Encoding utf8
git -C $ProjectRoot diff --binary | Out-File (Join-Path $destination "working-tree.patch") -Encoding utf8
git -C $ProjectRoot diff --cached --binary | Out-File (Join-Path $destination "staged.patch") -Encoding utf8
git -C $ProjectRoot bundle create (Join-Path $destination "repository.bundle") --all

Write-Host "2/4 - Copie du code sans secrets"
New-Item -ItemType Directory -Path $sourceStaging -Force | Out-Null

$null = robocopy $ProjectRoot $sourceStaging /E `
    /XD .git .venv venv node_modules .next dist coverage __pycache__ uploads data `
    /XF .env "*.db" "*.sqlite" "*.sqlite3" "*.log" "*.pdf"

if ($LASTEXITCODE -ge 8) {
    throw "Robocopy a echoue avec le code $LASTEXITCODE."
}

Compress-Archive `
    -Path (Join-Path $sourceStaging "*") `
    -DestinationPath (Join-Path $destination "source-code.zip") `
    -CompressionLevel Optimal

Remove-Item -Path $sourceStaging -Recurse -Force

Write-Host "3/4 - Sauvegarde de la configuration"
$envExample = Join-Path $ProjectRoot ".env.example"
if (Test-Path $envExample) {
    Copy-Item $envExample (Join-Path $destination ".env.example")
}

$envFile = Join-Path $ProjectRoot ".env"
$databaseUrl = "sqlite+pysqlite:///./applymatch.db"

if (Test-Path $envFile) {
    $databaseLine = Get-Content $envFile |
        Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } |
        Select-Object -First 1

    if ($databaseLine) {
        $databaseUrl = ($databaseLine -split '=', 2)[1].Trim().Trim('"').Trim("'")
    }

    Get-Content $envFile |
        Where-Object { $_ -match '^\s*[A-Za-z_][A-Za-z0-9_]*\s*=' } |
        ForEach-Object { ($_ -split '=', 2)[0].Trim() + "=" } |
        Out-File (Join-Path $destination "env-keys-only.txt") -Encoding utf8
}

Write-Host "4/4 - Sauvegarde de la base"
$databaseBackupCreated = $false

if ($databaseUrl -match '^sqlite(?:\+pysqlite)?:///(.+)$') {
    $sqlitePath = $Matches[1]
    if (-not [System.IO.Path]::IsPathRooted($sqlitePath)) {
        $sqlitePath = Join-Path $ProjectRoot $sqlitePath.TrimStart('.', '/', '\')
    }

    if (Test-Path $sqlitePath) {
        Copy-Item $sqlitePath (Join-Path $destination "applymatch.db")
        $databaseBackupCreated = $true
    } else {
        Write-Warning "Base SQLite introuvable : $sqlitePath"
    }
} elseif ($databaseUrl -match '^postgresql') {
    if (Get-Command pg_dump -ErrorAction SilentlyContinue) {
        $databaseDump = Join-Path $destination "applymatch.dump"
        & pg_dump --dbname=$databaseUrl --format=custom --file=$databaseDump
        if ($LASTEXITCODE -ne 0) {
            throw "pg_dump a echoue avec le code $LASTEXITCODE."
        }
        $databaseBackupCreated = $true
    } else {
        Write-Warning "pg_dump est absent. Installe PostgreSQL Client Tools puis relance ce script."
    }
} else {
    Write-Warning "Type de base non reconnu."
}

$manifest = @(
    "Sauvegarde : $timestamp"
    "Projet : $ProjectRoot"
    "Commit : $(Get-Content (Join-Path $destination 'git-commit.txt'))"
    "Base sauvegardee : $databaseBackupCreated"
    "Secrets .env inclus : False"
)
$manifest | Out-File (Join-Path $destination "MANIFEST.txt") -Encoding utf8

Write-Host ""
Write-Host "Sauvegarde creee dans : $destination" -ForegroundColor Green

if (-not $databaseBackupCreated) {
    Write-Warning "Le code est sauvegarde, mais pas la base. Ne commence pas la phase 1 avant de corriger ce point."
    exit 2
}

Write-Host "Phase 0 validee : code, Git et base sauvegardes." -ForegroundColor Green
