#!/usr/bin/env bash
# Universal command wrapper — full output to log file, JSON summary to stdout.
# Prevents context window exhaustion when running builds, installs, or any verbose command.
#
# Usage: bash {baseDir}/scripts/run-command.sh [options] -- <command...>
#
# Options:
#   --label NAME     Label for this command (used in log filename, default: "command")
#   --log-dir DIR    Directory for log files (default: current directory)
#
# Examples:
#   bash {baseDir}/scripts/run-command.sh --label "npm-install" --log-dir docs/dev/001/logs -- npm install
#   bash {baseDir}/scripts/run-command.sh --label "build" --log-dir logs -- cargo build --release
#   bash {baseDir}/scripts/run-command.sh -- python setup.py install
#
# Output (stdout): Single JSON line with summary
#   Success: {"status":"success","exit_code":0,"lines":847,"errors":0,"warnings":3,"log":"logs/npm-install.log"}
#   Failure: {"status":"failed","exit_code":1,"lines":234,"errors":2,"warnings":0,"first_error":"...","log":"logs/build.log"}

set -euo pipefail

# ── Parse arguments ──────────────────────────────────────
label="command"
log_dir="."
cmd_args=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --label)
            label="$2"
            shift 2
            ;;
        --log-dir)
            log_dir="$2"
            shift 2
            ;;
        --)
            shift
            cmd_args=("$@")
            break
            ;;
        *)
            # If no -- separator, treat everything as the command
            cmd_args=("$@")
            break
            ;;
    esac
done

if [[ ${#cmd_args[@]} -eq 0 ]]; then
    echo '{"status":"error","message":"No command provided. Usage: run-command.sh [--label NAME] [--log-dir DIR] -- <command...>"}' >&2
    exit 1
fi

# ── Setup ────────────────────────────────────────────────
mkdir -p "$log_dir"
log_file="${log_dir}/${label}.log"

# ── Run command, capture everything ──────────────────────
set +e
"${cmd_args[@]}" > "$log_file" 2>&1
exit_code=$?
set -e

# ── Analyze output ───────────────────────────────────────
total_lines=$(wc -l < "$log_file" | tr -d ' ')

# Count errors and warnings (case-insensitive, common patterns)
# Note: grep -c outputs "0" and exits 1 when no matches. Use fallback assignment to avoid capturing both.
error_count=$(grep -ciE '(^error[:\[]|ERROR[:\[]| error:| fatal:| FATAL:| FAILED|panic:)' "$log_file" 2>/dev/null) || error_count=0
warning_count=$(grep -ciE '(^warn(ing)?[:\[]|WARN(ING)?[:\[]| warning:| WARN:)' "$log_file" 2>/dev/null) || warning_count=0

# Get first error line for quick diagnosis
first_error=""
if [[ "$exit_code" -ne 0 ]]; then
    first_error=$(grep -iE '(^error[:\[]|ERROR[:\[]| error:| fatal:| FATAL:| FAILED|panic:)' "$log_file" 2>/dev/null | head -1 | cut -c1-200) || first_error=""
    # If no error pattern matched, grab last non-empty line
    if [[ -z "$first_error" ]]; then
        first_error=$(grep -v '^[[:space:]]*$' "$log_file" | tail -1 | cut -c1-200) || first_error=""
    fi
fi

# ── Build JSON summary ───────────────────────────────────
status="success"
if [[ "$exit_code" -ne 0 ]]; then
    status="failed"
fi

# Escape JSON strings (handle quotes and backslashes in error messages)
json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

first_error_escaped=$(json_escape "$first_error")

if [[ "$exit_code" -ne 0 ]]; then
    echo "{\"status\":\"${status}\",\"exit_code\":${exit_code},\"lines\":${total_lines},\"errors\":${error_count},\"warnings\":${warning_count},\"first_error\":\"${first_error_escaped}\",\"log\":\"${log_file}\"}"
else
    echo "{\"status\":\"${status}\",\"exit_code\":${exit_code},\"lines\":${total_lines},\"errors\":${error_count},\"warnings\":${warning_count},\"log\":\"${log_file}\"}"
fi

exit $exit_code
