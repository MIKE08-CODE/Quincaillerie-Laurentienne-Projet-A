<#
.SYNOPSIS
  Paquet de distribution de l'application de bureau (cahier §6.3) : exécutable Windows autonome,
  appsettings.json pointant vers l'API publique, archive ZIP et empreinte SHA-256.

.EXAMPLE
  ./desktop/scripts/package.ps1 -ApiUrl https://quincaillerie-laurentienne-api.onrender.com/api/v1 -Version v0.1.0

  Produit, à la racine du dépôt : QuincaillerieLaurentienne-Bureau-v0.1.0-win-x64.zip et son .sha256.
  N'efface rien hors du dossier de publication qu'il crée lui-même (publish-bureau/).
#>
param(
  [string]$Project = "desktop/src/QuincaillerieLaurentienne.Desktop/QuincaillerieLaurentienne.Desktop.csproj",
  [Parameter(Mandatory = $true)][string]$ApiUrl,
  [Parameter(Mandatory = $true)][ValidatePattern('^[A-Za-z0-9._-]+$')][string]$Version
)
$ErrorActionPreference = "Stop"

if ($ApiUrl -notmatch '^https://') { throw "L'URL de l'API distribuée doit être en https : $ApiUrl" }

$out = "publish-bureau"
if (Test-Path $out) { throw "Le dossier $out existe déjà : le supprimer ou le renommer avant de relancer." }

dotnet publish $Project -c Release -r win-x64 --self-contained true `
  -p:PublishSingleFile=true -p:IncludeNativeLibrariesForSelfExtract=true -o $out
if ($LASTEXITCODE -ne 0) { throw "Échec de dotnet publish." }

# URL de l'API publique dans le paquet seulement (le dépôt garde l'adresse locale de développement).
$settingsPath = Join-Path $out "appsettings.json"
$settings = Get-Content $settingsPath -Raw | ConvertFrom-Json
$settings.Api.BaseUrl = $ApiUrl
$settings | ConvertTo-Json -Depth 5 | Set-Content $settingsPath -Encoding utf8
Get-ChildItem $out -Filter *.pdb | Remove-Item  # symboles de débogage : non distribués

$archive = "QuincaillerieLaurentienne-Bureau-$Version-win-x64.zip"
Compress-Archive -Path "$out/*" -DestinationPath $archive
$hash = (Get-FileHash $archive -Algorithm SHA256).Hash.ToLower()
"$hash  $archive" | Set-Content "$archive.sha256" -Encoding ascii

$size = [math]::Round((Get-Item $archive).Length / 1MB, 1)
Write-Output "Archive : $archive ($size Mo) ; SHA-256 : $hash"
Write-Output "Contenu : $((Get-ChildItem $out).Name -join ', ')"
Write-Output "API configurée : $((Get-Content $settingsPath -Raw | ConvertFrom-Json).Api.BaseUrl)"
if ($env:GITHUB_OUTPUT) { "archive=$archive" | Add-Content $env:GITHUB_OUTPUT }
if ($env:GITHUB_STEP_SUMMARY) { "Archive : $archive ($size Mo), SHA-256 ``$hash``" | Add-Content $env:GITHUB_STEP_SUMMARY }
