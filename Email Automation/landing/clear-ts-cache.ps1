# Clear TypeScript cache and verify setup
Write-Host "Clearing TypeScript cache..." -ForegroundColor Yellow

# Remove TypeScript build info files
Get-ChildItem -Path . -Filter "tsconfig.tsbuildinfo" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path . -Filter ".tsbuildinfo" -Recurse -ErrorAction SilentlyContinue | Remove-Item -Force -ErrorAction SilentlyContinue

# Verify app directory is removed
if (Test-Path "app") {
    Write-Host "WARNING: app directory still exists!" -ForegroundColor Red
    Remove-Item -Path "app" -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Removed app directory" -ForegroundColor Green
} else {
    Write-Host "✓ app directory does not exist" -ForegroundColor Green
}

# Verify Next.js is not in package.json
$packageJson = Get-Content "package.json" -Raw | ConvertFrom-Json
if ($packageJson.dependencies.next) {
    Write-Host "WARNING: Next.js found in dependencies!" -ForegroundColor Red
} else {
    Write-Host "✓ Next.js not in package.json" -ForegroundColor Green
}

# Verify tsconfig.json excludes app
$tsconfig = Get-Content "tsconfig.json" -Raw | ConvertFrom-Json
if ($tsconfig.exclude -contains "app") {
    Write-Host "✓ tsconfig.json excludes app directory" -ForegroundColor Green
} else {
    Write-Host "WARNING: tsconfig.json does not exclude app" -ForegroundColor Yellow
}

Write-Host "`nDone! Please restart TypeScript server in your IDE." -ForegroundColor Cyan
Write-Host "Press Ctrl+Shift+P and type: TypeScript: Restart TS Server" -ForegroundColor Cyan
