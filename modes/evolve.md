# Evolve Mode

Turn the skill's own traces into improvement signals. Meta-prompting: the skill improves itself using the same structured process it uses to build software.

> **Core principle:** Self-improvement quality = trace quality. Every contract changelog, test name, quality report, and adversarial finding is a signal. Poor traces → blind evolution. Rich traces → targeted evolution.

> **Pragmatic default:** Most evolution happens organically — user feedback mid-build, "this is too heavy" corrections, and observing which gates actually catch bugs vs. which get skipped. The formal cycle below is for periodic deep retrospectives (e.g., after 10+ builds on diverse projects) when you want structured pattern-mining. Default to organic: when something feels like theater, trim it; when something catches a real bug, reinforce it.

---

## When to Evolve

| Signal | Action |
|--------|--------|
| User says "evolve", "meta", "improve the skill" | Run full evolve cycle |
| After 5+ builds on different projects | Suggest evolve (enough data to find patterns) |
| Repeated failure pattern across builds | Targeted evolve on that specific phase |
| After significant skill changes | Validation evolve (does the change work?) |
| User says "that was unnecessary" or skips a gate repeatedly | Trim that gate immediately — don't wait for a formal evolve cycle |

**When NOT to evolve:** After a single build (not enough signal), mid-build (finish first), when traces are sparse (nothing to learn from).

---

## Phase 1: Harvest

Collect all traces since the last evolution (or since a given date/commit).

### Trace Sources

| Source | What to extract | How |
|--------|----------------|-----|
| **Git history** | Commits, diffs, commit messages | `git log --since="LAST_EVOLVE_DATE"` across project repos |
| **Contract changelogs** | `## Contract Changelog` sections | What contracts changed mid-build and why — specification failures |
| **Quality reports** | `logs/quality.log` | Recurring lint/security/type patterns |
| **Adversarial findings** | Review outputs in git history | What logic bugs get through to the final gate |
| **Test results** | `logs/tests.log` | Test failure patterns, what breaks repeatedly |
| **Experiment logs** | `experiment-log.md` (ML projects) | What approaches were tried, what worked, what was wasted effort |
| **Failure escalations** | Git history + commit messages | What causes the skill to get stuck |
| **Skill file changes** | `git log -- path/to/skill/` | What was manually changed outside evolve cycles |
| **Wiki pages** | `wiki/` directory | Accumulated project understanding, decisions, patterns |

### Harvest Subagent

Spawn a harvest subagent:
```
Collect all development traces from [project(s)] since [date/commit].

1. Run: git log --since="[date]" --stat for each project
2. Read logs/ directories for quality and test JSON summaries
3. Read experiment-log.md if present (ML projects)
4. Search for Contract Changelog entries in committed files
5. Run: git log --since="[date]" --stat -- [skill-path] for skill changes
6. Read wiki/ directory for accumulated project context

Output: A structured harvest report with sections:
Contract Drift, Quality Patterns, Logic Findings,
Failure Modes, Process Friction.
```

---

## Phase 2: Pattern

Classify harvested signals into actionable categories.

| Category | Question | Example finding |
|----------|----------|-----------------|
| **Specification gaps** | What contracts changed mid-build? | "API response format changed 3/5 times → success criteria under-specify response shape" |
| **Late catches** | What did adversarial review find that verification missed? | "Null handling bugs caught at adversarial stage in 4/5 builds → test subagent prompt doesn't emphasize null paths" |
| **Recurring quality issues** | What ruff/bandit patterns repeat? | "B105 (hardcoded passwords) in 3 projects → implementation prompt should mention secrets handling" |
| **Process friction** | What ceremony gets skipped or feels heavy? | "Contract changelogs empty in 80% of builds → either contracts don't change (good) or changes aren't logged (bad)" |
| **Stuck patterns** | Where do subagents hit attempt 3? | "Implementation subagent stuck on async patterns → needs research subagent trigger for concurrency" |
| **Test gaps** | What breaks in production that tests didn't catch? | "Edge cases with empty inputs missed in 3 projects → test prompt should mandate empty/null/boundary inputs" |

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
4. **Include rollback criteria** — "If after 3 builds [bad outcome], revert"
5. **Wu Wei filter** — does this pattern actually cause problems, or is it theoretical purity?

### User Approval Gate

**STOP.** Present hypotheses ranked by Impact / Effort. User approves which ones to apply. Never self-modify without approval.

---

## Phase 4: Apply

Apply approved modifications using the skill's own build process:

1. **Success criteria** — For each hypothesis, define "done when" based on the predicted effect
2. **Edit skill files** — Modify prompts, workflows, conventions per approved hypotheses
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
| Scripts | With user approval | Functional changes need explicit approval |

---

## Phase 5: Validate

Run the evolved skill on a real project and compare traces.

| Approach | When | How |
|----------|------|-----|
| **Next natural project** | Default | Compare traces from next 3-5 builds against harvest baseline |
| **Replay** | Specific failure pattern | Re-run a previous task with evolved skill, compare outcomes |
| **Canary** | Risky changes | Apply to one project first, hold others on previous version |

### Comparison Metrics

- **Contract changelog entries** — fewer = better specification upfront
- **Adversarial CRITICAL findings** — fewer = better implementation quality
- **Quality scan issues** — trending down across builds
- **Failure escalations** — fewer stuck subagents
- **New problems** — did the change introduce friction or regressions?

### Evolution Log

Maintain in the skill repo:

```markdown
## Evolution [N] — [date]

### Harvest scope
- Projects: [list]
- Builds analyzed: [count]
- Date range: [from] → [to]

### Patterns found
1. [pattern] — Impact: [H/M/L], Effort: [H/M/L]

### Hypotheses applied
1. [hypothesis name] — [target file] — [status: applied/deferred/rejected]

### Validation results (filled after 3-5 builds)
- [metric]: [before] → [after]
- Verdict: [keep/revert/refine]
```
