# Experiment Loop

Iterative optimization through autonomous experimentation. Derived from Karpathy's autoresearch pattern, generalized beyond ML training.

Works for: model training, hyperparameter sweeps, feature engineering, prompt optimization, config tuning, data pipeline optimization — anything with a numeric score.

---

## Setup

Before the loop starts, define three things:

### 1. Mutable Surface

The file(s) the agent can modify. Everything else is locked.

```
Examples:
- train.py           (model architecture, optimizer, hyperparams)
- config.yaml        (pipeline configuration)
- prompt.txt         (prompt engineering)
- features.py        (feature engineering for tabular data)
- src/               (broader surface for software optimization)
```

Smaller surface = faster convergence. Start with one file.

### 2. Evaluation

The scoring function. **Agent must not be able to modify this.** Keep it in a separate locked file, or use an external metric.

```python
# Examples of fixed evaluations:
val_bpb = evaluate_bpb(model, val_data)     # language model quality
accuracy = evaluate(model, test_set)          # classification
latency_p99 = benchmark(endpoint, n=1000)     # performance
lighthouse_score = run_lighthouse(url)         # web performance
f1 = evaluate_extraction(pipeline, gold_set)  # NLP pipeline
```

Requirements:
- Returns a single scalar (or a primary scalar + secondary for tiebreaking)
- Runs in bounded time (set a budget: 5 min training, 30 sec eval, etc.)
- Deterministic enough to compare across runs

### 3. Baseline

Run the evaluation once before any changes. Record the starting metric. Every experiment is compared against this.

---

## The Loop

```
LOOP:
  1. git status — understand current state
  2. Pick an idea — based on prior results, domain knowledge, or creative exploration
  3. Edit the mutable surface — implement the idea
  4. git commit -m "experiment: <hypothesis>"
  5. Run evaluation — redirect output: command > run.log 2>&1
  6. Extract metric — grep/parse only the score from the log
  7. Log to results — append to results.tsv or similar (experiment, metric, notes)
  8. Decision:
     - If improved → keep the commit (branch advances)
     - If worse → git reset --hard HEAD~1 (revert to previous best)
     - If crashed → read traceback, attempt fix or skip
  9. CONTINUE — never stop, never ask. Run until interrupted.
```

### Context Protection

Verbose training/eval output destroys agent context. Always:
- Redirect: `command > run.log 2>&1`
- Extract: `grep "^metric:" run.log` or parse specific lines
- Never pipe raw output into the conversation

Use `bash {baseDir}/scripts/run-command.sh --label "exp-N" -- <command>` for structured JSON extraction.

### Idea Generation

When the agent runs low on ideas:

- **Ablation**: Remove a recent change. Did it actually help?
- **Opposites**: If large learning rate helped, try even larger. If regularization helped, try more.
- **Literature**: Search for recent papers/techniques in the domain.
- **Simplification**: Delete code. If the metric holds, the removed code was noise.
- **Combination**: Combine the two best independent improvements.
- **Scale**: Change model size, batch size, sequence length, data volume.

### The Simplicity Criterion

A small improvement that adds 20 lines of hacky code? Probably not worth it.
A small improvement from deleting code? Definitely keep.
Complexity has a cost. Weigh metric improvement against code complexity added.

---

## Variants

### Warm-Start (for training tasks)

Instead of training from scratch each cycle, load the previous best checkpoint and continue. Compounds gains across experiments. Use when: training budget is long (>5 min) and architecture isn't changing.

### Multi-Metric

When one scalar isn't enough (e.g., accuracy AND latency), define a composite:
```
score = accuracy - 0.01 * latency_ms
```
Or use a primary metric with a constraint: "maximize accuracy where latency < 100ms."

### Hardware-Aware

When running on specific hardware (e.g., RTX 5080 16GB), track VRAM usage alongside the metric. An improvement that OOMs in production isn't an improvement.

```
# Extract from log
val_bpb=$(grep "^val_bpb:" run.log | tail -1 | cut -d' ' -f2)
peak_vram=$(grep "^peak_vram_mb:" run.log | tail -1 | cut -d' ' -f2)
```

---

## Results Tracking

Keep a TSV/CSV log (untracked by git — the commits ARE the experiment history):

```
experiment	metric	vram_mb	notes
baseline	1.423	8200	default config
exp-1: larger hidden dim	1.401	9100	+12% params, -1.5% bpb
exp-2: cosine schedule	1.389	9100	significant improvement
exp-3: label smoothing	1.392	9100	slight regression, reverted
```

Or use `results.tsv` and let git commits tell the story.

---

## When to Stop

- Diminishing returns: last 5 experiments all within noise of each other
- Time limit: user specified a budget ("run overnight", "try 20 experiments")
- Metric target: user specified a goal ("get below 1.35 bpb")
- User interrupts

Report: best metric achieved, total experiments run, top 3 improvements, what didn't work.
