# Sprint Mode

Execute multiple items as coordinated waves. YOU are the coordinator.

---

## Phase 1: Classify Items

For each item, assign a work type:

| Type | Description | Execution | Example |
|------|-------------|-----------|---------|
| `mechanical` | Repetitive pattern across many files | Structured edit plan, no reasoning agent | Dark mode classes, rename, i18n |
| `surgical` | Targeted change, clear scope | Coordinator-direct | Config fix, dead code removal, small tweak |
| `constructive` | New logic or behavior | Build mode pipeline (TDD when Medium+) | New endpoint, new component, new service |
| `exploratory` | Unknown scope, needs investigation | Assess or Research first | "Make it faster", "fix the flaky test" |

**Mechanical vs Constructive:** If you can predict the exact change for every file without reading it, it's mechanical. If each file needs different reasoning, it's constructive.

---

## Phase 2: Wave Planning

Group items into waves by dependency:

1. **Dependencies first** — Items that unblock others go in earlier waves
2. **Parallel within waves** — Independent items in the same wave execute simultaneously
3. **Shared files** — Items touching the same files go in the same wave or sequential waves (avoid merge conflicts)
4. **Assessment before execution** — If an assessment feeds implementation, it's Wave 0

Output a dependency graph:
```
Wave 0: [assessment, setup] — no deps
Wave 1: [item-a, item-b] — parallel, different files
Wave 2: [item-c] — depends on item-a (shared file)
```

---

## Phase 3: Execute

### Mechanical Items

See `references/subagent-briefs.md` → Mechanical Edit Pattern.

1. Read 2-3 representative files to confirm the pattern
2. Generate edit list: `[{file, old, new}, ...]`
3. Apply via Edit tool (use `replace_all` where safe)
4. Verify with build/lint

**Token budget:** ~1K per file (read + edit). 20 files = ~20K tokens, not 100K+.

**Teach the pattern once.** Before fanning out, emit a short tagged block (`**Pattern:**`) explaining what the mechanical change *is*, why this codebase has it, and what would break with the naive alternative. One concept, 3–5 sentences. Per `references/pushback-and-teach.md` — the user should absorb the pattern, not just watch 40 files change.

### Surgical Items

Coordinator works directly. Read the file, make the change, verify.

### Constructive Items

Follow Build mode (`modes/build.md`). For each item:
1. Classify weight (Light/Medium/Heavy)
2. Apply TDD decision heuristic (see Build mode)
3. Use subagents when the item benefits from parallelism or isolation
4. Run planned gates (adversarial, verification)

### Exploratory Items

Run Assess or Research first. Reclassify as mechanical/surgical/constructive after investigation.

---

## Phase 4: Verify Per Wave

After each wave completes:
1. **Backend:** Run test suite
2. **Frontend:** Run build
3. **Both:** Verify no regressions from parallel changes
4. **Test-health gate:** Any red test — new or pre-existing — must be triaged: fix / quarantine (skip or xfail with reason + follow-up task) / delete. See Build mode Phase 4 for the full rubric. Pre-existing failures are test bit-rot; leaving them red is how they accumulate into "5 broken tests nobody noticed for weeks."

Do not start the next wave until the current wave verifies clean.

---

## Phase 5: Gate Enforcement

If the sprint plan specifies gates (adversarial review, test validation, verification) for an item, they are NOT optional during execution.

Before marking any item complete:
1. Check what gates were planned for this item
2. Execute each planned gate
3. If skipping a gate: state the reason explicitly

```
"Skipping adversarial: surgical change, 3 lines modified in config"  ← valid
(silence)                                                              ← NOT valid
```

The coordinator must not skip gates silently. Planned gates are promises to the user.

---

## Sprint Tracker

Use TaskCreate/TaskUpdate to track items. Each item gets a task with:
- Work type tag (mechanical/surgical/constructive/exploratory)
- Wave assignment
- Planned gates
- Status progression: pending → in_progress → gates → completed

Report progress at natural milestones (wave completion), not after every edit.
