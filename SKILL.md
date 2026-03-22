---
name: dev
description: "Development lifecycle: build software, run experiments, assess codebases. USE WHEN user wants to build/fix/add features, run iterative experiments (training, optimization, tuning), or assess/refactor code. Keywords: build, create, implement, fix, experiment, train, optimize, tune, sweep, assess, refactor, analyze."
---

# Dev

Build software. Run experiments. Assess codebases. Minimum process, maximum output.

## Principles

- **Simple over clever.** Readable. No unnecessary complexity.
- **Start light.** Add structure only when its absence causes failures.
- **Research is reactive.** Spawn research when unknowns surface, not upfront.

### Wu Wei Filter

```
Is this actually causing problems?
  - Blocking work?  - Causing bugs?  - Maintenance burden?  - Slowing development?

YES → Fix (real issue)    NO → Drop (theoretical purity)
Priority = Impact ÷ Effort
```

## Integrity Constraints

These override everything else:

1. **Never modify success criteria** to match implementation. If criteria can't be met, STOP and report.
2. **Never mock/stub production code** unless explicitly requested.
3. **Never report success without evidence.** Show actual output, not summaries.
4. **Never silently skip requirements.** Get explicit user approval first.
5. **If stuck for >3 attempts, STOP.** Report blockers, don't work around silently.
6. **Never fake results.** Honest failure beats fabricated success.

---

## Modes

Claude infers the mode from context. No keyword matching needed.

### Build

For software: features, bug fixes, services, APIs, scripts.

**Light** (fix bug, small change): Just do it. Define done → build → verify.

**Medium** (feature, refactor): Define done → tests first → build → verify → cold review.

**Heavy** (greenfield app, multi-component): Define done + contracts → phased build with tests → verify per phase → cold review.

Read `references/build-directives.md` for subagent patterns when building with test separation.

**Key rules:**
- Write tests before implementation for medium+ builds (prevents AI-shaped tests)
- Extending existing code → the codebase IS the contract. Read it, don't re-specify it.
- Use `bash {baseDir}/scripts/run-tests.sh` and `bash {baseDir}/scripts/run-quality.sh` for structured output
- Use `bash {baseDir}/scripts/run-command.sh` to wrap verbose commands (builds, installs)
- For medium/heavy builds, spawn a **cold review** subagent — gives it ONLY the code, no context, no rationale. Catches correlated blind spots.

### Experiment

For iterative optimization: model training, hyperparameter sweeps, data pipeline tuning, prompt engineering, config optimization — anything with a measurable score.

Read `references/experiment-loop.md` for the full pattern. Core idea:

```
LOOP:
  1. Propose change (hypothesis)
  2. Apply change to the mutable surface
  3. Run evaluation (fixed budget, single metric)
  4. Record result
  5. If improved → keep. If worse → revert.
  6. Repeat until interrupted or diminishing returns.
```

**Key rules:**
- Fix the evaluation. Lock it down so the agent can't game the metric.
- Single scalar metric. Reduce the objective to one number.
- Fixed time/compute budget per run. Makes every experiment directly comparable.
- Git as experiment tracking. Improvements advance the branch; failures get reverted.
- Redirect verbose output to log files. Extract only the metric. Protect context.
- **NEVER STOP unless asked.** If out of ideas, try the opposite of what worked.

### Assess

For codebase health, refactoring, auditing.

1. **What hurts?** — Wu Wei entry. Scope to what the user asked about.
2. **Scan** — `python3 {baseDir}/scripts/analyze.py --mode summary [path]` for overview, `--mode full` for deep dive.
3. **Present** — Order by Impact ÷ Effort. What's working, what hurts, what to skip.
4. **Act** — One change at a time. Verify after each. User controls progression.

### Analyze

For data-driven investigation: "why do results look like this?", root cause analysis, experiment evaluation.

1. Categorize failure modes and their distribution
2. Map cause → effect chains
3. Rank fixes by impact ÷ effort
4. Design experiments to test the top fix
5. Chain into Build (implement) or Experiment (validate)

---

## Failure Protocol

```
Attempt 1: Retry with error feedback
Attempt 2: Fresh approach with "X failed because Y, try Z"
Attempt 3: ESCALATE to user with: what was tried, specific blockers, options
```

---

## Scripts

All scripts output JSON summaries to stdout, full logs to files.

| Script | Purpose |
|--------|---------|
| `run-tests.sh [path]` | Auto-detects runner (pytest/jest/go/cargo), returns pass/fail JSON |
| `run-quality.sh [path]` | Runs ruff + bandit + pyright, returns lint/security/types JSON |
| `run-command.sh -- <cmd>` | Wraps verbose commands, keeps context clean |
| `analyze.py --mode summary [path]` | Codebase stats, deps, flags (context-friendly) |

Options: `--log-dir DIR` for organized logs, `--runner RUNNER` to force test runner.
