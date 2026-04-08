# Train Mode

Iterative ML training loops — finetuning, architecture experiments, hyperparameter search. Unlike Build mode (test → implement → verify), Train mode follows an experiment loop where success is measured by metrics, not binary tests.

Read `references/ml-heuristics.md` for problem reframing and architecture decision heuristics.

---

## Phase 1: Define Convergence Criteria

Before any training, define what "done" looks like:

```markdown
## Convergence Criteria
- Primary: [metric] [operator] [threshold] (e.g., mAP@50 > 0.85)
- Secondary: [metric] [operator] [threshold] (e.g., inference latency < 50ms)
- Stop condition: [when to stop iterating] (e.g., 3 consecutive experiments with <1% improvement)
```

If you can't define convergence criteria, you're not ready to train — go to Design mode first.

---

## Phase 2: Validate Data

Before spending compute, verify the data is sound:

- [ ] Class distribution — are classes balanced? If not, is that intentional?
- [ ] Label quality — sample 20-50 items and manually verify labels
- [ ] Train/val/test splits — no data leakage between splits
- [ ] Data pipeline — does loading, augmentation, preprocessing produce expected output?
- [ ] Edge cases — what does the model see for ambiguous/hard examples?

If data pipeline engineering is needed (ingestion, cleaning, transformation), switch to **Build mode** for that work, then return to Train mode.

---

## Phase 3: Baseline

Establish baseline with minimal configuration:
- Pretrained model, default hyperparameters, no augmentation
- Record all metrics in experiment log
- This is experiment #1 — every future experiment is measured against it

---

## Phase 4: Experiment Loop

```
Read experiment-log.md → Change ONE variable → Train → Evaluate → Record → Decide
```

**Rules:**
1. **One variable per experiment** — changing lr AND augmentation AND architecture means you can't attribute the result
2. **Read the log first** — always, every time. This survives context compression.
3. **Record before deciding** — write the result before choosing the next experiment. Prevents confirmation bias.
4. **Stop when criteria met OR diminishing returns** — don't chase the last 0.1% unless the business requires it

**Typical experiment order** (high-to-low impact):
1. Architecture / model selection
2. Data augmentation strategy
3. Learning rate and schedule
4. Batch size
5. Regularization (dropout, weight decay)
6. Fine-grained hyperparameters

---

## Phase 5: Evaluate & Handoff

When convergence criteria are met:
- Run final evaluation on held-out test set (not val set)
- Profile inference performance (latency, throughput, memory)
- Export model (see `references/ml-heuristics.md` Deployment section)
- Record final results in experiment log

**Handoff to Build mode** for: inference engine, API wrapper, deployment pipeline, monitoring.
**Handoff to Analyze mode** for: "why do certain classes underperform?", error analysis, failure mode investigation.

---

## Experiment Log

Maintain an append-only `experiment-log.md` in project root. This survives context compression and prevents retrying dead ends.

### Format

```markdown
# Experiment Log

## Goal
[One sentence: what we're optimizing for]

## Current Best
| Metric | Value | Config | Checkpoint |
|--------|-------|--------|------------|
| [e.g. mAP@50] | [value] | [key hyperparams] | [path/epoch] |

## Log

### Exp [N] — [timestamp]
- **Changed:** [what was different from previous]
- **Result:** [metrics]
- **Verdict:** [better/worse/inconclusive — why]
- **Next:** [what to try based on this result]
```

### Rules

1. **Always read the log before starting a new experiment** — this is your memory across context compressions
2. **Update "Current Best" immediately** when a new best is found
3. **Record failures** — "tried X, got worse because Y" prevents retrying dead ends
4. **Keep entries terse** — this file will be read many times

---

## Key Differences from Build Mode

| Build Mode | Train Mode |
|-----------|------------|
| Success = tests pass (binary) | Success = metrics meet criteria (continuous) |
| Test → implement → verify (linear) | Experiment → evaluate → adjust (loop) |
| Subagents for separation | Coordinator runs directly (training is sequential) |
| Contract changelog for changes | Experiment log for iterations |
| Adversarial review at end | Analyze mode for result investigation |

Train mode chains into: **Build** (inference engine, deployment pipeline), **Analyze** (why are results bad?), or more **Train** (next experiment).
