# Build Directives

How to spawn subagents using the Task tool for feature builds and complex implementations. These are imperatives, not suggestions.

> **When the coordinator works directly**: Wiring, data prep, config, small fixes — subagent overhead exceeds value. Use subagent delegation for feature builds where test separation pays for itself.

---

## Context Management

Verbose commands (builds, installs, compiles) eat context. Use wrapper scripts to keep context clean:

- **Verbose commands** → `bash {baseDir}/scripts/run-command.sh npm install` — full output to log file, JSON summary to stdout
- **Test runs** → `bash {baseDir}/scripts/run-tests.sh tests/` — auto-detects runner (pytest/jest/go/cargo), returns JSON pass/fail
- **Quick one-liners** (`mkdir`, `cp`, `mv`) → run directly, wrapper overhead not justified

Both scripts accept optional `--log-dir DIR` to organize logs by session. Without it, logs go to the current directory.

---

## Research Subagent

**When:** A builder reports unknowns, or you encounter unfamiliar domain/tech during scoping.

**Spawn:** Task tool with `subagent_type: general-purpose`

**Provide:** The specific question (not "research everything about X"), where to save findings (`docs/dev/[session]/research/`), "Do NOT write implementation code. Present options with tradeoffs."

For parallel research: spawn multiple subagents simultaneously in a single message.

---

## Test Subagent

**When:** After success criteria (and contracts, if any) are defined. BEFORE implementation.

**Why tests first:** AI agents writing code AND tests together produce tests shaped to pass their code, not tests shaped to verify the contract.

**Spawn:** Task tool with `subagent_type: general-purpose`

**Provide:** Success criteria, contracts (if any), phase deliverables, target test directory, existing test patterns.

**Prompt constraints:**
```
Write tests that verify contract compliance. Tests are executable specifications.

- Tests must parse/compile successfully
- Tests should FAIL without implementation (no code exists yet)
- Cover ALL success criteria + edge cases from contracts
- Do NOT read or write implementation code
- Do NOT mock/stub the system under test
- Run tests: bash {baseDir}/scripts/run-tests.sh [test-path]

TEST NAMING — use contract-traceable names:
  Pattern: test_<contract_clause>_<behavior>
  Examples:
    test_api_get_users_returns_json_array
    test_api_get_users_unauthorized_returns_401
    test_schema_user_email_required
    test_schema_user_rejects_invalid_email
  When no formal contract exists, trace to success criteria:
    test_criteria_csv_export_includes_headers
    test_criteria_search_returns_within_500ms
  The name should answer: "which requirement broke?" without reading the test body.
```

**After:** Verify tests parse (expect failures, not errors). Verify coverage of success criteria.

---

## Implementation Subagent

**When:** After tests are verified (they parse and fail as expected).

**Spawn:** Task tool with `subagent_type: general-purpose`

**Provide:** Contracts, test file paths ("These tests must pass"), phase deliverables, previous phase handoff (if exists), existing code patterns.

**Prompt constraints:**
```
Write code that passes all tests while matching contracts.

- Full freedom in HOW to implement
- All tests MUST pass (no skipping, no modifying tests)
- Follow existing project patterns
- Do NOT mock/stub production code or modify success criteria
- Run tests: bash {baseDir}/scripts/run-tests.sh [test-path]
- For verbose commands (builds, installs): bash {baseDir}/scripts/run-command.sh <command>
- If tests can't be passed, STOP and report why
- If stuck >3 attempts, STOP and escalate
- On failure, read the log file for details instead of re-running commands
```

**After:** Run tests yourself — do NOT trust subagent's reported output. If contract changes proposed, evaluate merit, then:

1. Update the contract document with the change
2. Append to the `## Contract Changelog` section in success-criteria.md:
   ```
   - [PHASE-N] Changed: [what] → [what]. Reason: [why]. Approved by: user/coordinator.
   ```
3. If the change affects tests, re-run affected tests to confirm alignment

Never silently modify contracts. The changelog IS the audit trail.

---

## Verification Subagent

