[CmdletBinding()]
param(
    [string]$OutputDirectory
)

$ErrorActionPreference = "Stop"

$projectRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot "..")).Path
$componentRoot = Join-Path $projectRoot "custom_components\ecoflow_powerpulse2"
$manifestPath = Join-Path $componentRoot "manifest.json"

if (-not (Test-Path -LiteralPath $manifestPath -PathType Leaf)) {
    throw "Integration manifest not found: $manifestPath"
}

$manifest = Get-Content -Raw -LiteralPath $manifestPath | ConvertFrom-Json
if (-not $manifest.version) {
    throw "Integration manifest has no version"
}

if (-not $OutputDirectory) {
    $OutputDirectory = Join-Path $projectRoot "dist"
}
elseif (-not [System.IO.Path]::IsPathRooted($OutputDirectory)) {
    $OutputDirectory = Join-Path $projectRoot $OutputDirectory
}

$outputRoot = [System.IO.Path]::GetFullPath($OutputDirectory)
[System.IO.Directory]::CreateDirectory($outputRoot) | Out-Null

$archiveName = "ecoflow_powerpulse2-v$($manifest.version).zip"
$archivePath = Join-Path $outputRoot $archiveName

# This path is derived exclusively from the fixed integration name and the
# manifest version. Rebuilding may safely replace that generated artifact.
if (Test-Path -LiteralPath $archivePath -PathType Leaf) {
    Remove-Item -LiteralPath $archivePath -Force
}

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open(
    $archivePath,
    [System.IO.Compression.ZipArchiveMode]::Create
)

try {
    $files = Get-ChildItem -LiteralPath $componentRoot -Recurse -File |
        Where-Object {
            $_.Extension -notin ".pyc", ".pyo" -and
            $_.FullName -notmatch "[\\/]__pycache__[\\/]"
        }

    foreach ($file in $files) {
        $entryName = [System.IO.Path]::GetRelativePath(
            $projectRoot,
            $file.FullName
        ).Replace("\", "/")
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile(
            $archive,
            $file.FullName,
            $entryName,
            [System.IO.Compression.CompressionLevel]::Optimal
        ) | Out-Null
    }
}
finally {
    $archive.Dispose()
}

$hash = Get-FileHash -LiteralPath $archivePath -Algorithm SHA256
[PSCustomObject]@{
    Path = $archivePath
    Version = [string]$manifest.version
    Bytes = (Get-Item -LiteralPath $archivePath).Length
    SHA256 = $hash.Hash
}
