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
Train/finetune: [DESCRIPTION]          → Train mode
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
| "Train", "finetune", "experiment", "hyperparameter", "evaluate model" | **Train** | `references/ml-heuristics.md` (Training mode) |
| "Ingest", "convert", "prepare data", "wire up", "configure" | **Wire/Prep** | Coordinator works directly, no subagents |
| "Evolve", "meta", "improve the skill", "self-improve" | **Evolve** | `references/evolve-workflow.md` |

---

## Design Mode

Read `references/design-workflow.md` for full workflow. Overview:

1. **Clarify Intent** — Understand what, who, why, constraints, scope
2. **Research** — Calibrate depth, deploy research subagents, loop-back on pivots
3. **Document** — Scale docs to project size
4. **Spec Adversarial Review** — Cold review of spec by subagent with no discussion context. Catches untestable criteria, missing edge cases, contradictions, over/under-engineering. CRITICAL findings must resolve before handoff. Skip for light builds.
5. **Handoff** — Exit gate: all criteria binary+testable, unknowns named, no unresolved CRITICALs, spec is stranger-readable. Transition to Build mode.

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
| ML/CV/NLP task (train, finetune, detect, classify, deploy model) | +ML Heuristics | Read `references/ml-heuristics.md` — reframe problem before choosing approach |

### Phase 2: Align

**Light (all projects):** Success criteria only — verifiable, binary, specific.

```markdown
## Done When
- [ ] GET /users returns 200 with JSON array
- [ ] All tests pass with 0 failures

## Contract Changelog
<!-- Append entries here if contracts change during build -->
<!-- Format: - [PHASE-N] Changed: X → Y. Reason: Z. Approved by: user/coordinator. -->
```

**Greenfield builds** without existing code → create data schemas and API contracts as refinable coordination tools. Claude generates these from architecture docs — no template needed.

**Extending existing code** → the codebase IS the contract. Read it, don't re-specify it.

**Test naming convention:** Tests trace back to contracts/criteria via their names: `test_<contract_clause>_<behavior>` (e.g., `test_api_get_users_returns_json_array`). When a test fails, the name tells you which requirement broke.

**STOP for user approval before building.**

### Phase 3: Build

**YOU are the coordinator.** Read `references/build-directives.md` for exact invocation patterns.

- **Feature builds → subagents** (test separation pays for itself)
- **Wiring, data prep, config, small fixes → coordinator works directly**
- **Verbose commands** (builds, installs) → wrap with `bash {baseDir}/scripts/run-command.sh <command>` to keep context clean
- **Test runs** → `bash {baseDir}/scripts/run-tests.sh [test-path]` for structured JSON results

For subagent builds: Spawn TEST subagent → **Test validation** (medium/heavy) → Spawn IMPLEMENTATION subagent → Run tests → Spawn VERIFICATION subagent → Spawn ADVERSARIAL REVIEW subagent (medium/heavy only).

**Test validation** (medium/heavy builds): After tests parse, spawn a validation subagent with the tests + success criteria + business context (but NOT the test-writing process). It answers: "Do these tests actually verify what the business requires? Are there critical paths missing?" This catches bad tests before they corrupt everything downstream. See `references/build-directives.md` for prompt.

### Phase 4: Verify

Verification subagent covers: tests pass, **code quality scan** (ruff + bandit + pyright via `run-quality.sh`), contracts met, no mocked production code, **ai-slop-detector**, success criteria evidence.

**Red flags (auto-fail):** Mocked production code, tests testing mocks, modified success criteria, "it works" without proof, lint errors, HIGH/CRITICAL security findings.

### Phase 5: Adversarial Review (medium/heavy builds)

A separate subagent reviews the code **cold** — no planning context, no contracts, no rationale. It reads the code like a new developer joining the project. Catches logic bugs, over-engineering, and correlated blind spots that verification misses.

- **CRITICAL findings** → must fix before delivery
- **3+ CRITICAL** → systemic problem, STOP and escalate to user
- **Skip for**: light-weight tasks (small fixes, config, wiring)

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

## Train Mode

Read `references/ml-heuristics.md` for full reference. Overview:

For iterative ML training loops — finetuning, architecture experiments, hyperparameter search. Unlike Build mode (test → implement → verify), Train mode follows an experiment loop where success is measured by metrics, not binary tests.

### Workflow

1. **Define convergence criteria** — What metrics, what thresholds, what's "good enough"? (e.g., mAP@50 > 0.85, inference < 50ms)
2. **Validate data** — Before training: check data quality, class distribution, train/val/test splits, label consistency. Use Build mode for data pipeline engineering if needed.
3. **Baseline** — Establish baseline metrics with minimal config. Record in experiment log.
4. **Experiment loop** — Change one variable → train → evaluate → record in `experiment-log.md` → decide next step. Read the log before every experiment to avoid retrying dead ends.
5. **Evaluate** — When convergence criteria met (or diminishing returns): export, benchmark inference, validate on held-out data.

### Key Differences from Build Mode

| Build Mode | Train Mode |
|-----------|------------|
| Success = tests pass (binary) | Success = metrics meet criteria (continuous) |
| Test → implement → verify (linear) | Experiment → evaluate → adjust (loop) |
| Subagents for separation | Coordinator runs directly (training is sequential) |
| Contract changelog for changes | Experiment log for iterations |
| Adversarial review at end | Analyze mode for result investigation |

Train mode chains into: **Build** (inference engine, deployment pipeline), **Analyze** (why are results bad?), or more **Train** (next experiment).

---

## Evolve Mode

Read `references/evolve-workflow.md` for full workflow. Overview:

The skill improves itself by analyzing its own traces. This is meta-prompting: the same structured process that builds software is turned inward on the skill's own prompts, workflows, and conventions.

1. **Harvest** — Collect traces since last evolution: git history, contract changelogs, quality reports, adversarial findings, failure escalations
2. **Pattern** — Classify recurring signals: what keeps failing? what gets caught late? what ceremony gets skipped? what contract changes repeat?
3. **Hypothesize** — Propose specific skill modifications with predicted effect
4. **Apply** — Modify skill files (prompts, workflows, conventions) through the skill's own build process
5. **Validate** — Run the evolved skill on a real project, compare trace quality before/after

Quality of self-improvement = quality of traces. Every structured output (test names, contract changelogs, quality JSON, adversarial findings) is a signal the evolve loop can learn from.

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
- For ML work: is the experiment log up to date?
