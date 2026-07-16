param(
  [string]$Version = "1.0.1"
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$releaseRoot = Join-Path $root "release-assets"
$stageRoot = Join-Path $releaseRoot "staging"

if (Test-Path $releaseRoot) {
  Remove-Item -LiteralPath $releaseRoot -Recurse -Force
}

New-Item -ItemType Directory -Path $releaseRoot | Out-Null
New-Item -ItemType Directory -Path $stageRoot | Out-Null

Push-Location $root
try {
  python scripts/generate_openapi.py
  python scripts/build_docs_site.py
  npm --prefix desktop run build
  npm --prefix js-sdk run build

  $pythonDist = Join-Path $releaseRoot "python-dist"
  New-Item -ItemType Directory -Path $pythonDist | Out-Null
  Push-Location (Join-Path $root "sdk")
  try {
    python setup.py sdist bdist_wheel --dist-dir $pythonDist
  }
  finally {
    Pop-Location
  }
  Compress-Archive -Path (Join-Path $pythonDist "*") -DestinationPath (Join-Path $releaseRoot "aquastat-python-sdk-$Version.zip")

  Copy-Item openapi\openapi.json -Destination (Join-Path $releaseRoot "openapi.json")
  Copy-Item openapi\openapi.yaml -Destination (Join-Path $releaseRoot "openapi.yaml")

  Copy-Item desktop\index.html -Destination (Join-Path $stageRoot "desktop-index.html")
  Copy-Item -Recurse desktop\dist -Destination (Join-Path $stageRoot "desktop")
  Copy-Item -Recurse docs\assets -Destination (Join-Path $stageRoot "desktop-assets")
  Compress-Archive -Path (Join-Path $stageRoot "desktop"), (Join-Path $stageRoot "desktop-index.html"), (Join-Path $stageRoot "desktop-assets") -DestinationPath (Join-Path $releaseRoot "aquastat-desktop-$Version.zip")

  Copy-Item -Recurse js-sdk\dist -Destination (Join-Path $stageRoot "js-sdk")
  Copy-Item js-sdk\package.json -Destination (Join-Path $stageRoot "js-sdk-package.json")
  Compress-Archive -Path (Join-Path $stageRoot "js-sdk"), (Join-Path $stageRoot "js-sdk-package.json") -DestinationPath (Join-Path $releaseRoot "aquastat-js-sdk-$Version.zip")

  Copy-Item -Recurse site -Destination (Join-Path $stageRoot "site")
  Compress-Archive -Path (Join-Path $stageRoot "site") -DestinationPath (Join-Path $releaseRoot "aquastat-docs-site-$Version.zip")

  Copy-Item openapi\openapi.json -Destination (Join-Path $stageRoot "openapi.json")
  Copy-Item openapi\openapi.yaml -Destination (Join-Path $stageRoot "openapi.yaml")
  Compress-Archive -Path (Join-Path $stageRoot "openapi.json"), (Join-Path $stageRoot "openapi.yaml") -DestinationPath (Join-Path $releaseRoot "aquastat-openapi-$Version.zip")

  $sourceArchive = Join-Path $releaseRoot "aquastat-source-$Version.zip"
  git archive --format=zip --output=$sourceArchive HEAD
}
finally {
  Pop-Location
}
