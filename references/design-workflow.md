# Design Workflow

Transform ideas into development-ready specifications through iterative research and discussion. Loaded in **Design mode**.

---

## Phase 1: Clarify Intent

Understand what the user wants to build, why, and what constraints exist.

| Category | Questions |
|----------|-----------|
| **What** | What problem does this solve? What does success look like? |
| **Who** | Who are the users? What's their context? |
| **Why** | Why build this? Why now? What happens if we don't? |
| **Constraints** | Timeline? Budget? Tech preferences? Team size? |
| **Scope** | MVP vs full vision? What's explicitly out of scope? |

### Rules

1. **Don't interrogate** — Weave questions naturally into discussion
2. **Summarize understanding** — "So you want X that does Y for Z, correct?"
3. **Surface assumptions** — "I'm assuming [X], is that right?"
4. **Identify unknowns** — "We'll need to research [Y] to answer this"

Output: shared mental model of the project. No documents yet.

---

## Phase 2: Research

### Calibrate Scope First

| Signal | Research Depth |
|--------|----------------|
| Clear requirements, familiar domain | Minimal (1-2 searches) |
| Clear requirements, unfamiliar domain | Domain-focused |
| Unclear requirements, familiar domain | Clarification-focused |
| Unclear requirements, unfamiliar domain | Full research |

### Deploy Research Team

YOU are the coordinator. Spawn research subagents using the Task tool for independent topics. Do NOT do all research yourself — parallel subagents save context and time.

**Parallel** when topics are independent. **Sequential** when findings would redirect later research.

Each subagent gets a specific question (not "research everything about X"), saves findings to `docs/dev/research/`, and presents options with tradeoffs — no final decisions. Use `subagent_type: general-purpose` (or `Explore` for existing codebase investigation).

### The Loop-Back Rule

If research reveals something that could change direction (better alternative, significant constraint, scope much larger than expected): STOP and surface to user before continuing.

---

## Phase 3: Document & Handoff

### Only When Direction Is Stable

Scale documentation to project complexity:

| Project Scale | Documentation |
|--------------|---------------|
| Script/CLI tool | CLAUDE.md only |
| Single-purpose service | CLAUDE.md + data-model |
| Multi-component system | Full set (architecture, tech-stack, data-model, api-design) |

CLAUDE.md must include: Overview (the "why"), Quick Start (3-5 commands), Architecture (the "what"), Key Decisions (the "why this way"), Constraints (the "what not").

---

## Phase 4: Spec Adversarial Review

**Before handoff to Build mode**, the spec gets a cold review. Same principle as code adversarial review — a subagent reads the spec with no context about the discussion that produced it.

**Spawn:** Agent tool with `subagent_type: general-purpose`

**Provide:** ONLY the spec documents (success criteria, contracts, CLAUDE.md, data models). Do NOT provide conversation context, rationale, or "why we chose X."

**Prompt:**
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

**After review:**
- **CRITICAL findings** → must resolve before handoff (update spec, discuss with user)
- **WARNING findings** → present to user for decision (fix now or accept risk)
- **ADVISORY findings** → note in handoff, build team is aware
- If 3+ CRITICAL → spec needs another iteration, not patches

**Skip for:** Light builds (bug fixes, config, wiring) — these go straight from scope to build.

---

## Phase 5: Handoff

### Planning Exit Gate

Planning is done when ALL of these are true:

- [ ] Every success criterion is **binary and testable** (not "works well" but "returns 200 with JSON array")
- [ ] You can **name the remaining unknowns** and they're acceptable risks, not blockers
- [ ] Spec adversarial review has **no unresolved CRITICAL findings**
- [ ] A stranger could read the spec and **build the right thing** without asking you questions

The messy discussion that gets here is not a bug — it's the work. The exit gate is what matters, not the path.

When complete: summarize what was produced, confirm with user, transition to Build mode using design artifacts as input.
