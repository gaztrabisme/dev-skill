#!/usr/bin/env bash
# Smart test runner — JSON summary to stdout, full output to log file.
# Auto-detects test runner (pytest, jest, go test, cargo test) or accepts explicit runner.
#
# Usage: bash {baseDir}/scripts/run-tests.sh [options] [test-args...]
#
# Options:
#   --log-dir DIR        Directory for log files (default: current directory)
#   --runner RUNNER      Force runner: pytest|jest|go|cargo (default: auto-detect)
#
# Examples:
#   bash {baseDir}/scripts/run-tests.sh tests/
#   bash {baseDir}/scripts/run-tests.sh --log-dir docs/dev/001/logs tests/test_api.py
#   bash {baseDir}/scripts/run-tests.sh --runner jest -- --coverage
#   bash {baseDir}/scripts/run-tests.sh --runner go ./...
#
# Output (stdout): JSON summary
#   {"status":"pass","passed":47,"failed":0,"total":47,"duration":"3.2s","log":"logs/tests.log"}
#   {"status":"fail","passed":45,"failed":2,"total":47,"errors":["test_login ...","test_auth ..."],"log":"logs/tests.log"}

# ── Parse arguments ──────────────────────────────────────
log_dir="."
runner="auto"
test_args=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --log-dir)
            log_dir="$2"
            shift 2
            ;;
        --runner)
            runner="$2"
            shift 2
            ;;
        --)
            shift
            test_args=("$@")
            break
            ;;
        *)
            test_args=("$@")
            break
            ;;
    esac
done

mkdir -p "$log_dir"
log_file="${log_dir}/tests.log"

# ── Auto-detect runner ───────────────────────────────────
if [[ "$runner" == "auto" ]]; then
    if [[ -f "package.json" ]] && grep -q '"jest"\|"vitest"\|"mocha"' package.json 2>/dev/null; then
        runner="jest"
    elif [[ -f "go.mod" ]]; then
        runner="go"
    elif [[ -f "Cargo.toml" ]]; then
        runner="cargo"
    elif [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "pytest.ini" ]] || [[ -f "setup.cfg" ]]; then
        runner="pytest"
    elif command -v pytest &>/dev/null || command -v python &>/dev/null; then
        runner="pytest"
    else
        echo '{"status":"error","message":"Could not detect test runner. Use --runner to specify."}'
        exit 1
    fi
fi

# ── Run tests ────────────────────────────────────────────
set +e
case "$runner" in
    pytest)
        python -m pytest --tb=short -q "${test_args[@]}" > "$log_file" 2>&1
        exit_code=$?
        ;;
    jest)
        npx jest --no-colors "${test_args[@]}" > "$log_file" 2>&1
        exit_code=$?
        ;;
    go)
        go test -v "${test_args[@]}" > "$log_file" 2>&1
        exit_code=$?
        ;;
    cargo)
        cargo test "${test_args[@]}" > "$log_file" 2>&1
        exit_code=$?
        ;;
    *)
        echo "{\"status\":\"error\",\"message\":\"Unknown runner: ${runner}\"}"
        exit 1
        ;;
esac
set -e

