# Assessment Workflow

Assess codebase health and generate refactoring plans following wu wei — minimum intervention, maximum clarity. Loaded in **Assess** and **Analyze** modes.

---

## Severity Tiers

| Tier | Behavior | User Action |
|------|----------|-------------|
| **CRITICAL** | Blocks progression (security, contract violations, mocked production code) | Must fix before proceeding |
| **QUALITY** | Advisory (AI slop, dead code, code smells, dependency issues) | User decides: fix now, defer, or accept |

---

## Phase 1: Scope & Filter (Wu Wei Entry Point)

**Start by filtering, not scanning.** Ask: what hurts? What did the user ask about?

```
User: "Refactor the backend"     -> scope = ./backend/
User: "Assess this codebase"     -> scope = ./
User: "Clean up the API layer"   -> scope = ./src/api/
```

Apply the Wu Wei filter:
```
Is this actually causing problems?
  - Blocking other work?  - Causing bugs?  - Making onboarding hard?
  - Creating maintenance burden?  - Slowing development?

YES -> Investigate    NO -> Skip
```

**Size check**: Small codebase (< 50 files)? Read directly — skip scripts. Large codebase? Scope to affected directories first.

---

## Phase 2: Scan

Run the analysis script. Start with `summary` for a context-friendly overview, then drill into `full` only if needed:
```bash
# Context-friendly overview (flags and actionable items only)
python3 {baseDir}/scripts/analyze.py --mode summary [scope]

# Full detail when investigating specific findings (redirect to file, read on-demand)
python3 {baseDir}/scripts/analyze.py --mode full [scope] > docs/dev/[session]/analysis-full.json
```

Other modes: `--mode stats` (file metrics only), `--mode deps` (dependency graph only).

**Important**: Script output is a guide, not ground truth. Dynamic imports, plugin systems, and external consumers are invisible to static analysis.

### Assessment Rules

| Category | Target | Flag |
|----------|--------|------|
| File size | < 500 lines | Any file > 500 lines (except generated/data files) |
| Configuration | One high-level location | Hardcoded URLs, thresholds, credentials scattered in code |
| Separation | One clear responsibility per file | God classes, mixed concerns |
| Dependencies | Clean graph, no cycles | Circular deps, hotspots |
| Dead code | All code reachable and used | Orphan files, unused functions (flag as "candidates") |

### Subagent Deployment (Large Codebases)

For 3+ modules: spawn parallel assessment subagents using Task tool with `subagent_type="general-purpose"`. One subagent per module, no file overlap. Aggregate findings after all complete.

---

## Phase 3: Present

Order findings by **Impact / Effort**:
- High impact, low effort → Do first (Quick Wins)
- High impact, high effort → Plan carefully (Structural)
- Low impact, low effort → Do if time permits
- Low impact, high effort → Don't do it

Structure the report as prose:
- **Executive Summary**: 2-3 sentences — overall health, biggest issue, recommended action
- **What's Working Well**: Good patterns to preserve
- **What Hurts**: Findings ordered by priority, with file locations and evidence
- **What to Skip**: Things flagged but filtered by Wu Wei, with reasoning

Save to `docs/dev/NNN-assessment-[scope]/report.md`.

---

## Phase 4: Act (If User Approves)

One change at a time. Verify after each (tests pass, no runtime errors). User controls progression.

### Feeding into Harden Mode

Group findings by severity tier → create phased success criteria → use test-first subagents (Build mode) to fix each tier → full regression suite after each tier.

---

## Analyze Mode

For data-driven investigation: "why do results look like this?", "root cause analysis", "evaluate experiment results."

This mode asks "what's wrong with the *results*?" vs Assess which asks "what's wrong with the *code*?"

### Pattern (from session 004)

1. **Root Cause Taxonomy** — Categorize failure modes. What types of errors exist? What's their distribution?
2. **Causal Model** — Map cause → effect chains. What produces each failure type?
3. **Impact/Effort Ranking** — For each root cause: how much would fixing it improve results vs how hard is the fix?
4. **Experiment Design** — Define specific changes to test, with before/after measurement criteria
5. **Projected Impact Matrix** — Expected improvement per intervention, ordered by cumulative gain

### Output

Save to `docs/dev/NNN-analysis-[topic]/`:
- `success-criteria.md` — what the analysis should answer
- `analysis.md` — findings with taxonomy, causal model, rankings
- `eval-results.md` — before/after data if experiments were run

Analyze mode often leads to Build mode (implement the top-ranked fix) or further Analyze (validate the fix worked).
