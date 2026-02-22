#!/usr/bin/env bash
# Smart test runner — minimal output on success, full detail on failure.
# Prevents context window exhaustion when running large test suites.
#
# Usage: bash {baseDir}/scripts/run-tests.sh [pytest-args...]
# Examples:
#   bash {baseDir}/scripts/run-tests.sh tests/
#   bash {baseDir}/scripts/run-tests.sh tests/test_api.py -k "test_auth"
#   bash {baseDir}/scripts/run-tests.sh --cov=src tests/

output=$(python -m pytest --tb=short -q "$@" 2>&1)
exit_code=$?

if [ $exit_code -eq 0 ]; then
    # Success: only show summary line
    echo "$output" | tail -n 3
else
    # Failure: show full output so subagent can diagnose
    echo "$output"
fi

exit $exit_code
