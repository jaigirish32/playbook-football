# deploy.ps1 - Deploy Playbook Football to Azure
# Usage:
#   .\deploy.ps1                    # deploy all (frontend + backend + db)
#   .\deploy.ps1 -target frontend   # frontend only
#   .\deploy.ps1 -target backend    # backend only
#   .\deploy.ps1 -target db         # database only
#   .\deploy.ps1 -target frontend,backend  # frontend + backend only

param([string]$target = "all")

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

$BACKEND_URL  = "https://playbook-backend.greencoast-08c84278.eastus.azurecontainerapps.io"
$ACR          = "playbookfootballacr.azurecr.io"
$ACR_NAME     = "playbookfootballacr"
$APP_NAME     = "playbook-backend"
$RG           = "playbook-football-rg"
$STATIC_APP   = "playbook-football-web"
$DB_DUMP_PATH = "C:\mywork\playbook.sql"
$ADMIN_EMAIL  = "admin@playbook.com"
$ADMIN_PASS   = "admin123"

# ── Frontend ──────────────────────────────────────────────────
if ($target -eq "all" -or $target -eq "frontend") {
    Write-Host "`n Deploying Frontend ────────────────────────────────" -ForegroundColor Cyan
    Set-Location "$root\frontend"
    npm run build
    $deployToken = az staticwebapp secrets list --name $STATIC_APP --resource-group $RG --query "properties.apiKey" -o tsv
    npx @azure/static-web-apps-cli deploy ./dist --deployment-token $deployToken --env production
    Set-Location $root
    Write-Host "Ok Frontend deployed" -ForegroundColor Green
}

# ── Backend ───────────────────────────────────────────────────
if ($target -eq "all" -or $target -eq "backend") {
    Write-Host "`n Deploying Backend ─────────────────────────────────" -ForegroundColor Cyan
    Set-Location "$root\backend"
    $v = "v$(Get-Date -Format 'yyyyMMddHHmm')"
    Write-Host "  Building image: $ACR/${APP_NAME}:$v"
    az acr login --name $ACR_NAME
    docker build -t "$ACR/${APP_NAME}:$v" .
    docker push "$ACR/${APP_NAME}:$v"
    az containerapp update --name $APP_NAME --resource-group $RG --image "$ACR/${APP_NAME}:$v"
    Set-Location $root
    Write-Host "Ok Backend deployed: $v" -ForegroundColor Green
}

# ── Database ──────────────────────────────────────────────────
if ($target -eq "all" -or $target -eq "db") {
    Write-Host "`n Syncing Database to Azure ─────────────────────────" -ForegroundColor Cyan

    # Dump local DB
    Write-Host "  Dumping local database..."
    docker exec playbook_db pg_dump -U playbook_user -d playbook --no-owner --no-privileges -Fp -f /tmp/playbook.sql
    docker cp playbook_db:/tmp/playbook.sql $DB_DUMP_PATH
    $sizeMB = [math]::Round((Get-Item $DB_DUMP_PATH).Length / 1MB, 2)
    Write-Host "  Dump size: $sizeMB MB"

    # Upload and restore via backend API
    Write-Host "  Uploading to Azure..."
    Add-Type -AssemblyName System.Net.Http
    $client  = New-Object System.Net.Http.HttpClient
    $content = New-Object System.Net.Http.MultipartFormDataContent
    $fileStream  = [System.IO.File]::OpenRead($DB_DUMP_PATH)
    $fileContent = New-Object System.Net.Http.StreamContent($fileStream)
    $content.Add($fileContent, "file", "playbook.sql")

    $response = $client.PostAsync("$BACKEND_URL/api/admin/restore-db", $content).Result
    $result   = $response.Content.ReadAsStringAsync().Result
    $fileStream.Close()

    if ($response.StatusCode -eq "OK") {
        Write-Host "Ok Database synced to Azure" -ForegroundColor Green
    } else {
        Write-Host "Fail Database sync failed: $result" -ForegroundColor Red
    }
}

Write-Host "Ok Deployment complete!" -ForegroundColor Green
