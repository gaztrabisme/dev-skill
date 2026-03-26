# Work Tracking

Persistent work graph that survives context switches across sessions. Lives at `.tracks/` in the project root.

---

## Structure

```
.tracks/
├── index.md          # Auto-generated status table (Claude reads on entry)
├── map.html          # Auto-generated visual graph (open in browser)
└── nodes/
    ├── eda-exploration.md
    ├── synth-pipeline.md
    └── backend-wiring.md
```

- **index.md** and **map.html** are generated artifacts. Do not edit them directly.
- **nodes/*.md** are the source of truth. Claude reads and writes these.

---

## Node File Format

```markdown
---
id: synth-pipeline
title: Synthetic Data Augmentation Pipeline
status: active
created: 2026-03-27
updated: 2026-03-27
depends: [eda-exploration]
---

## Objective
One-sentence description of what this workstream achieves.

## Ideas
- [ ] First hypothesis to test
- [ ] Second hypothesis to test
- [x] Third hypothesis — tested, result was X (YYYY-MM-DD)

## Breadcrumbs
- **YYYY-MM-DD HH:MM** — What was tried, what happened, what was learned.
- **YYYY-MM-DD HH:MM** — Another significant event.

## Next
- Concrete next step when returning to this workstream.
- Second step if applicable.
```

### Frontmatter Fields

| Field | Required | Values |
|-------|----------|--------|
| `id` | Yes | kebab-case, unique across nodes |
| `title` | Yes | Human-readable name |
| `status` | Yes | `active`, `paused`, `blocked`, `done` |
| `created` | Yes | YYYY-MM-DD |
| `updated` | Yes | YYYY-MM-DD (update on every edit) |
| `depends` | No | List of node IDs this workstream depends on |

### Status Transitions

```
          ┌─────────┐
    ┌────►│  paused  │◄────┐
    │     └────┬────┘     │
    │          │          │
    │     ┌────▼────┐     │
    └─────│  active  │─────┘
          └────┬────┘
               │
          ┌────▼────┐
          │  done    │
          └─────────┘

Any status can transition to "blocked" and back.
```

- **active** → currently being worked on. Only 1-2 nodes should be active at a time.
- **paused** → has work remaining but not the current focus.
- **blocked** → cannot proceed until a dependency is resolved.
- **done** → completed. Keep for graph context; archive later if graph gets large.

---

## Granularity Guidelines

A node should represent a **workstream**, not a task. Think "week of work" not "afternoon of work."

**Too granular** (don't do this):
```
fix-tokenizer-bug.md
add-logging.md
update-config.md
```

**Right level**:
```
data-pipeline.md          # Covers ingestion, cleaning, tokenization
model-training.md         # Covers architecture, hyperparams, training loop
api-integration.md        # Covers endpoints, auth, deployment
```

If a node gets too large (>50 breadcrumbs), split it into sub-workstreams.

---

## Breadcrumb Conventions

Breadcrumbs are the paper trail. Log these:

- **Failed attempts** — "Tried X, didn't work because Y" (prevents re-trying)
- **Key decisions** — "Chose A over B because C"
- **Surprising findings** — "Data is 40% duplicates, need dedup step"
- **Metric changes** — "Accuracy went from 0.72 to 0.81 after feature X"

Do NOT log:
- Routine operations ("ran tests, they passed")
- Implementation details that are visible in the code
- Verbose debug output

Format: `- **YYYY-MM-DD HH:MM** — <what happened>`

---

## Ideas Checklist

The Ideas section tracks hypotheses and approaches to test. This is the queue that prevents "I forgot to try X."

- `- [ ] Hypothesis` — untested
- `- [x] Hypothesis — result summary (YYYY-MM-DD)` — tested

When starting work on a node, check Ideas first for queued items.

---

## Regenerating the Graph

After editing any node file:

```bash
python3 {baseDir}/scripts/generate-map.py <project-root>
```

This updates both `index.md` and `map.html`. Open `map.html` in any browser to see the visual graph.

To initialize tracking in a new project:

```bash
python3 {baseDir}/scripts/generate-map.py --init <project-root>
```

---

## Integration with Dev Modes

Tracking wraps all dev modes. It's not a separate mode — it's a layer.

| Phase | What Claude Does |
|-------|-----------------|
| **Entry** | Read `index.md`. Identify relevant node. Read it. Show user: status, last breadcrumbs, queued ideas. |
| **During** | Log breadcrumbs for significant findings. Update ideas as tested. |
| **Exit** | Update node: status, breadcrumbs, next steps, `updated` date. Regenerate graph. |

The overhead is minimal: ~200 tokens to read index, ~300 tokens to read a node. The value compounds across sessions.