# ── Parse results by runner ──────────────────────────────
json_escape() {
    local s="$1"
    s="${s//\\/\\\\}"
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

passed=0
failed=0
total=0
duration=""
errors_json="[]"

case "$runner" in
    pytest)
        # Parse pytest summary line: "47 passed, 2 failed in 3.21s"
        summary_line=$(grep -E '[0-9]+ (passed|failed|error)' "$log_file" | tail -1) || summary_line=""
        if [[ -n "$summary_line" ]]; then
            passed=$(echo "$summary_line" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+') || passed=0
            failed=$(echo "$summary_line" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+') || failed=0
            errors_count=$(echo "$summary_line" | grep -oE '[0-9]+ error' | grep -oE '[0-9]+') || errors_count=0
            failed=$((failed + errors_count))
            duration=$(echo "$summary_line" | grep -oE 'in [0-9.]+s' | sed 's/in //') || duration=""
        fi
        total=$((passed + failed))

        # Extract failing test names (FAILED lines)
        if [[ "$failed" -gt 0 ]]; then
            failing_tests=$(grep -E '^FAILED ' "$log_file" | head -5 | sed 's/^FAILED //' | sed 's/ - .*//') || failing_tests=""
            if [[ -n "$failing_tests" ]]; then
                errors_json="["
                first=true
                while IFS= read -r line; do
                    escaped=$(json_escape "$line")
                    if $first; then
                        errors_json+="\"${escaped}\""
                        first=false
                    else
                        errors_json+=",\"${escaped}\""
                    fi
                done <<< "$failing_tests"
                errors_json+="]"
            fi
        fi
        ;;

    jest)
        # Parse jest summary: "Tests: 2 failed, 45 passed, 47 total"
        summary_line=$(grep -E 'Tests:.*total' "$log_file" | tail -1) || summary_line=""
        if [[ -n "$summary_line" ]]; then
            passed=$(echo "$summary_line" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+') || passed=0
            failed=$(echo "$summary_line" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+') || failed=0
            total=$(echo "$summary_line" | grep -oE '[0-9]+ total' | grep -oE '[0-9]+') || total=0
        fi
        time_line=$(grep -E 'Time:' "$log_file" | tail -1) || time_line=""
        duration=$(echo "$time_line" | grep -oE '[0-9.]+ s' | head -1) || duration=""
        ;;

    go)
        # Parse go test: "ok" / "FAIL" lines + "--- FAIL:" lines
        passed=$(grep -cE '^ok\s' "$log_file") || passed=0
        failed=$(grep -cE '^FAIL\s' "$log_file") || failed=0
        total=$((passed + failed))
        duration=$(grep -oE '[0-9.]+s$' "$log_file" | tail -1) || duration=""

        if [[ "$failed" -gt 0 ]]; then
            failing_tests=$(grep -E '^--- FAIL:' "$log_file" | head -5 | sed 's/^--- FAIL: //; s/ (.*//' ) || failing_tests=""
            if [[ -n "$failing_tests" ]]; then
                errors_json="["
                first=true
                while IFS= read -r line; do
                    escaped=$(json_escape "$line")
                    if $first; then
                        errors_json+="\"${escaped}\""
                        first=false
                    else
                        errors_json+=",\"${escaped}\""
                    fi
                done <<< "$failing_tests"
                errors_json+="]"
            fi
        fi
        ;;

    cargo)
        # Parse cargo test: "test result: ok. 10 passed; 0 failed;"
        summary_line=$(grep -E 'test result:' "$log_file" | tail -1) || summary_line=""
        if [[ -n "$summary_line" ]]; then
            passed=$(echo "$summary_line" | grep -oE '[0-9]+ passed' | grep -oE '[0-9]+') || passed=0
            failed=$(echo "$summary_line" | grep -oE '[0-9]+ failed' | grep -oE '[0-9]+') || failed=0
        fi
        total=$((passed + failed))
        duration=$(grep -oE 'finished in [0-9.]+s' "$log_file" | grep -oE '[0-9.]+s') || duration=""

        if [[ "$failed" -gt 0 ]]; then
            failing_tests=$(grep -E "^---- .* stdout ----" "$log_file" | head -5 | sed 's/^---- //; s/ stdout ----//') || failing_tests=""
            if [[ -n "$failing_tests" ]]; then
                errors_json="["
                first=true
                while IFS= read -r line; do
                    escaped=$(json_escape "$line")
                    if $first; then
                        errors_json+="\"${escaped}\""
                        first=false
                    else
                        errors_json+=",\"${escaped}\""
                    fi
                done <<< "$failing_tests"
                errors_json+="]"
            fi
        fi
        ;;
esac

# Default values if parsing failed
passed=${passed:-0}
failed=${failed:-0}
total=${total:-0}

# ── Build JSON summary ───────────────────────────────────
status="pass"
if [[ "$exit_code" -ne 0 ]]; then
    status="fail"
fi

if [[ "$failed" -gt 0 ]]; then
    echo "{\"status\":\"${status}\",\"runner\":\"${runner}\",\"passed\":${passed},\"failed\":${failed},\"total\":${total},\"duration\":\"${duration}\",\"errors\":${errors_json},\"log\":\"${log_file}\"}"
else
    echo "{\"status\":\"${status}\",\"runner\":\"${runner}\",\"passed\":${passed},\"failed\":${failed},\"total\":${total},\"duration\":\"${duration}\",\"log\":\"${log_file}\"}"
fi

exit $exit_code