**When:** After all tests pass for a phase. Combines audit + quality checks in one pass.

**Spawn:** Task tool with `subagent_type: general-purpose`

**Provide:** Success criteria, contracts (if any), implementation file paths, test file paths.

**Prompt constraints:**
```
You are a skeptical auditor. Verify with evidence, not trust.

1. TESTS PASS — Run: bash {baseDir}/scripts/run-tests.sh [test-path]
2. CODE QUALITY — Run: bash {baseDir}/scripts/run-quality.sh [src-path]
   - Lint errors → FAIL (must fix before proceeding)
   - Security issues → report severity, FAIL on HIGH/CRITICAL
   - Type errors → advisory (report but don't block unless --strict)
   - Show the JSON summary in your report
3. CONTRACT COMPLIANCE — Compare implementation vs contracts field-by-field
   - Check Contract Changelog: any undocumented deviations → FAIL
   - Verify test names trace to contract clauses or success criteria
4. NO MOCKED PRODUCTION CODE — Check src/ for mock/stub/fake patterns
5. AI SLOP CHECK — Run /ai-slop-detector on changed files
   - Look for: theatrical error handling, dead code paths, hallucinated APIs,
     over-abstracted wrappers, comments restating the obvious
   - Advisory findings: report but don't block
   - Structural slop (hallucinated APIs, broken abstractions): FAIL
6. SUCCESS CRITERIA — For EACH criterion, show specific evidence

Red flags (AUTO-FAIL): Mocked production code, tests testing mocks,
modified success criteria, "it works" without proof, lint errors,
HIGH/CRITICAL security findings.

Output: PASS / FAIL / PARTIAL with evidence for each item.
Include quality scan JSON summary in report.
```

---

## Adversarial Review Subagent

**When:** After verification passes. This is the final gate before delivery. Mandatory for medium/heavy weight builds. Skip for light (small fixes, config changes).

**Why:** The implementation subagent and verification subagent share the same model and similar context — they have correlated blind spots. The adversarial reviewer gets the code **cold**, without planning context, contracts, or rationale. It reads the code like a new developer would: "does this actually make sense?"

**Spawn:** Agent tool with `subagent_type: general-purpose`

**Provide:** ONLY the implementation file paths. Do NOT provide success criteria, contracts, design docs, or rationale. The reviewer must judge the code on its own merits.

**Prompt constraints:**
```
You are a senior engineer reviewing code written by someone else. You have
NO context about why this code was written or what it's supposed to do.
Read it cold and answer:

LOGIC REVIEW:
- What does this code actually do? (your interpretation, not theirs)
- Are there logic bugs? (off-by-one, wrong operator, missing edge cases,
  race conditions, infinite loops, silent failures)
- Are there paths where data could be None/null/undefined unexpectedly?
- Do error handling paths actually handle the error or just swallow it?
- Are there assumptions baked in that could break? (hardcoded values,
  implicit ordering, platform assumptions)

ARCHITECTURE REVIEW:
- Is anything over-engineered for what it does?
- Is anything suspiciously simple for what it claims to do?
- Are abstractions earning their complexity?
- Would a junior developer understand this in 6 months?

SMELL TEST:
- Does anything look copy-pasted or templated without understanding?
- Are there TODO/FIXME/HACK comments that indicate unfinished work?
- Are there functions that do too many things?
- Is there dead code or unreachable branches?

For EACH finding, provide:
  - File and line number
  - What you found
  - Severity: CRITICAL (will break) / WARNING (might break) / ADVISORY (code smell)
  - Suggested fix (one sentence)

If you find nothing concerning, say so — but be genuinely skeptical.
Do NOT rubber-stamp.
```

**After:** Review findings. CRITICAL findings must be fixed before delivery (spawn implementation subagent with fix instructions). WARNING findings: present to user for decision. ADVISORY: include in handoff notes.

**Escalation:** If adversarial reviewer finds 3+ CRITICAL issues, the build phase has systemic problems. STOP, report to user, do not patch individual findings.
