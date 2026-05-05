# Subagent Briefs

Prompt templates for each subagent type. The coordinator reads the relevant brief and passes ONLY that brief plus task-specific context to the subagent. Subagents never see the full skill.

---

## Research Subagent

**When:** Unknowns surface during scoping, or unfamiliar domain/tech encountered.

**Spawn:** Agent tool with `subagent_type: general-purpose`

**Provide:** The specific question (not "research everything about X"), expected output format.

**Prompt constraints:**
```
Research: [specific question]

Do NOT write implementation code. Present options with tradeoffs.
If you find multiple viable approaches, compare them in a table.
```

For parallel research: spawn multiple subagents simultaneously in a single message.

---

## Test Subagent

**When:** After success criteria (and contracts, if any) are defined. BEFORE implementation.

**Why tests first:** AI agents writing code AND tests together produce tests shaped to pass their code, not tests shaped to verify the contract.

**Spawn:** Agent tool with `subagent_type: general-purpose`

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

## Test Validation Subagent

**When:** Opt-in for high-stakes domains (finance, security, healthcare, data integrity). Skip when tests were written against clear success criteria — the test and validation subagents read the same spec and have correlated blind spots. Most builds don't need this gate.

**Why:** Bad tests corrupt everything downstream. The test subagent's interpretation could miss business-critical paths, over-test implementation details, or misunderstand domain requirements.

**Spawn:** Agent tool with `subagent_type: general-purpose`

**Provide:** Test file paths, success criteria, contracts (if any), business context/requirements. Do NOT provide the test subagent's process or reasoning.

**Prompt constraints:**
```
You are reviewing tests written by someone else. You have the business
requirements and success criteria but you did NOT write these tests.

COVERAGE:
- Does every success criterion have at least one test? Map each criterion
  to its test(s). Flag any criterion with no coverage.
- Are there business-critical paths NOT in the success criteria that should
  be tested? (e.g., security boundaries, data integrity, failure recovery)
- Are edge cases covered? (empty inputs, boundary values, concurrent access,
  invalid data, permission boundaries)

CORRECTNESS:
- Does each test actually verify what its name claims?
- Are any tests testing implementation details instead of behavior?
  (e.g., testing that a specific function is called vs testing the outcome)
- Are assertions meaningful? (e.g., "assert response is not None" is weak —
  "assert response.status == 200 and 'users' in response.json()" is strong)
- Could any test pass with a wrong implementation? (e.g., testing only the
  happy path when the requirement implies error handling)

DOMAIN:
- Do tests reflect how the system will actually be used?
- Are there domain-specific invariants missing? (e.g., financial calculations
  need precision tests, auth flows need token expiry tests)

For EACH finding:
  - Test name and file
  - What's wrong or missing
  - Severity: CRITICAL (will miss real bugs) / WARNING (weak coverage) /
    ADVISORY (could be better)
  - Suggested fix (one sentence)

If tests are solid, say so — but be genuinely skeptical.
```

**After:** CRITICAL findings → test subagent fixes before implementation proceeds. WARNING → coordinator decides. ADVISORY → note for later.

---

## Implementation Subagent

**When:** After tests are verified (parse and fail as expected) and validated (medium/heavy).

**Spawn:** Agent tool with `subagent_type: general-purpose`

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

**Additional constraint — surface key decisions in your report:**
```
At the end of your report, include a "Key Decisions" section listing the
3–5 most load-bearing decisions you made while implementing. For each:
  - What you picked (one line)
  - What the naive alternative would have been (one line)
  - Why the naive alternative would have failed or been worse (one line)
Not every decision — the ones a junior engineer would benefit from seeing.
The coordinator uses this to teach the user inline; don't skip it.
```

**After:** Run tests yourself — do NOT trust subagent's reported output. Read the Key Decisions section and pick the single most load-bearing one to narrate to the user with a `**Why this matters:**` tag — per `references/pushback-and-teach.md`, one concept per task. If you changed any interface shape that tests depend on, re-run affected tests to confirm alignment.

---

## Verification Subagent

**When:** After all tests pass for a phase.

