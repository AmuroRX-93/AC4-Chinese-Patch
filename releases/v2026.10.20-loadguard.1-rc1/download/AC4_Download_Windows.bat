@echo off
setlocal DisableDelayedExpansion
set "AC4_BOOTSTRAP=%~f0"
powershell.exe -NoProfile -Command "$ac4Text=Get-Content -LiteralPath $env:AC4_BOOTSTRAP -Raw -Encoding UTF8; $ac4Match=[regex]::Match($ac4Text,'(?ms)^# AC4_POWERSHELL_PAYLOAD\r?\n(.*)\z'); if(-not $ac4Match.Success){throw 'Bootstrap payload missing'}; & ([scriptblock]::Create($ac4Match.Groups[1].Value))"
set "AC4_RESULT=%ERRORLEVEL%"
pause
exit /b %AC4_RESULT%
# AC4_POWERSHELL_PAYLOAD
$ErrorActionPreference='Stop'
$Root=[IO.Path]::GetDirectoryName($env:AC4_BOOTSTRAP)
$Base='https://github.com/AmuroRX-93/AC4-Chinese-Patch/releases/download/v2026.10.20-loadguard.1-rc1/'
$Archive='AC4_delta5_LoadGuard_Normal_20261020_rc1.zip'
$Expected='2aedb74015f7d39ef766ca85ca9648bebae86231e26d5924bb61bacc08c7977d'
$Parts=ConvertFrom-Json @'
[{"file":"AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part001","bytes":33554432,"sha256":"09b7be3ae306f01726176f75ee9f453c471aee1941fc8be303cb082bda67e94e"},{"file":"AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part002","bytes":33554432,"sha256":"c4091d004c845ff7e0003cf15c6972560b5b2cafc6c5fe7afe258fc92da2c06e"},{"file":"AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part003","bytes":33554432,"sha256":"e0ba84423a9d0c2cf2f2c3da1c9eff6f8fd37802b31e76104ca3e08117836443"},{"file":"AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part004","bytes":33554432,"sha256":"d686d1fc4bddb368c0bdc0366732e6158a6835c49d1857325f69fbc4aba0d3c1"},{"file":"AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part005","bytes":33554432,"sha256":"b401df9d1144c1204acfbbc9d53c4a91577d0ac8c468777ec6404bd672550401"},{"file":"AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part006","bytes":33554432,"sha256":"ada1e043fb5ba057eefb9833137c40a2d02447d338ac0535fbd1337a0d443362"},{"file":"AC4_delta5_LoadGuard_Normal_20261020_rc1.zip.part007","bytes":27575091,"sha256":"11931f6ce00dd52d777ea31f2cb872111bc50994b3b22f9a4516685ae7c06502"}]
'@
function Hash-File($Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
$Zip=Join-Path $Root $Archive
if ((Test-Path -LiteralPath $Zip) -and ((Hash-File $Zip) -eq $Expected)) {
 Write-Host 'Archive already verified.'
} else {
 foreach ($Part in $Parts) {
  $Path=Join-Path $Root $Part.file
  if ((Test-Path -LiteralPath $Path) -and ((Hash-File $Path) -eq $Part.sha256)) { Write-Host ('Verified: '+$Part.file); continue }
  Write-Host ('Downloading: '+$Part.file)
  Invoke-WebRequest -UseBasicParsing -Uri ($Base+$Part.file) -OutFile ($Path+'.download') -TimeoutSec 1200
  if ((Hash-File ($Path+'.download')) -ne $Part.sha256) { throw ('Checksum failed: '+$Part.file) }
  if (Test-Path -LiteralPath $Path) { Move-Item -LiteralPath $Path -Destination ($Path+'.invalid.'+(Get-Date -Format yyyyMMddHHmmss)) }
  Move-Item -LiteralPath ($Path+'.download') -Destination $Path
 }
 $Building=$Zip+'.assembling'
 $Ac4OutputStream=[IO.File]::Create($Building)
 try {
  foreach ($Part in $Parts) {
   $Ac4SourceStream=[IO.File]::OpenRead((Join-Path $Root $Part.file))
   try { $Ac4SourceStream.CopyTo($Ac4OutputStream) } finally { $Ac4SourceStream.Dispose() }
  }
 } finally { $Ac4OutputStream.Dispose() }
 if ((Hash-File $Building) -ne $Expected) { throw 'Combined archive checksum failed' }
 if (Test-Path -LiteralPath $Zip) { Move-Item -LiteralPath $Zip -Destination ($Zip+'.old.'+(Get-Date -Format yyyyMMddHHmmss)) }
 Move-Item -LiteralPath $Building -Destination $Zip
}
$Destination=Join-Path $Root 'AC4_loadguard_20261020_rc1_extracted'
if (Test-Path -LiteralPath $Destination) { throw ('Extraction directory already exists. Keep it or rename it before retrying: '+$Destination) }
Expand-Archive -LiteralPath $Zip -DestinationPath $Destination
Write-Host ('Complete: '+(Join-Path $Destination 'AC4_delta5_LoadGuard_Normal_20261020_rc1'))
Write-Host 'Run the installation entry inside the extracted folder. Python is included.'
