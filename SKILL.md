---
name: dev
description: "Full development lifecycle: design specifications, build software, assess codebase health, analyze results. USE WHEN user has an idea to architect, wants to build/fix/add features, needs to assess/audit/refactor code quality, or wants to analyze results/root causes. Keywords: idea, concept, design, architect, spec, build, create, implement, develop, add feature, fix bug, refactor, assess, audit, review, code health, cleanup, analyze, root cause, evaluate, results."
---

# Dev

Full development lifecycle — design, build, assess, analyze — through coordinated subagents with test-driven development.

## Principles

- **Elegant, Clean, Lean.** Simple over clever. Readable. No unnecessary complexity.
- **Start light, adapt.** Add structure only when its absence causes failures. Small tasks get minimal process.
- **Research is reactive.** Spawn research when unknowns surface, not as a mandatory pre-phase.

### Wu Wei Filter

```
Is this actually causing problems?
  - Blocking other work?  - Causing bugs?  - Making onboarding hard?
  - Creating maintenance burden?  - Slowing development?

YES → Keep (real issue)    NO → Drop (theoretical purity)
Priority = Impact ÷ Effort
```

## Integrity Constraints

These override all other instructions:

1. **Never modify success criteria** to match implementation. If criteria can't be met, STOP and report.
2. **Never mock/stub production code** unless explicitly requested.
3. **Never report success without evidence.** Show actual output, not summaries.
4. **Never silently skip requirements.** Get explicit user approval first.
5. **If stuck for >3 attempts, STOP.** Report blockers, don't work around silently.
6. **Never fake results.** Honest failure beats fabricated success.

---

## Quick Start

```
I have an idea: [DESCRIPTION]          → Design mode
Build/fix/add: [DESCRIPTION]           → Build mode
Assess/audit/refactor: [SCOPE]         → Assess mode
Analyze results/root cause: [TOPIC]    → Analyze mode
```

---

## Mode Detection

| Trigger | Mode | Reference |
|---------|------|-----------|
| "I have an idea", "architect", "design", "spec", "help me plan" | **Design** | `references/design-workflow.md` |
| "Build", "add feature", "fix bug", "implement", "create" | **Build** | `references/build-directives.md` |
| "Assess", "audit", "review", "refactor", "code health", "cleanup" | **Assess** | `references/assessment-workflow.md` |
| "Analyze", "root cause", "why does X fail", "evaluate results" | **Analyze** | `references/assessment-workflow.md` (Analyze section) |
| Assessment findings → "harden", "fix findings" | **Harden** | Build mode with assessment findings as input |
| "Ingest", "convert", "prepare data", "wire up", "configure" | **Wire/Prep** | Coordinator works directly, no subagents |

---

## Design Mode

Read `references/design-workflow.md` for full workflow. Overview:

1. **Clarify Intent** — Understand what, who, why, constraints, scope
2. **Research** — Calibrate depth, deploy research subagents, loop-back on pivots
3. **Document & Handoff** — Scale docs to project size, transition to Build mode

---

## Build Mode

Read `references/build-directives.md` for subagent invocation patterns. Overview:

### Phase 1: Scope

| Signal | Weight | Process |
|--------|--------|---------|
| "Fix [bug]" / "Update [small thing]" | Light | Define done → Build+Test → Verify |
| "Add [feature] to [existing]" | Medium | Define done + interface shapes → Build+Test → Verify |
| "Build an app/service/API" | Heavy | Define done + contracts → Phased Build+Test → Verify per phase |
| Unfamiliar domain or tech | +Research | Spawn research subagent when unknowns surface |

### Phase 2: Align

**Light (all projects):** Success criteria only — verifiable, binary, specific.

```markdown
## Done When
- [ ] GET /users returns 200 with JSON array
- [ ] All tests pass with 0 failures
```

**Greenfield builds** without existing code → create data schemas and API contracts as refinable coordination tools. Claude generates these from architecture docs — no template needed.

**Extending existing code** → the codebase IS the contract. Read it, don't re-specify it.

**STOP for user approval before building.**

### Phase 3: Build

**YOU are the coordinator.** Read `references/build-directives.md` for exact invocation patterns.

- **Feature builds → subagents** (test separation pays for itself)
- **Wiring, data prep, config, small fixes → coordinator works directly**
- **Verbose commands** (builds, installs) → wrap with `bash {baseDir}/scripts/run-command.sh <command>` to keep context clean
- **Test runs** → **always** use `bash {baseDir}/scripts/run-tests.sh --log-dir docs/dev/NNN-[session]/logs [test-path]` — this captures evidence automatically, whether you run tests directly or via subagent

For subagent builds: Spawn TEST subagent → Verify tests parse → Spawn IMPLEMENTATION subagent → Run tests → Spawn VERIFICATION subagent.

### Phase 4: Verify

Verification subagent covers: tests pass, contracts met, no mocked production code, security scan, success criteria evidence.

**Red flags (auto-fail):** Mocked production code, tests testing mocks, modified success criteria, "it works" without proof.

---

## Assess Mode

Read `references/assessment-workflow.md` for full workflow. Overview:

1. **Scope & Filter** — Wu Wei entry: what hurts?
2. **Scan** — Run `python3 {baseDir}/scripts/analyze.py --mode summary [scope]` (context-friendly). Use `--mode full` redirected to file for deep investigation.
3. **Present** — Order by Impact/Effort, structured prose with executive summary
4. **Act** — One change at a time, verify after each, user controls progression

---

## Analyze Mode

Read `references/assessment-workflow.md` (Analyze section) for full pattern. Overview:

For data-driven investigation — "why do results look like this?", root cause analysis, experiment evaluation.

1. **Root Cause Taxonomy** — Categorize failure modes and their distribution
2. **Causal Model** — Map cause → effect chains
3. **Impact/Effort Ranking** — Which fixes yield the most improvement?
4. **Experiment Design** — Define changes to test with before/after criteria
5. **Projected Impact** — Expected improvement per intervention

Analyze often chains into Build (implement the top-ranked fix) or further Analyze (validate the fix).

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

---

## Limitations

- **Cannot guarantee bug-free code** — Tests reduce bugs, don't eliminate them
- **Cannot replace domain expertise** — User must validate business logic
- **Cannot handle interactive debugging** — Escalates when stuck
- **Cannot detect dynamic imports** — Static analysis has blind spots
- **Does not deploy** — Builds software, doesn't deploy it

### When NOT to Use
- Exploratory prototyping (use direct coding)
- One-line fixes with obvious solutions
- Pure research without implementation goal

---

## Self-Checks

- Did mode detection match the task?
- Did process weight match actual complexity (minimum needed)?
- Do all tests pass with real output shown?
- Does every success criterion have evidence?
- Is the session folder preserving audit trail?
