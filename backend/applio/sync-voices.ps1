$source = "C:\work\projects\2025-voice-assistent\backend\applio\voices"
$target = "C:\work\projects\2025-voice-assistent\backend\applio\logs"

if (!(Test-Path $target)) {
    New-Item $target -ItemType Directory | Out-Null
}

Get-ChildItem $source -Directory | ForEach-Object {
    $voiceName = $_.Name
    $targetDir = Join-Path $target $voiceName
    
    if (!(Test-Path $targetDir)) {
        New-Item $targetDir -ItemType Directory | Out-Null
    }
    
    Get-ChildItem $_.FullName -Filter *.pth | ForEach-Object {
        $dest = Join-Path $targetDir $_.Name
        if (!(Test-Path $dest)) {
            Copy-Item $_.FullName $dest
        }
    }
    
    Get-ChildItem $_.FullName -Filter *.index | ForEach-Object {
        $dest = Join-Path $targetDir $_.Name
        if (!(Test-Path $dest)) {
            Copy-Item $_.FullName $dest
        }
    }
}

Write-Host "Voices synced successfully." -ForegroundColor Green
