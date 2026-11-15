$py = 'c:\Users\admin\dilkush007\.venv\Scripts\python.exe'
$root = 'c:\Users\admin\dilkush007'
$rep = @()

# 1) py_compile the two patched files
& $py -m py_compile "$root\wallix-code\smart_pinterest_agent.py" "$root\wallix-code\tests\test_agent_pipeline.py" 2>&1 |
    ForEach-Object { $rep += "PYCOMPILE-OUT: $_" }
$rep += "PYCOMPILE_EXIT=$LASTEXITCODE"

# 2) focused resolver tests only
Push-Location "$root\wallix-code"
& $py -m pytest 'tests\test_agent_pipeline.py::TestPinMediaResolver' -v 2>&1 |
    ForEach-Object { $rep += $_ }
$focusExit = $LASTEXITCODE
Pop-Location
$rep += "FOCUSED_PYTEST_EXIT=$focusExit"

Set-Content -Path "$root\_focused_tests.txt" -Value $rep -Encoding UTF8
Write-Host "FOCUSED_DONE exit=$focusExit"
