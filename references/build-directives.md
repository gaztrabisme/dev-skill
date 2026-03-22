# Build Directives

How to coordinate subagents for builds where test separation matters. For small fixes and wiring, skip this — work directly.

---

## Context Management

- **Verbose commands** → `bash {baseDir}/scripts/run-command.sh --label "build" -- npm install`
- **Test runs** → `bash {baseDir}/scripts/run-tests.sh tests/`
- **Quick one-liners** → run directly

Both accept `--log-dir DIR` to organize logs.

---

## Test-First Subagent

**When:** Medium+ builds. After success criteria are defined, BEFORE implementation.

**Why:** AI writing code AND tests together produces tests shaped to pass the code, not tests that verify the contract.

Spawn with `subagent_type: general-purpose`. Provide success criteria, target test directory, existing test patterns.

```
Write tests that verify the success criteria. Tests are executable specifications.

- Tests must parse/compile successfully
- Tests should FAIL without implementation (no code exists yet)
- Cover success criteria + edge cases
- Do NOT read or write implementation code
- Do NOT mock/stub the system under test
- Name tests: test_<what>_<expected_behavior>
  e.g. test_api_get_users_returns_json, test_search_empty_query_returns_all
```

---

## Implementation Subagent

**When:** After tests exist and fail as expected.

Provide test file paths, existing code patterns, any contracts.

```
Write code that passes all tests.

- Full freedom in HOW to implement
- All tests MUST pass — no skipping, no modifying tests
- Follow existing project patterns
- Do NOT mock/stub production code
- Run tests: bash {baseDir}/scripts/run-tests.sh [test-path]
- If stuck >3 attempts, STOP and escalate
```

**After:** Run tests yourself. Don't trust the subagent's reported output.

---

## Cold Review Subagent

**When:** After tests pass, for medium/heavy builds. Skip for small fixes.

**Why:** Builder and verifier share the same model — correlated blind spots. The cold reviewer reads the code with NO context about why it was written.

Provide ONLY the implementation file paths. Do NOT provide success criteria, design docs, or rationale.

```
You are a senior engineer reviewing code written by someone else.
NO context about why this code was written.

LOGIC: bugs, edge cases, silent failures, hardcoded assumptions?
ARCHITECTURE: over-engineered? under-engineered? abstractions earning their cost?
SMELLS: copy-paste? dead code? functions doing too many things?

For each finding: file, line, what, severity (CRITICAL/WARNING/ADVISORY), one-sentence fix.
If nothing concerning, say so — but be genuinely skeptical.
```

- CRITICAL findings → must fix before delivery
- 3+ CRITICAL → systemic problem, STOP and escalate to user
