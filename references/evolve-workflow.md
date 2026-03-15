# Evolve Workflow

Turn the skill's own traces into improvement signals. This is meta-prompting: the skill improves itself using the same structured process it uses to build software.

> **Core principle:** Self-improvement quality = trace quality. Every contract changelog, test name, quality report, and adversarial finding is a signal. Poor traces → blind evolution. Rich traces → targeted evolution.

---

## When to Evolve

| Signal | Action |
|--------|--------|
| User says "evolve", "meta", "improve the skill" | Run full evolve cycle |
| After 5+ build sessions on different projects | Suggest evolve (enough data to find patterns) |
| Repeated failure pattern across sessions | Targeted evolve on that specific phase |
| After significant skill changes (like adding adversarial review) | Validation evolve (does the change work?) |

**When NOT to evolve:** After a single session (not enough signal), mid-build (finish first), when traces are sparse (nothing to learn from).

---

## Phase 1: Harvest

Collect all traces since the last evolution (or since a given date/commit).

### Trace Sources

| Source | What to extract | How |
|--------|----------------|-----|
| **Session docs** | `docs/dev/*/success-criteria.md` | Success criteria patterns, what gets defined well vs poorly |
| **Contract changelogs** | `## Contract Changelog` sections | What contracts changed mid-build and why — these are specification failures |
| **Quality reports** | `docs/dev/*/logs/quality.log` | Recurring lint/security/type patterns across projects |
| **Adversarial findings** | Adversarial review outputs | What logic bugs get through to the final gate |
| **Test results** | `docs/dev/*/logs/tests.log` | Test failure patterns, what breaks repeatedly |
| **Failure escalations** | Session notes where subagents hit attempt 3 | What causes the skill to get stuck |
| **Git history of skill files** | `git log --since="LAST_EVOLVE_DATE" -- path/to/skill/` | What was manually changed outside evolve cycles |
| **Session index** | `docs/dev/session-index.md` | Completion rates, partial/abandoned sessions |

### Harvest Command

The coordinator collects traces by spawning a harvest subagent:

```
Collect all development traces from [project(s)] since [date/commit].

For each session folder in docs/dev/:
1. Read success-criteria.md — note any Contract Changelog entries
2. Read logs/ — extract quality.log JSON summaries and test results
3. Read handoffs/ — note Key Decisions and escalations
4. Check session-index.md for status (Complete/Partial/Abandoned)

For skill file changes:
1. Run: git log --since="[date]" --stat -- [skill-path]
2. For each commit, read the diff

Output: A structured harvest report saved to docs/dev/[session]/harvest.md
with sections: Contract Drift, Quality Patterns, Logic Findings,
Failure Modes, Process Friction.
```

---

## Phase 2: Pattern

Classify harvested signals into actionable categories.

### Pattern Categories

| Category | Question | Example finding |
|----------|----------|-----------------|
| **Specification gaps** | What contracts changed mid-build? | "API response format changed 3/5 times → success criteria under-specify response shape" |
| **Late catches** | What did adversarial review find that verification missed? | "Null handling bugs caught at adversarial stage in 4/5 sessions → test subagent prompt doesn't emphasize null paths" |
| **Recurring quality issues** | What ruff/bandit patterns repeat? | "B105 (hardcoded passwords) in 3 projects → implementation prompt should mention secrets handling" |
| **Process friction** | What ceremony gets skipped or feels heavy? | "Contract changelogs empty in 80% of sessions → either contracts don't change (good) or changes aren't logged (bad)" |
| **Stuck patterns** | Where do subagents hit attempt 3? | "Implementation subagent stuck on async patterns → needs research subagent trigger for concurrency" |
| **Test gaps** | What breaks in production that tests didn't catch? | "Edge cases with empty inputs missed in 3 projects → test prompt should mandate empty/null/boundary inputs" |

### Pattern Analysis Prompt

```
Given this harvest report, identify patterns:

1. SPECIFICATION PATTERNS — Do contract changelogs show systematic gaps
   in how we define success criteria or contracts?
2. DETECTION PATTERNS — Are certain bug types consistently caught late
   (adversarial) vs early (tests/quality)? What should move earlier?
3. PROCESS PATTERNS — Is ceremony being skipped? Is it because it's
   unnecessary (Wu Wei: drop it) or because it's poorly prompted?
4. FAILURE PATTERNS — Do stuck/escalated sessions share common traits?

For each pattern:
  - Evidence: [specific traces]
  - Frequency: [how often across sessions]
  - Impact: [what goes wrong when this pattern occurs]
  - Root cause: [why does this happen — is it a prompt gap, a missing
    step, a wrong assumption?]

Rank by Impact ÷ Effort to fix.
```

