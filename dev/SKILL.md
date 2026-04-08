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

## Project Wiki

On first entry to any mode, read `references/wiki-protocol.md` and follow the wiki initialization/update protocol. The wiki is a persistent knowledge base that compounds project understanding across sessions — read it before starting work, update it as you learn.

---

## Mode Detection

| Trigger | Mode | Action |
|---------|------|--------|
| "I have an idea", "architect", "design", "spec", "help me plan" | **Design** | Read `modes/design.md` |
| "Build", "add feature", "fix bug", "implement", "create" | **Build** | Read `modes/build.md` |
| "Assess", "audit", "review", "refactor", "code health", "cleanup" | **Assess** | Read `modes/assess.md` |
| "Analyze", "root cause", "why does X fail", "evaluate results" | **Analyze** | Read `modes/assess.md` (Analyze section) |
| Assessment findings → "harden", "fix findings" | **Harden** | Build mode with assessment findings as input |
| "Train", "finetune", "experiment", "hyperparameter", "evaluate model" | **Train** | Read `modes/train.md` |
| "Ingest", "convert", "prepare data", "wire up", "configure" | **Wire/Prep** | Coordinator works directly, no subagents |
| "Evolve", "meta", "improve the skill", "self-improve" | **Evolve** | Read `modes/evolve.md` |

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

## Available Tools

Use situationally, not by default.

| Tool | When | How |
|------|------|-----|
| **Context Hub** (`chub`) | Greenfield builds, unfamiliar libraries | `chub search "lib"` → `chub get <id>` |
| **GitNexus** (MCP) | Existing codebases — blast radius, call flows, impact analysis | `context`, `impact`, `query`, `detect_changes` |

---

## Limitations

- Cannot guarantee bug-free code — tests reduce bugs, don't eliminate them
- Cannot replace domain expertise — user must validate business logic
- Cannot handle interactive debugging — escalates when stuck
- Does not deploy — builds software, doesn't deploy it

### When NOT to Use
- Exploratory prototyping (use direct coding)
- One-line fixes with obvious solutions
- Pure research without implementation goal

## Self-Checks

- Did mode detection match the task?
- Did process weight match actual complexity (minimum needed)?
- Do all tests pass with real output shown?
- Does every success criterion have evidence?
- For ML work: is the experiment log up to date?
- Was the project wiki updated with session findings?