**Spawn:** Agent tool with `subagent_type: general-purpose`

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
5. TECHNICAL SOUNDNESS — Read the code for structural problems tools can't catch:
   - Algorithmic efficiency: nested loops over same data? O(n²) where set/dict gives O(n)?
   - Resource management: files/connections/locks opened but not closed? Missing context managers?
   - Concurrency safety: shared mutable state without locks? async/await misuse? race conditions?
   - Error propagation: does the error reach someone who can act, or does it vanish silently?
   - Severity: CRITICAL if it will cause data loss, deadlock, or resource exhaustion under load.
     WARNING if it degrades performance or fails under edge conditions. ADVISORY for suboptimal patterns.
6. AI SLOP CHECK — Run /ai-slop-detector on changed files
   - Look for: theatrical error handling, dead code paths, hallucinated APIs,
     over-abstracted wrappers, comments restating the obvious
   - Advisory findings: report but don't block
   - Structural slop (hallucinated APIs, broken abstractions): FAIL
7. SUCCESS CRITERIA — For EACH criterion, show specific evidence

Red flags (AUTO-FAIL): Mocked production code, tests testing mocks,
modified success criteria, "it works" without proof, lint errors,
HIGH/CRITICAL security findings.

Output: PASS / FAIL / PARTIAL with evidence for each item.
Include quality scan JSON summary in report.
```

---

## Adversarial Review Subagent

**When:** After verification passes. Final gate before delivery. **Medium/heavy builds only.** Skip for light (small fixes, config).

**Why:** Implementation and verification subagents share similar context — they have correlated blind spots. The adversarial reviewer gets the code **cold**.

**Spawn:** Agent tool with `subagent_type: general-purpose`

**Provide:** ONLY the implementation file paths. Do NOT provide success criteria, contracts, design docs, or rationale.

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

**After:** CRITICAL findings must be fixed before delivery. WARNING: present to user. ADVISORY: include in handoff notes. If 3+ CRITICAL → systemic problem, STOP and escalate to user.

---

## Spec Adversarial Review Subagent

**When:** Before handoff from Design to Build mode. Skip for light builds.

**Spawn:** Agent tool with `subagent_type: general-purpose`

**Provide:** ONLY spec documents (success criteria, contracts, CLAUDE.md, data models). No conversation context or rationale.

**Prompt constraints:**
```
You are a senior engineer handed a spec to implement. You have NO context
about why decisions were made. Read the spec cold and answer:

COMPLETENESS:
- Can you build this without asking questions? If not, what's missing?
- Are all success criteria binary and testable? Flag any that say "works well",
  "handles gracefully", "is fast" — these are untestable.
- Are error cases specified? What happens when inputs are invalid, services
  are down, or data is missing?
- Are edge cases called out? (empty inputs, boundary values, concurrent access,
  large payloads)

CONTRADICTIONS:
- Do any requirements conflict with each other?
- Do contracts match the success criteria? Any gaps?
- Are there implicit assumptions that aren't stated?

ARCHITECTURE:
- Does the proposed approach match the problem scale? (over-engineered or
  under-engineered?)
- Are there simpler alternatives the spec doesn't consider?
- What will be hardest to change later if requirements shift?
- Any scalability concerns visible from the spec alone?

MISSING UNKNOWNS:
- What risks aren't addressed?
- What third-party dependencies could block implementation?
- What questions would you ask in a design review?

For EACH finding:
  - Section/criterion affected
  - What you found
  - Severity: CRITICAL (will block build or cause wrong product) /
    WARNING (likely to cause rework) / ADVISORY (worth discussing)
  - Suggested resolution (one sentence)

If the spec is solid, say so — but be genuinely skeptical.
```

**After:** CRITICAL → must resolve before handoff. WARNING → user decides. ADVISORY → note in handoff. If 3+ CRITICAL → spec needs another iteration.

---

## Mechanical Edit Pattern

**When:** The task is repetitive pattern application across many files (dark mode classes, rename, migration, i18n keys). The change is predictable and doesn't require reasoning about each file.

**DO NOT spawn a reasoning agent.** Instead:

1. Read 2-3 representative files to confirm the pattern
2. Generate a structured edit list: `[{file, old, new}, ...]`
3. Apply edits via Edit tool with `replace_all` where safe
4. Verify with build/lint

**Token budget:** ~1K per file (read + edit). A mechanical task touching 20 files should cost ~20K tokens, not 100K+ for a reasoning agent.

**When it's NOT mechanical:** If each file needs different logic (conditional changes, context-dependent decisions), use a regular implementation subagent.
