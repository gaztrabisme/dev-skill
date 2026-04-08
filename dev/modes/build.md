# Build Mode

Feature builds via coordinated subagents with test-driven development. YOU are the coordinator.

---

## Phase 1: Scope

| Signal | Weight | Process |
|--------|--------|---------|
| "Fix [bug]" / "Update [small thing]" | Light | Define done → Build+Test → Verify |
| "Add [feature] to [existing]" | Medium | Define done + interface shapes → Build+Test → Verify → Adversarial Review |
| "Build an app/service/API" | Heavy | Define done + contracts → Phased Build+Test → Verify per phase → Adversarial Review |
| Unfamiliar domain or tech | +Research | Spawn research subagent when unknowns surface |
| ML/CV/NLP task | +ML Heuristics | Read `references/ml-heuristics.md` — reframe problem before choosing approach |

---

## Phase 2: Align

**Light (all projects):** Success criteria only — verifiable, binary, specific.

```markdown
## Done When
- [ ] GET /users returns 200 with JSON array
- [ ] All tests pass with 0 failures

## Contract Changelog
<!-- Append entries here if contracts change during build -->
<!-- Format: - [PHASE-N] Changed: X → Y. Reason: Z. Approved by: user/coordinator. -->
```

**Greenfield builds** without existing code → create data schemas and API contracts as refinable coordination tools. Claude generates these from architecture docs.

**Extending existing code** → the codebase IS the contract. Read it, don't re-specify it.

**Test naming convention:** `test_<contract_clause>_<behavior>` (e.g., `test_api_get_users_returns_json_array`). When a test fails, the name tells you which requirement broke.

**STOP for user approval before building.**

---

## Phase 3: Build

### Context Management

- **Verbose commands** (builds, installs) → `bash {baseDir}/scripts/run-command.sh <command>`
- **Test runs** → `bash {baseDir}/scripts/run-tests.sh [test-path]`
- **Quick one-liners** (`mkdir`, `cp`, `mv`) → run directly

### Codebase Understanding (Existing Projects)

Use GitNexus MCP tools (if repo is indexed) before scoping:
- `context <symbol>` — 360-degree view: callers, callees, process participation
- `impact <symbol>` — Blast radius with depth grouping and confidence
- `detect_changes` — Maps git diff to affected symbols/processes
- `query <concept>` — Find execution flows for a concept end-to-end

Skip GitNexus for: greenfield projects, small fixes where you can read the code directly, config/wiring tasks.

### API Documentation (Greenfield / Unfamiliar Libraries)

Use Context Hub before writing code with unfamiliar libraries:
```bash
chub search "fastapi"          # Find available docs
chub get fastapi/package       # Fetch curated API reference
```

### Subagent Orchestration

**Feature builds → subagents** (test separation pays for itself). **Wiring, data prep, config, small fixes → coordinator works directly.**

Spawn in this order:
1. **Test subagent** — BEFORE implementation. Tests verify contract, not code.
2. **Test validation subagent** (medium/heavy only) — Reviews tests cold against business requirements.
3. **Implementation subagent** — Write code that passes tests.
4. **Verification subagent** — Tests pass, quality scan, contract compliance, no mocked production.
5. **Adversarial review subagent** (medium/heavy only) — Cold code review, no planning context.

Read `references/subagent-briefs.md` for exact prompt templates. When briefing subagents, provide ONLY the relevant prompt constraints from that file plus task-specific context. Do not forward skill-level instructions.

---

## Phase 4: Verify

Verification subagent covers: tests pass, code quality scan (ruff + bandit + pyright via `run-quality.sh`), contracts met, no mocked production code, ai-slop-detector, success criteria evidence.

**Red flags (auto-fail):** Mocked production code, tests testing mocks, modified success criteria, "it works" without proof, lint errors, HIGH/CRITICAL security findings.

---

## Phase 5: Adversarial Review (medium/heavy builds)

A separate subagent reviews the code **cold** — no planning context, no contracts, no rationale. Reads the code like a new developer joining the project.

- **CRITICAL findings** → must fix before delivery
- **3+ CRITICAL** → systemic problem, STOP and escalate to user
- **Skip for**: light-weight tasks (small fixes, config, wiring)

---

## Evidence

Match effort to task weight:

| Weight | Evidence |
|--------|----------|
| **Light** (bug fix, config, wiring) | Pass/fail count + 1-line summary per criterion |
| **Medium** (feature, refactor) | `run-tests.sh` JSON in `logs/` + checked criteria |
| **Heavy** (multi-phase, greenfield) | Full `logs/` directory + report.md + checked criteria |

Minimum: every success criterion either checked with evidence, deferred with reason, or marked N/A.

---

## Failure Protocol

```
Attempt 1: Same subagent retries with error feedback
Attempt 2: Fresh subagent with original spec + "Approach X failed, try Y"
Attempt 3: ESCALATE to user
```

Escalation includes: what was attempted, specific blockers, options (simplify scope / change approach / user assists / abort).
