# Design Mode

Transform ideas into development-ready specifications through iterative research and discussion.

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
5. **Challenge vague intent** — Read `references/pushback-and-teach.md`. When the request is business-speak ("add auth", "make it fast", "just like X"), name the concrete forks the request leaves open, present 2–3 options per fork with tradeoffs and a recommendation, and do NOT accept scope until each fork has a concrete answer. Two vague answers in a row → stop and ask for binary, testable criteria.
6. **Teach concept gaps inline** — If the user's framing reveals a missing concept (conflating auth/authz, thinking JWT = session, treating a cache like a DB, etc.), teach the concept in 3–5 sentences with a tagged block (`**Why this matters:**`) before moving on.
7. **ML work: Reframe before solving** — If the task involves ML/CV/NLP, read `references/ml-heuristics.md` and apply the Problem Reframing questions. Challenge the first approach: "Does the spec actually require this, or are we assuming it?" Teaching applies to ML math/intuition too, not just systems work.
8. **Greenfield library research** — If the design pulls in unfamiliar libraries, use `chub search "lib"` → `chub get <id>` for accurate API docs instead of guessing signatures. Annotate discoveries for future sessions.

**Hard gate:** Phase 1 does not exit until every top-level decision has a concrete, testable answer. "It should be fast" is not an answer; "p95 latency under 200ms for reads" is. No proceeding to Phase 2 research until this is true.

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

YOU are the coordinator. Spawn research subagents using the Agent tool for independent topics. Do NOT do all research yourself — parallel subagents save context and time.

**Parallel** when topics are independent. **Sequential** when findings would redirect later research.

Each subagent gets a specific question (not "research everything about X") and presents options with tradeoffs — no final decisions.

**ML work:** Before researching solutions, apply `references/ml-heuristics.md` — Problem Reframing and Architecture Decisions. Often the right research question isn't "which model?" but "what simpler problem does this reduce to?"

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

**Before handoff to Build mode**, the spec gets a cold review. A subagent reads the spec with no context about the discussion that produced it.

Spawn an Agent with `subagent_type: general-purpose`. Provide ONLY the spec documents (success criteria, contracts, CLAUDE.md, data models). Do NOT provide conversation context, rationale, or "why we chose X."

Read `references/subagent-briefs.md` for the spec adversarial review prompt template.

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

When complete: summarize what was produced, confirm with user, transition to Build mode using design artifacts as input.
