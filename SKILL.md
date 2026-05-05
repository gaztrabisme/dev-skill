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
- **Challenge before execute.** When a request is vague, business-level, or hand-waves over tradeoffs, push back and surface the decisions. Silent competence is a failure mode — the user is learning the stack *through* this work and silent wins teach nothing. See `references/pushback-and-teach.md`.

### Wu Wei Filter

```
Is this actually causing problems?
  - Blocking other work?  - Causing bugs?  - Making onboarding hard?
  - Creating maintenance burden?  - Slowing development?

YES → Keep (real issue)    NO → Drop (theoretical purity)
Priority = Impact ÷ Effort
```

### Engineering Style

Write code that solves your specific problem with standard library primitives, and stop.

1. **One file = one concern, ≤120 lines of logic.** If you need to scroll, you've overscoped the file. Split by responsibility, not by abstraction layer.
2. **Standard library over wrappers.** `nn.CrossEntropyLoss` > custom loss library. `torchvision.transforms` > albumentations. `torchvision.models` > timm. Use the wrapper only if you need something it uniquely provides.
3. **No ABC until you have two implementations.** One model = one class. No interface, no factory, no registry until the second variant arrives. When it does, extract the interface from the working code — don't design it upfront.
4. **Visible control flow.** If you can't see the core logic (forward pass, training loop, data pipeline) in one screen, you've over-abstracted. Callbacks, plugins, and hook systems hide control flow — use them only when the framework demands it.
5. **Single-file tools with zero deps.** If a human needs to use it (labeling tool, review tool, visualizer), make it one file, trivially runnable. No build steps, no servers, no package managers.
6. **Metrics, losses, and data loading are just code.** If your metric fits in 40 lines of tensor ops, don't import a library. If your dataset is images + JSON, write a 80-line `Dataset` subclass. Libraries add indirection, version coupling, and edge cases you'll debug longer than writing it yourself.
7. **Dependencies are liabilities.** Every external package can break between runs, add install friction, bloat containers, and create version conflicts. The bar for adding one: "Does this save more debugging time than it will eventually cost?"

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

## Pushback and Teach

On first entry to any mode, also read `references/pushback-and-teach.md`. It defines when to challenge vague instructions, when to surface concept gaps inline, and how to tag teaching moments so the user recognizes them. Design mode enforces the pushback gate hardest; other modes apply it lighter but still narrate the WHY in final reports.

---

## Mode Detection

| Trigger | Mode | Action |
|---------|------|--------|
| "I have an idea", "architect", "design", "spec", "help me plan" | **Design** | Read `modes/design.md` |
| "Build", "add feature", "fix bug", "implement", "create" | **Build** | Read `modes/build.md` |
| Multiple items, "sprint", "batch", "execute plan", "execute these" | **Sprint** | Read `modes/sprint.md` |
| "Plan implementation for N items" | **Design → Sprint** | Design first, then Sprint for execution |
| "Assess", "audit", "review", "refactor", "code health", "cleanup" | **Assess** | Read `modes/assess.md` |
| "Analyze", "root cause", "why does X fail", "evaluate results" | **Analyze** | Read `modes/assess.md` (Analyze section) |
| Assessment findings → "harden", "fix findings" | **Harden** | Build mode with assessment findings as input |
| "Train", "finetune", "experiment", "hyperparameter", "evaluate model" | **Train** | Read `modes/train.md` |
| "Ingest", "convert", "prepare data", "wire up", "configure" | **Wire/Prep** | Coordinator works directly, no subagents |
| "Evolve", "meta", "improve the skill", "self-improve" | **Evolve** | Read `modes/evolve.md` |

### Proactive Detection

When the user's task matches a mode trigger, invoke the appropriate mode WITHOUT requiring explicit `/dev` invocation. The skill should activate when:
- The task involves building, fixing, or adding features (→ Build)
- The task involves reviewing, auditing, or cleaning code (→ Assess)
- The task involves planning architecture or specs (→ Design)
- The task involves multiple deliverables or a backlog (→ Design → Sprint)
- The task involves training or experimenting (→ Train)

Do not wait for the user to say "/dev" — match on intent.

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
- **Test-health:** Does the suite have zero unexplained red? Pre-existing failures are test bit-rot — they must be triaged (fix / quarantine with reason + task / delete), not silently left red. See Build mode Phase 4.
- **Signature changes:** When a function's shape changed, were all callers — including test mocks — grep'd and updated?
- Does every success criterion have evidence?
- For ML work: is the experiment log up to date?
- Was the project wiki updated with session findings?
