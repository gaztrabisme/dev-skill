# Build Directives

How to spawn subagents using the Task tool for feature builds and complex implementations. These are imperatives, not suggestions.

> **When the coordinator works directly**: Wiring, data prep, config, small fixes — subagent overhead exceeds value. Use subagent delegation for feature builds where test separation pays for itself.

## Context Rules

These apply to ALL subagent spawns:

1. **Estimate output size before running commands.** If >50 lines expected, pipe to file and read summary/tail.
2. **Subagents write to disk, return summaries.** Full output goes to `docs/dev/[session]/`. The coordinator gets a TL;DR (10-20 lines).
3. **Checkpoint between phases.** For Heavy-weight builds (3+ phases), write a handoff document between phases. This survives context compaction.

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
- Use descriptive test names that read as specifications
- Do NOT read or write implementation code
- Do NOT mock/stub the system under test
- Run tests using: bash {baseDir}/scripts/run-tests.sh [test-path]
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
- Run tests using: bash {baseDir}/scripts/run-tests.sh [test-path]
- If tests can't be passed, STOP and report why
- If stuck >3 attempts, STOP and escalate
- Show actual command output, not summaries
```

**After:** Run tests yourself — do NOT trust subagent's reported output. If contract changes proposed, evaluate and either update or escalate.

---

## Agent Teams for Heavy Builds

When `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is enabled and the build spans 3+ independent modules that need cross-coordination, use agent teams instead of sequential subagents.

**When to escalate**: Modules have shared interfaces, changes in one affect another, or integration testing requires awareness of all modules simultaneously.

**When NOT to escalate**: Modules are truly independent (no shared interfaces), sequential subagents work fine. Default to subagents.

If agent teams are not enabled, fall back to parallel subagents with explicit interface contracts passed to each.

---

## Verification Subagent

**When:** After all tests pass for a phase. Combines audit + quality checks in one pass.

**Spawn:** Task tool with `subagent_type: general-purpose`

**Provide:** Success criteria, contracts (if any), implementation file paths, test file paths.

**Prompt constraints:**
```
You are a skeptical auditor. Verify with evidence, not trust.

1. TESTS PASS — Run: bash {baseDir}/scripts/run-tests.sh [test-path]
2. CONTRACT COMPLIANCE — Compare implementation vs contracts field-by-field
3. NO MOCKED PRODUCTION CODE — Check src/ for mock/stub/fake patterns
4. SECURITY SCAN — Hardcoded secrets, injection vectors, path traversal
5. SUCCESS CRITERIA — For EACH criterion, show specific evidence

Red flags (AUTO-FAIL): Mocked production code, tests testing mocks,
modified success criteria, "it works" without proof.

Output: PASS / FAIL / PARTIAL with evidence for each item.
```

### Post-Verification Discernment

After the verification subagent reports PASS, the coordinator surfaces uncertainty before closing the phase:

1. **Uncertainty disclosure** — State what the verification did NOT cover (dynamic behavior, edge cases untested, assumptions made).
2. **Targeted question** — Ask the user ONE specific question about the area of highest uncertainty. Not "does this look good?" but "The tests don't cover [X scenario] — is that acceptable, or should we add coverage?"

This counters the artifact blindspot: polished output kills scrutiny. A single well-placed question restores it.
