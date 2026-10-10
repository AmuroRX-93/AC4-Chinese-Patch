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
$Base='https://github.com/AmuroRX-93/AC4-Chinese-Patch/releases/download/v2026.10.10-delta.5-platforms.1/'
$Archive='AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip'
$Expected='650c095b17bd83354640ee115a22e93b8fe291a70911f82ba14c56b72b018a43'
$Parts=ConvertFrom-Json @'
[{"file":"AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part001","bytes":33554432,"sha256":"bcd844dd91bf25b7d8a4f00184897e466c96b58240727da162f8bace2f2b84bf"},{"file":"AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part002","bytes":33554432,"sha256":"8f1588e53a6e8fc5110e47a42684d3a8631a7aebb4a664a0058ded2f3c14277b"},{"file":"AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part003","bytes":33554432,"sha256":"4942c596eef1a0d42e3f45aace51372fd625c07ad2bb0544ec7214dfc9c50cee"},{"file":"AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part004","bytes":33554432,"sha256":"26ae37b06dc37d68e67eb5ec7ee4270400949119e67441e291d732924d94afb9"},{"file":"AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part005","bytes":33554432,"sha256":"5e4df92a8f2a9cca53a42b4929d00890dff9e295e64f19b4b1cb6e6bff9d793f"},{"file":"AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part006","bytes":33554432,"sha256":"10d6ae65958bfdf813ebaa6033b62c98507079328c9e9822af92ce254179cefd"},{"file":"AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part007","bytes":33554432,"sha256":"ceb9a3be78afde5bddcad68a9ade845d74f2a6125bf0eae94e7b5b09316c8546"},{"file":"AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012.zip.part008","bytes":25713974,"sha256":"ff1010f233f6422f88a8b02b7709a496daa48da089fb440d1112a900f131f907"}]
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
$Destination=Join-Path $Root 'AC4_delta5_20261010_extracted'
if (Test-Path -LiteralPath $Destination) { throw ('Extraction directory already exists. Keep it or rename it before retrying: '+$Destination) }
Expand-Archive -LiteralPath $Zip -DestinationPath $Destination
Write-Host ('Complete: '+(Join-Path $Destination 'AC4_CN_FullPatch_20261010_delta5_ThreePlatforms_BLJM60012'))
Write-Host 'Run the installation entry inside the extracted folder. Python is included.'
