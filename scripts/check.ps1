# Local quality gate. Run before every commit. No CI runs in the cloud.
# Each step must exit 0; the script stops at the first one that does not.
$ErrorActionPreference = "Stop"

$steps = @(
    "ruff format --check .",
    "ruff check .",
    "mypy --strict src",
    "mypy --strict tests",
    "python -m pytest"
)
foreach ($step in $steps) {
    Write-Host "> $step"
    Invoke-Expression $step
    if ($LASTEXITCODE -ne 0) { throw "Failed: $step" }
}
