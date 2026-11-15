$out = @()
$out += '=== STATUS wallix-code full ==='
$out += (git -C wallix-code status --short 2>&1 | Out-String)
$out += '=== tracked? smart_pinterest_agent.py ==='
$out += (git -C wallix-code ls-files --error-unmatch smart_pinterest_agent.py 2>&1 | Out-String)
$out += '=== tracked? tests ==='
$out += (git -C wallix-code ls-files tests 2>&1 | Out-String)
$out += '=== tests dir listing ==='
$out += (Get-ChildItem 'wallix-code\tests' -File -ErrorAction SilentlyContinue |
    ForEach-Object { $_.Name + ' | ' + $_.Length + ' | ' + $_.LastWriteTime } | Out-String)
$out += '=== grep resolver/media in tests ==='
$hits = Get-ChildItem 'wallix-code\tests' -Filter '*.py' -File -ErrorAction SilentlyContinue |
    Select-String -Pattern 'resolver|resolve_pin|media_url|media url|persistent' -ErrorAction SilentlyContinue
foreach ($h in $hits) { $out += ($h.Filename + ':' + $h.LineNumber + ': ' + $h.Line.Trim()) }
$out += '=== grep resolver/media in wallix-code root py ==='
$hits2 = Get-ChildItem 'wallix-code' -Filter '*.py' -File -ErrorAction SilentlyContinue |
    Select-String -Pattern 'def test_|resolve_pin_media_with_browser|authenticated' -ErrorAction SilentlyContinue
foreach ($h in $hits2) { $out += ($h.Filename + ':' + $h.LineNumber + ': ' + $h.Line.Trim()) }
Set-Content -Path 'c:\Users\admin\dilkush007\_git2.txt' -Value $out -Encoding UTF8
Write-Host GIT2_DONE
