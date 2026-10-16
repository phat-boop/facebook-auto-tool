"""Exercise release helpers only, never the publish/commit section of the script."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[2]
SHELLS = [Path(os.environ.get("WINDIR", "C:/Windows")) / "System32/WindowsPowerShell/v1.0/powershell.exe"]
pwsh = shutil.which("pwsh")
if not pwsh:
    bundled = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/native/powershell/pwsh.exe"
    pwsh = str(bundled) if bundled.exists() else None
if pwsh:
    SHELLS.append(Path(pwsh))
SHELLS = [path for path in SHELLS if path.exists()]


def ps_string(value):
    return "'" + str(value).replace("'", "''") + "'"


def run_helpers(shell, body):
    # AST extraction defines functions but never evaluates top-level release code.
    script = r"""
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$tokens = $null
$parseErrors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(SCRIPT_PATH, [ref]$tokens, [ref]$parseErrors)
if ($parseErrors.Count) { throw ($parseErrors | Out-String) }
$definitions = $ast.FindAll({ param($node) $node -is [System.Management.Automation.Language.FunctionDefinitionAst] }, $true)
foreach ($definition in $definitions) { Invoke-Expression $definition.Extent.Text }
""".replace("SCRIPT_PATH", ps_string(ROOT / "release.ps1")) + body
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    result = subprocess.run([str(shell), "-NoProfile", "-NonInteractive", "-EncodedCommand", encoded],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    for line in reversed(result.stdout.splitlines()):
        if line.startswith("RESULT:"):
            return json.loads(line[len("RESULT:"):])
    raise AssertionError(result.stdout + result.stderr)


@pytest.mark.parametrize("shell", SHELLS, ids=lambda path: path.name)
def test_release_parser_and_native_stderr_use_exit_code(shell):
    body = "\n$r=Invoke-NativeCapture " + ps_string(sys.executable) + " @('-c', 'import sys; sys.stderr.write(str(123)); sys.exit(0)')\n"
    body += "'RESULT:' + (@{ExitCode=$r.ExitCode; Count=@($r.Output).Count} | ConvertTo-Json -Compress)"
    assert run_helpers(shell, body) == {"ExitCode": 0, "Count": 1}


@pytest.mark.parametrize("shell", SHELLS, ids=lambda path: path.name)
@pytest.mark.parametrize("count,summary,exit_code,expected", [
    (87, "87 passed, 2 skipped", 0, True),
    (100, "100 passed, 1 warning", 0, True),
    (1, "1 failed", 1, False),
    (0, "no tests ran", 5, False),
    (0, "collection/import error", 2, False),
])
def test_release_gate_is_dynamic_and_never_ignores_runner_failure(shell, count, summary, exit_code, expected):
    body = "\nfunction Invoke-NativeCapture { param($FilePath,$ArgumentList) [pscustomobject]@{ ExitCode=" + str(exit_code) + "; Output=@(" + ps_string(summary) + ") } }\n"
    body += "$pass=$true; try { Invoke-PytestGate 'unused' } catch { $pass=$false }; 'RESULT:' + (@{Pass=$pass} | ConvertTo-Json -Compress)"
    assert run_helpers(shell, body)["Pass"] is expected


@pytest.mark.parametrize("shell", SHELLS, ids=lambda path: path.name)
def test_release_prefers_project_build_environment(shell, tmp_path):
    python = tmp_path / ".venv-build/Scripts/python.exe"
    python.parent.mkdir(parents=True)
    python.touch()
    body = "\n$projectRoot=" + ps_string(tmp_path) + "; $chosen=Resolve-BuildPython; 'RESULT:' + (@{Python=$chosen} | ConvertTo-Json -Compress)"
    assert Path(run_helpers(shell, body)["Python"]) == python


@pytest.mark.parametrize("shell", SHELLS, ids=lambda path: path.name)
@pytest.mark.parametrize("outcome", ["test-failure", "build-failure", "invalid-exe", "success", "locked-exe"])
def test_release_build_keeps_old_exe_until_new_build_is_valid(shell, tmp_path, outcome):
    old = tmp_path / "dist/client_app.exe"
    old.parent.mkdir()
    old.write_bytes(b"MZ_OLD_WORKING_BUILD")
    body = "\n$projectRoot=" + ps_string(tmp_path) + "\n$sourceRoot=Join-Path $projectRoot 'source'\n$specPath=Join-Path $projectRoot 'client_app.spec'\n$exePath=Join-Path $projectRoot 'dist/client_app.exe'\n$outcome=" + ps_string(outcome) + "\n"
    body += r"""
function Invoke-PytestGate { param($PythonPath) if ($outcome -eq 'test-failure') { throw 'test failed' } }
function Invoke-NativeChecked {
    param($FilePath, [string[]]$ArgumentList, $Label)
    if ($ArgumentList -contains 'PyInstaller') {
        if ($outcome -eq 'build-failure') { throw 'build failed' }
        $dist = $ArgumentList[[Array]::IndexOf($ArgumentList, '--distpath') + 1]
        New-Item -ItemType Directory -Path $dist -Force | Out-Null
        $content = if ($outcome -eq 'invalid-exe') { 'INVALID' } else { 'MZ_NEW_VALID_BUILD' }
        [System.IO.File]::WriteAllText((Join-Path $dist 'client_app.exe'), $content)
    }
}
$lock = $null
if ($outcome -eq 'locked-exe') {
    $lock = [System.IO.File]::Open($exePath, [System.IO.FileMode]::Open, [System.IO.FileAccess]::Read, [System.IO.FileShare]::None)
}
$pass = $true
$errorMessage = ''
try { $build = Invoke-ProjectBuild 'unused' }
catch { $pass = $false; $errorMessage = $_.Exception.Message }
finally { if ($null -ne $lock) { $lock.Dispose() } }
'RESULT:' + (@{Pass=$pass; Content=[System.IO.File]::ReadAllText($exePath); Error=$errorMessage} | ConvertTo-Json -Compress)
"""
    result = run_helpers(shell, body)
    assert result["Pass"] is (outcome == "success"), result
    assert result["Content"] == ("MZ_NEW_VALID_BUILD" if outcome == "success" else "MZ_OLD_WORKING_BUILD")


@pytest.mark.parametrize("shell", SHELLS, ids=lambda path: path.name)
def test_release_cleanup_refuses_paths_outside_allowed_root(shell, tmp_path):
    outside = tmp_path / "keep.txt"
    outside.write_text("keep", encoding="utf-8")
    body = "\n$pass=$true; try { Remove-PathWithRetry -Path " + ps_string(outside) + " -AllowedRoot " + ps_string(tmp_path / "build") + " } catch { $pass=$false }; 'RESULT:' + (@{Pass=$pass} | ConvertTo-Json -Compress)"
    assert not run_helpers(shell, body)["Pass"]
    assert outside.read_text() == "keep"


def test_build_only_returns_before_git_github_and_version_changes():
    script = (ROOT / "release.ps1").read_text(encoding="utf-8-sig")
    branch = script.split("if ($BuildOnly) {", 1)[1].split("\n    }", 1)[0]
    assert "Invoke-ProjectBuild $python" in branch
    assert "return" in branch
    assert "git" not in branch.lower().replace("no git/github changes", "")
    assert script.index("if ($BuildOnly) {") < script.index("$git = Get-RequiredCommand 'git'")
    assert script.index("if ($BuildOnly) {") < script.index("Write-Utf8NoBom $clientPath $updatedClientContent")
