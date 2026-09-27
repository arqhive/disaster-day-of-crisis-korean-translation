# 파일 단위 한글 패처 (disc-file-patcher 스킬 템플릿, 게임 정보는 data/config.txt)
# 원본 이미지를 풀어 바뀐 게임 파일만 차분 적용한 뒤 다시 묶는다.
# 정본 ISO, WBFS, WBFS에서 변환한 ISO 등 덤프 형태가 달라도 게임 파일만 같으면 적용된다.
# 사용: 패치하기.bat 에 이미지를 끌어다 놓거나, 이 폴더에 이미지를 두고 실행
#       powershell -File patch.ps1 [원본 이미지] [결과 파일(.iso 또는 .wbfs)]
param([string]$Src, [string]$Out)

$ErrorActionPreference = 'Stop'
$env:LANG = 'en_US.UTF-8'   # 없으면 cygwin wit 이 한글 경로를 열지 못함
[Console]::OutputEncoding = [Text.Encoding]::UTF8
$here = $PSScriptRoot
$wit = Join-Path $here 'bin\wit.exe'
$xd = Join-Path $here 'bin\xdelta3.exe'
$data = Join-Path $here 'data'
$work = Join-Path $here '_work'
$tmpA = Join-Path $here '_tmp_a'
$tmpB = Join-Path $here '_tmp_b'
$cfg = @{}
foreach ($l in Get-Content -LiteralPath (Join-Path $data 'config.txt') -Encoding UTF8) {
    if ($l -match '^(\w+)=(.*)$') { $cfg[$Matches[1]] = $Matches[2] }
}

function Fail($msg) { Write-Host ''; Write-Host "[오류] $msg" -ForegroundColor Red; Cleanup; exit 1 }
function Cleanup {
    foreach ($p in $work, $tmpA, $tmpB) {
        if (Test-Path -LiteralPath $p) { Remove-Item -LiteralPath $p -Recurse -Force }
    }
}
function Md5($path) { (Get-FileHash -LiteralPath $path -Algorithm MD5).Hash.ToLower() }
function Run($exe, [string[]]$argv) {
    & $exe @argv
    if ($LASTEXITCODE -ne 0) { Fail "$([IO.Path]::GetFileName($exe)) 실행 실패 (코드 $LASTEXITCODE)" }
}

Write-Host "$($cfg.title) 한글 패처"
Write-Host '================================'

# 1. 원본 이미지 고르기
if (-not $Src) {
    $cand = @(Get-ChildItem -LiteralPath $here -File | Where-Object { $_.Extension -match '^\.(iso|wbfs|ciso|wia|wdf)$' -and $_.Name -notmatch '\(Korean\)' -and $_.BaseName -ne $cfg.result })
    if ($cand.Count -eq 1) { $Src = $cand[0].FullName }
    else {
        if ($cand.Count -gt 1) { Write-Host '이 폴더에 이미지가 여러 개 있습니다.' }
        $Src = (Read-Host '원본 이미지 경로를 입력하세요(파일을 이 창에 끌어다 놓아도 됩니다)').Trim('"', ' ')
    }
}
if (-not (Test-Path -LiteralPath $Src -PathType Leaf)) { Fail "파일이 없습니다: $Src" }
$Src = (Resolve-Path -LiteralPath $Src).Path
if ([IO.Path]::GetExtension($Src) -eq '.rvz') { Fail 'RVZ는 지원하지 않습니다. Dolphin에서 ISO로 변환한 뒤 다시 실행하세요.' }
if (-not $Out) {
    $ext = if ([IO.Path]::GetExtension($Src) -eq '.wbfs') { '.wbfs' } else { '.iso' }
    $Out = Join-Path ([IO.Path]::GetDirectoryName($Src)) "$($cfg.result)$ext"
}
$fmt = if ([IO.Path]::GetExtension($Out) -eq '.wbfs') { '--wbfs' } else { '--iso' }
Write-Host "원본: $Src"
Write-Host "결과: $Out"

# 2. 게임 확인
$id = (& $wit id6 $Src | Select-Object -First 1)
if ($id -ne $cfg.id) { Fail "$($cfg.title)($($cfg.id))가 아닙니다. 읽은 게임 ID: $id" }

# 3. 풀기
Cleanup
Write-Host ''
Write-Host '[1/3] 이미지 푸는 중... (몇 분 걸립니다)'
Run $wit @('extract', $Src, $work, '--psel', 'data', '--pmode', 'none', '-o', '-q')

# 4. 파일별 차분 적용
Write-Host '[2/3] 한글 패치 적용 중...'
$lines = Get-Content -LiteralPath (Join-Path $data 'manifest.txt') -Encoding UTF8 | Where-Object { $_ }
$i = 0
foreach ($line in $lines) {
    $mode, $patch, $rel, $srcMd5, $dstMd5 = $line -split "`t"
    $i++
    Write-Progress -Activity '한글 패치 적용' -Status $rel -PercentComplete ($i * 100 / $lines.Count)
    $file = Join-Path $work ($rel -replace '/', '\')
    if (-not (Test-Path -LiteralPath $file)) { Fail "게임 파일이 없습니다: $rel" }
    if ((Md5 $file) -ne $srcMd5) { Fail "원본 게임 파일이 다릅니다: $rel`n  $($cfg.id) 원본인지, 이미 패치한 이미지가 아닌지 확인하세요." }
    if ($mode -eq 'gz') {
        $in = [IO.File]::OpenRead($file); $o = [IO.File]::Create($tmpA)
        $gz = New-Object IO.Compression.GZipStream($in, [IO.Compression.CompressionMode]::Decompress)
        $gz.CopyTo($o); $gz.Close(); $o.Close()
        Run $xd @('-d', '-f', '-s', $tmpA, (Join-Path $data $patch), $tmpB)
        if ((Md5 $tmpB) -ne $dstMd5) { Fail "패치 결과가 다릅니다: $rel" }
        $in = [IO.File]::OpenRead($tmpB); $o = [IO.File]::Create($file)
        $gz = New-Object IO.Compression.GZipStream($o, [IO.Compression.CompressionLevel]::Optimal)
        $in.CopyTo($gz); $gz.Close(); $in.Close()
    } else {
        Run $xd @('-d', '-f', '-s', $file, (Join-Path $data $patch), $tmpB)
        if ((Md5 $tmpB) -ne $dstMd5) { Fail "패치 결과가 다릅니다: $rel" }
        Move-Item -LiteralPath $tmpB -Destination $file -Force
    }
}
Write-Progress -Activity '한글 패치 적용' -Completed
Write-Host "  파일 $($lines.Count)개 적용"

# 5. 다시 묶기
Write-Host '[3/3] 이미지 만드는 중... (몇 분 걸립니다)'
if (Test-Path -LiteralPath $Out) { Remove-Item -LiteralPath $Out -Force }
Run $wit @('copy', $work, $Out, $fmt, '-q')
Cleanup
Write-Host ''
Write-Host "완료: $Out" -ForegroundColor Green
