#!/usr/bin/env bash
# Code quality scanner — JSON summary to stdout, full output to log file.
# Runs ruff (lint + format), bandit (security), pyright (types) on Python code.
# For JS/TS projects, runs available linters.
#
# Usage: bash {baseDir}/scripts/run-quality.sh [options] [path]
#
# Options:
#   --log-dir DIR        Directory for log files (default: current directory)
#   --strict             Treat warnings as errors (default: advisories only)
#   --security-only      Run only security checks (bandit)
#   --lint-only          Run only lint checks (ruff)
#   --types-only         Run only type checks (pyright)
#
# Output (stdout): JSON summary
#   {"status":"pass","lint":{"errors":0,"warnings":3},"security":{"issues":0},"types":{"errors":0},"log":"logs/quality.log"}
#   {"status":"fail","lint":{"errors":5,"warnings":3},"security":{"issues":2,"critical":["B105:hardcoded_password"]},"types":{"errors":1},"log":"logs/quality.log"}

set -euo pipefail

# ── Parse arguments ──────────────────────────────────────
log_dir="."
target_path="."
strict=false
run_lint=true
run_security=true
run_types=true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --log-dir)
            log_dir="$2"
            shift 2
            ;;
        --strict)
            strict=true
            shift
            ;;
        --security-only)
            run_lint=false
            run_types=false
            shift
            ;;
        --lint-only)
            run_security=false
            run_types=false
            shift
            ;;
        --types-only)
            run_lint=false
            run_security=false
            shift
            ;;
        --)
            shift
            target_path="${1:-.}"
            break
            ;;
        *)
            target_path="$1"
            shift
            ;;
    esac
done

mkdir -p "$log_dir"
log_file="${log_dir}/quality.log"
> "$log_file"

# ── Helpers ──────────────────────────────────────────────
json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

has_python_files() {
    find "$target_path" -name '*.py' -not -path '*/node_modules/*' -not -path '*/.venv/*' -not -path '*/__pycache__/*' -not -path '*/.git/*' 2>/dev/null | head -1 | grep -q .
}

has_js_files() {
    find "$target_path" \( -name '*.js' -o -name '*.ts' -o -name '*.jsx' -o -name '*.tsx' \) -not -path '*/node_modules/*' -not -path '*/.git/*' 2>/dev/null | head -1 | grep -q .
}

# ── Detect project type ──────────────────────────────────
is_python=false
is_js=false

if has_python_files; then
    is_python=true
fi
if has_js_files; then
    is_js=true
fi

if ! $is_python && ! $is_js; then
    echo '{"status":"skip","message":"No Python or JS/TS files found in target path."}'
    exit 0
fi

# ── Initialize counters ─────────────────────────────────
lint_errors=0
lint_warnings=0
lint_fixable=0
security_issues=0
security_critical=()
type_errors=0
overall_status="pass"

