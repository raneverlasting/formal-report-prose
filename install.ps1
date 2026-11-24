[CmdletBinding()]
param(
    [string]$Target = (Join-Path $HOME ".dsh\skills\formal-report-prose"),
    [string]$GlobalRulesTarget = (Join-Path $HOME ".dsh\AGENTS.md"),
    [switch]$GlobalRules,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"
$Source = $PSScriptRoot
if (-not $Source) {
    $Source = (Get-Location).Path
}
$required = @(
    "SKILL.md",
    "references\rewrite-rules.md",
    "scripts\lint_prose.py",
    "tests\cases.md",
    "tests\test_lint_prose.py",
    "global-rules.md"
)

foreach ($relative in $required) {
    $path = Join-Path $Source $relative
    if (-not (Test-Path -LiteralPath $path)) {
        throw "Missing required file: $path"
    }
}

$sourceFull = [IO.Path]::GetFullPath($Source).TrimEnd('\')
$targetFull = [IO.Path]::GetFullPath($Target).TrimEnd('\')
if ($targetFull.Equals($sourceFull, [StringComparison]::OrdinalIgnoreCase) -or
    $targetFull.StartsWith($sourceFull + '\', [StringComparison]::OrdinalIgnoreCase)) {
    throw "Target must be outside the source directory: $Target"
}

Write-Host "Source: $sourceFull"
Write-Host "Target: $targetFull"

if ($DryRun) {
    Write-Host "Dry run: no files changed."
} else {
    $parent = Split-Path -Parent $targetFull
    if ($parent -and -not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }

    if (Test-Path -LiteralPath $targetFull) {
        $backup = "$targetFull.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
        Copy-Item -LiteralPath $targetFull -Destination $backup -Recurse -Force
        Remove-Item -LiteralPath $targetFull -Recurse -Force
        Write-Host "Backup: $backup"
    }

    New-Item -ItemType Directory -Path $targetFull -Force | Out-Null
    Get-ChildItem -LiteralPath $sourceFull -Force |
        Where-Object { $_.Name -notin @(".git", "__pycache__", ".pytest_cache") } |
        ForEach-Object {
            Copy-Item -LiteralPath $_.FullName -Destination $targetFull -Recurse -Force
        }
    Get-ChildItem -LiteralPath $targetFull -Recurse -Force -Directory |
        Where-Object { $_.Name -in @("__pycache__", ".pytest_cache") } |
        Remove-Item -Recurse -Force
    Write-Host "Installed skill files."
}

if ($GlobalRules) {
    $begin = "<!-- formal-report-prose:start -->"
    $end = "<!-- formal-report-prose:end -->"
    $rules = Get-Content -LiteralPath (Join-Path $sourceFull "global-rules.md") -Raw -Encoding UTF8
    $block = "$begin`r`n$($rules.Trim())`r`n$end"

    if (Test-Path -LiteralPath $GlobalRulesTarget) {
        [string]$existing = Get-Content -LiteralPath $GlobalRulesTarget -Raw -Encoding UTF8
        if ($existing.Contains($begin) -and $existing.Contains($end)) {
            $pattern = "(?s)" + [regex]::Escape($begin) + ".*?" + [regex]::Escape($end)
            $updated = [regex]::Replace($existing, $pattern, $block)
            $action = "Updated"
        } else {
            $updated = $existing.TrimEnd() + "`r`n`r`n" + $block + "`r`n"
            $action = "Appended"
        }
        if (-not $DryRun) {
            $backup = "$GlobalRulesTarget.bak-$(Get-Date -Format 'yyyyMMdd-HHmmss')"
            Copy-Item -LiteralPath $GlobalRulesTarget -Destination $backup -Force
            Write-Host "Global rules backup: $backup"
        }
    } else {
        $updated = $block + "`r`n"
        $action = "Created"
    }

    if ($DryRun) {
        Write-Host "Dry run: would $($action.ToLower()) global rules in $GlobalRulesTarget"
    } else {
        $globalParent = Split-Path -Parent $GlobalRulesTarget
        if ($globalParent -and -not (Test-Path -LiteralPath $globalParent)) {
            New-Item -ItemType Directory -Path $globalParent -Force | Out-Null
        }
        Set-Content -LiteralPath $GlobalRulesTarget -Value $updated -Encoding UTF8
        Write-Host "$action global rules: $GlobalRulesTarget"
    }
}

Write-Host "Done."
