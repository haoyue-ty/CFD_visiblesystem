param([string]$EnvFile = (Join-Path $PSScriptRoot '..\.env'))

$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path $PSScriptRoot -Parent
$allowed = @('SCIENTIFIC_DATA_ROOT', 'INVENTORY_PATH', 'CANONICAL_REGISTRY_PATH',
    'API_HOST', 'API_PORT', 'ENABLE_ACCOUNTS', 'DEEPSEEK_API_KEY', 'DEEPSEEK_MODEL',
    'DEEPSEEK_BASE_URL', 'DEEPSEEK_TIMEOUT_SECONDS', 'MAX_CONCURRENT_RUNS', 'MAX_QUEUED_RUNS',
    'MAX_RUN_SECONDS', 'MAX_RUN_OUTPUT_BYTES', 'WAITRESS_THREADS', 'MAX_SSE_CONNECTIONS',
    'DEEPSEEK_MAX_RETRIES', 'AI_MAX_OUTPUT_TOKENS', 'AI_DAILY_TOKEN_BUDGET', 'AI_MAX_INPUT_CHARS')

# Load literal values into this backend process only. Never execute .env content
# and never print credentials. Existing process settings take precedence.
if (Test-Path -LiteralPath $EnvFile) {
    foreach ($line in Get-Content -LiteralPath $EnvFile -Encoding utf8) {
        if ($line -match '^\s*([A-Z_]+)\s*=(.*)$') {
            $taskName = $Matches[1]
            $taskValue = $Matches[2].Trim()
            if ($taskName -notin $allowed -or [Environment]::GetEnvironmentVariable($taskName, 'Process')) { continue }
            if (($taskValue.StartsWith('"') -and $taskValue.EndsWith('"')) -or
                ($taskValue.StartsWith("'") -and $taskValue.EndsWith("'"))) {
                $taskValue = $taskValue.Substring(1, $taskValue.Length - 2)
            }
            [Environment]::SetEnvironmentVariable($taskName, $taskValue, 'Process')
        }
    }
}

Push-Location $taskRoot
try {
    & (Join-Path $taskRoot '.venv\Scripts\python.exe') -B -m scripts.serve_backend
    $taskExitCode = $LASTEXITCODE
} finally { Pop-Location }
exit $taskExitCode
