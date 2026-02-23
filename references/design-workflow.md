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

#### Subagent Types

| Type | When | `subagent_type` | Key prompt elements |
|------|------|-----------------|---------------------|
| **Technical** | Evaluating frameworks, libraries, APIs | `general-purpose` | Mainstream options, tradeoffs, production patterns. Focus on proven, maintained solutions. |
| **Domain** | Unfamiliar problem space or industry | `general-purpose` | Terminology, workflows, regulations, pain points. Cite sources for regulatory claims. |
| **Competitive** | Building in a space with existing solutions | `general-purpose` | Competitors, feature gaps, differentiation. If existing solution handles 80%+ → loop back to user. |
| **Local Context** | Existing codebase needs understanding | `Explore` | Structure, conventions, reusable components, integration points. Match existing style. |
| **Feasibility** | Uncertain if achievable given constraints | `general-purpose` | Verdict (Yes/Caveats/Uncertain/No), evidence, blockers, alternatives. |

All research subagents: save output to `docs/dev/[session]/research/`. Present options with tradeoffs — do NOT make final decisions.

**Agent teams for research** (when `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is enabled): If research needs multiple angles that should *challenge each other's conclusions* — e.g., evaluating competing architectures where pros/cons interact — use agent teams instead of parallel subagents. Teammates can message each other to reconcile conflicting findings before reporting back. Default to subagents; escalate to teams only when cross-challenge matters.

### Coordination Rules

1. **Parallel when independent** — launch multiple researchers simultaneously
2. **Sequential when dependent** — domain understanding may redirect technical research
3. **Loop back on pivots** — any finding that changes direction goes to user first
4. **Compress before integrating** — key facts, not narratives
5. **TL;DR to coordinator** — research subagents write full docs to disk but return a 10-20 line summary (decisions + key numbers) as their primary output. The coordinator ingests the summary, not raw content.

### The Loop-Back Rule

If research reveals insights that could change direction: STOP → SURFACE to user → DISCUSS → DECIDE together.

Triggers: better alternative found, significant constraint, compliance requirement, scope much larger than expected, user assumption contradicted.

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

When complete: summarize what was produced, confirm with user, transition to Build mode using design artifacts as input.