# ── Ruff (lint + format check) ──────────────────────────
if $run_lint && $is_python && command -v ruff &>/dev/null; then
    echo "=== RUFF LINT ===" >> "$log_file"

    # Lint check
    ruff_output=$(ruff check "$target_path" --output-format=json 2>>"$log_file") || true
    echo "$ruff_output" >> "$log_file"

    if [[ -n "$ruff_output" && "$ruff_output" != "[]" ]]; then
        lint_errors=$(echo "$ruff_output" | python3 -c "
import json, sys
data = json.load(sys.stdin)
errors = [d for d in data if d.get('fix') is None]
fixable = [d for d in data if d.get('fix') is not None]
print(len(errors))
" 2>/dev/null) || lint_errors=0
        lint_fixable=$(echo "$ruff_output" | python3 -c "
import json, sys
data = json.load(sys.stdin)
fixable = [d for d in data if d.get('fix') is not None]
print(len(fixable))
" 2>/dev/null) || lint_fixable=0
        lint_warnings=$lint_fixable
    fi

    # Format check
    echo "" >> "$log_file"
    echo "=== RUFF FORMAT CHECK ===" >> "$log_file"
    format_output=$(ruff format --check "$target_path" 2>&1) || true
    echo "$format_output" >> "$log_file"
    format_issues=$(echo "$format_output" | grep -c "Would reformat" 2>/dev/null) || format_issues=0
    lint_warnings=$((lint_warnings + format_issues))

    if [[ "$lint_errors" -gt 0 ]]; then
        overall_status="fail"
    fi

elif $run_lint && $is_js; then
    # Try eslint if available
    if command -v npx &>/dev/null && [[ -f "node_modules/.bin/eslint" || -f ".eslintrc.js" || -f ".eslintrc.json" || -f "eslint.config.js" ]]; then
        echo "=== ESLINT ===" >> "$log_file"
        eslint_output=$(npx eslint "$target_path" --format json 2>>"$log_file") || true
        echo "$eslint_output" >> "$log_file"
        if [[ -n "$eslint_output" ]]; then
            lint_errors=$(echo "$eslint_output" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(sum(d.get('errorCount', 0) for d in data))
" 2>/dev/null) || lint_errors=0
            lint_warnings=$(echo "$eslint_output" | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(sum(d.get('warningCount', 0) for d in data))
" 2>/dev/null) || lint_warnings=0
        fi
        if [[ "$lint_errors" -gt 0 ]]; then
            overall_status="fail"
        fi
    fi
fi

# ── Bandit (security) ───────────────────────────────────
if $run_security && $is_python && command -v bandit &>/dev/null; then
    echo "" >> "$log_file"
    echo "=== BANDIT SECURITY SCAN ===" >> "$log_file"

    bandit_output=$(bandit -r "$target_path" -f json --exclude '*/.venv/*,*/node_modules/*,*/__pycache__/*' 2>>"$log_file") || true
    echo "$bandit_output" >> "$log_file"

    if [[ -n "$bandit_output" ]]; then
        security_issues=$(echo "$bandit_output" | python3 -c "
import json, sys
data = json.load(sys.stdin)
results = data.get('results', [])
print(len(results))
" 2>/dev/null) || security_issues=0

        # Extract high/critical severity issues
        critical_list=$(echo "$bandit_output" | python3 -c "
import json, sys
data = json.load(sys.stdin)
results = data.get('results', [])
critical = [f\"{r['test_id']}:{r['test_name']}\" for r in results if r.get('issue_severity') in ('HIGH', 'MEDIUM')]
for c in critical[:5]:
    print(c)
" 2>/dev/null) || critical_list=""

        if [[ -n "$critical_list" ]]; then
            while IFS= read -r line; do
                security_critical+=("$line")
            done <<< "$critical_list"
        fi
    fi

    if [[ "$security_issues" -gt 0 ]]; then
        if $strict; then
            overall_status="fail"
        fi
    fi
fi

# ── Pyright (type checking) ─────────────────────────────
if $run_types && $is_python && command -v pyright &>/dev/null; then
    echo "" >> "$log_file"
    echo "=== PYRIGHT TYPE CHECK ===" >> "$log_file"

    pyright_output=$(pyright "$target_path" --outputjson 2>>"$log_file") || true
    echo "$pyright_output" >> "$log_file"

    if [[ -n "$pyright_output" ]]; then
        type_errors=$(echo "$pyright_output" | python3 -c "
import json, sys
data = json.load(sys.stdin)
summary = data.get('summary', {})
print(summary.get('errorCount', 0))
" 2>/dev/null) || type_errors=0
    fi

    # Type errors are advisory in non-strict mode
    if [[ "$type_errors" -gt 0 ]] && $strict; then
        overall_status="fail"
    fi
fi

# ── Build JSON summary ──────────────────────────────────
critical_json="[]"
if [[ ${#security_critical[@]} -gt 0 ]]; then
    critical_json="["
    first=true
    for item in "${security_critical[@]}"; do
        escaped=$(json_escape "$item")
        if $first; then
            critical_json+="\"${escaped}\""
            first=false
        else
            critical_json+=",\"${escaped}\""
        fi
    done
    critical_json+="]"
fi

cat <<EOJSON
{"status":"${overall_status}","lint":{"errors":${lint_errors},"warnings":${lint_warnings},"fixable":${lint_fixable}},"security":{"issues":${security_issues},"critical":${critical_json}},"types":{"errors":${type_errors}},"log":"${log_file}"}
EOJSON

if [[ "$overall_status" == "fail" ]]; then
    exit 1
fi
exit 0