---

## Phase 3: Hypothesize

For each ranked pattern, propose a specific modification.

### Hypothesis Format

```markdown
### Hypothesis: [short name]

**Pattern:** [what was observed]
**Root cause:** [why it happens]
**Proposed change:** [specific modification to skill file(s)]
**Target file(s):** [exact file paths]
**Predicted effect:** [what should improve, measurably]
**Risk:** [what could get worse]
**Validation:** [how to tell if it worked — what trace to look for next cycle]
```

### Rules

1. **One change per hypothesis** — no bundled modifications
2. **Specific, not vague** — "Add 'test null/empty inputs for every parameter' to test subagent prompt" not "improve test coverage"
3. **Predict the effect** — if you can't state what trace will change, the hypothesis is too vague
4. **Include rollback criteria** — "If after 3 sessions [bad outcome], revert"
5. **Wu Wei filter** — does this pattern actually cause problems, or is it theoretical purity?

### User Approval Gate

**STOP.** Present hypotheses ranked by Impact ÷ Effort. User approves which ones to apply. Never self-modify without approval.

---

## Phase 4: Apply

Apply approved modifications to skill files. This uses the skill's own build process:

1. **Success criteria** — For each hypothesis, define "done when" based on the predicted effect
2. **Edit skill files** — Modify prompts, workflows, conventions per the approved hypotheses
3. **Quality check** — Run the skill's own self-checks on modified files
4. **Commit** — Each hypothesis gets its own commit with the hypothesis as the commit message body

### What Can Be Modified

| Skill component | Evolve can change | Example |
|----------------|-------------------|---------|
| Subagent prompts | Yes | Add "test null inputs" to test subagent constraints |
| Mode detection triggers | Yes | Add new trigger words |
| Process weight thresholds | Yes | Change when medium → heavy triggers |
| Workflow phases | With user approval | Add/remove/reorder steps |
| Integrity constraints | **Never** | These are foundational — user modifies directly |
| Wu Wei filter | **Never** | Philosophy doesn't optimize, it guides |
| Scripts (run-tests.sh etc.) | With user approval | Functional changes need explicit approval |

---

## Phase 5: Validate

Run the evolved skill on a real project and compare traces.

### Validation Approaches

| Approach | When | How |
|----------|------|-----|
| **Next natural project** | Default — evolve, then use normally | Compare traces from next 3-5 sessions against harvest baseline |
| **Replay** | When a specific failure pattern needs validation | Re-run a previous session's task with evolved skill, compare outcomes |
| **Canary** | For risky changes | Apply to one project first, hold others on previous version |

### Comparison Metrics

Look for these in post-evolution traces:

- **Contract changelog entries** — fewer = better specification upfront
- **Adversarial CRITICAL findings** — fewer = better implementation quality
- **Quality scan issues** — trending down across sessions
- **Failure escalations** — fewer stuck subagents
- **Session completion rate** — more Complete, fewer Partial/Abandoned
- **New problems** — did the change introduce friction or regressions?

### Evolution Log

Maintain `docs/dev/evolution-log.md` (or in the skill repo itself):

```markdown
## Evolution [N] — [date]

### Harvest scope
- Projects: [list]
- Sessions analyzed: [count]
- Date range: [from] → [to]

### Patterns found
1. [pattern] — Impact: [H/M/L], Effort: [H/M/L]
2. ...

### Hypotheses applied
1. [hypothesis name] — [target file] — [status: applied/deferred/rejected]
2. ...

### Validation results (filled after 3-5 sessions)
- [metric]: [before] → [after]
- Verdict: [keep/revert/refine]
```

---

## The DSPy Parallel

What DSPy does algorithmically, Evolve does through structured analysis:

| DSPy | Evolve |
|------|--------|
| Treats LM calls as optimizable modules | Treats subagent prompts as optimizable modules |
| Measures outputs against a metric | Measures traces against pattern categories |
| Iteratively refines prompts | Iteratively refines prompts via harvest → pattern → hypothesize → apply |
| Automated optimization loop | Semi-automated with user approval gate |
| Needs labeled examples | Uses session traces as examples |

The key difference: DSPy optimizes for a single metric. Evolve optimizes for multiple signals (specification quality, detection timing, process efficiency, failure reduction). This is harder to automate fully but produces more nuanced improvements.

Future possibility: if trace data accumulates enough structure (JSON quality reports, structured adversarial findings), a scoring function could be built to close the loop further.

---

## Quick Start

```
"Evolve the skill based on [project] sessions"
"Meta: analyze traces from the last 5 builds"
"Self-improve: what patterns do you see in my recent sessions?"
```
