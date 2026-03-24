# ML Heuristics

Decision heuristics for ML work. Consult during Design mode (problem framing) and Build mode (architecture/deployment decisions). These are forcing questions, not rules — skip what doesn't apply.

---

## Problem Reframing

Before choosing a model or framework, challenge the problem statement itself.

### Forcing Questions

1. **"What does the spec actually say?"** — Read requirements literally. If it says "detect compliance," that's classification, not detection-with-bounding-boxes. Don't add complexity the problem doesn't demand.

2. **"Can I decompose this into solved sub-problems?"** — Chain existing solutions instead of training one model end-to-end. Example: person detection (solved) → crop → classify attributes (simpler problem) instead of multi-class fine-grained object detection (hard problem).

3. **"What's the simplest problem type this reduces to?"** — Detection → classification. Segmentation → detection + mask. Generation → retrieval + ranking. Every reduction in problem complexity is a 10x reduction in data/compute/debugging effort.

4. **"Can I build a labeling pipeline instead of a labeled dataset?"** — Semi-automate with VLMs or existing models producing structured output (JSON captions), then human-correct. This scales; manual labeling doesn't.

---

## Architecture Decisions

### Use Mechanisms, Not Models

Don't default to downloading a full model architecture. Ask: "Which specific mechanism solves my problem?"

| Need | Mechanism | Not |
|------|-----------|-----|
| Spatial focus on image regions | Cross-attention over CNN feature maps | Full Vision Transformer |
| Sequence ordering | Positional encoding + self-attention | Full transformer encoder-decoder |
| Feature comparison | Cosine similarity / contrastive head | Siamese network framework |
| Multi-label classification | Lightweight backbone + attention pooling + classifier head | End-to-end fine-tuned large model |

Custom architecture (backbone + mechanism + head) is smaller, faster, and tuned to exactly your problem. The tradeoff: no pretrained weights for your exact config — but often less data is needed when the architecture matches the problem structure.

### Strip to Primitives

Frameworks wrap layers of abstraction around computation kernels. For production, ask:

- **Training time:** Framework overhead is acceptable — developer velocity matters more.
- **Inference time:** Extract the computation graph. Remove what you don't use.

| Layer | Example | When to strip |
|-------|---------|---------------|
| High-level API | Ultralytics, HuggingFace Trainer | When you need control over the training loop or inference pipeline |
| Framework | PyTorch, TensorFlow | When deploying — export to ONNX/TensorRT, don't ship the training framework |
| Operator level | Custom CUDA kernels, C++ extensions | When a specific operation is the bottleneck and the framework's implementation is general-purpose |

---

## Deployment

### Separate Training from Inference

The training artifact is not the deployment artifact.

```
Train (PyTorch/TF) → Export (ONNX) → Optimize (TensorRT/ONNX Runtime) → Deploy
```

- Training container: large, GPU, full framework — that's fine, it runs once
- Inference container: minimal runtime only — no autograd, no optimizer, no training utilities
- PyTorch container: ~4GB+. ONNX Runtime container: ~500MB. TensorRT: even smaller with better throughput.

### Inference Optimization Checklist

- [ ] Exported to ONNX or framework-native format (TorchScript, SavedModel)?
- [ ] Quantized (FP16/INT8) where accuracy permits?
- [ ] Batching strategy defined (dynamic vs fixed)?
- [ ] Runtime selected (TensorRT for NVIDIA, ONNX Runtime for cross-platform, Core ML for Apple)?
- [ ] Profiled end-to-end latency (not just model inference — include pre/post-processing)?

---

## Training Mode Workflow

This workflow applies when the dev skill enters **Train mode**. It replaces Build mode's test→implement→verify loop with an experiment loop suited to ML's iterative nature.

### Phase 1: Define Convergence Criteria

Before any training, define what "done" looks like in measurable terms:

```markdown
## Convergence Criteria
- Primary: [metric] [operator] [threshold] (e.g., mAP@50 > 0.85)
- Secondary: [metric] [operator] [threshold] (e.g., inference latency < 50ms)
- Stop condition: [when to stop iterating] (e.g., 3 consecutive experiments with <1% improvement)
```

If you can't define convergence criteria, you're not ready to train — go to Design mode first.

### Phase 2: Validate Data

Before spending compute, verify the data is sound:

- [ ] Class distribution — are classes balanced? If not, is that intentional?
- [ ] Label quality — sample 20-50 items and manually verify labels
- [ ] Train/val/test splits — no data leakage between splits
- [ ] Data pipeline — does loading, augmentation, preprocessing produce expected output?
- [ ] Edge cases — what does the model see for ambiguous/hard examples?

If data pipeline engineering is needed (ingestion, cleaning, transformation), switch to **Build mode** for that work, then return to Train mode.

### Phase 3: Baseline

Establish a baseline with minimal configuration:
- Pretrained model, default hyperparameters, no augmentation
- Record all metrics in experiment log
- This is experiment #1 — every future experiment is measured against it

### Phase 4: Experiment Loop

```
Read experiment-log.md → Change ONE variable → Train → Evaluate → Record → Decide
```

**Rules:**
1. **One variable per experiment** — changing lr AND augmentation AND architecture means you can't attribute the result
2. **Read the log first** — always, every time, no exceptions. This survives context compression.
3. **Record before deciding** — write the result before choosing the next experiment. Prevents confirmation bias.
4. **Stop when criteria met OR diminishing returns** — don't chase the last 0.1% unless the business requires it

**Typical experiment order** (high-to-low impact):
1. Architecture / model selection
2. Data augmentation strategy
3. Learning rate and schedule
4. Batch size
5. Regularization (dropout, weight decay)
6. Fine-grained hyperparameters

### Phase 5: Evaluate & Handoff

When convergence criteria are met:
- Run final evaluation on held-out test set (not val set)
- Profile inference performance (latency, throughput, memory)
- Export model (see Deployment section above)
- Record final results in experiment log

**Handoff to Build mode** for: inference engine, API wrapper, deployment pipeline, monitoring.
**Handoff to Analyze mode** for: "why do certain classes underperform?", error analysis, failure mode investigation.

---

## Experiment Log (Long-Running ML Work)

When running iterative training loops (overnight/multi-day), context compression will drop earlier attempts. Maintain an append-only experiment log so Claude doesn't retry failed approaches or lose track of the best result.

**Create `experiment-log.md` in the project root** at the start of any ML training session. Append after every meaningful experiment.

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
4. **Keep entries terse** — this file will be read many times, don't pad it

This only applies to ML iteration loops. Dev builds (apps, pipelines) use the standard evidence pattern (test results + quality scans).

---

## The Meta-Principle

**Minimize the distance between your problem and your solution.**

| Approach | Energy |
|----------|--------|
| Start from problem → pull only needed primitives | Low |
| Start from framework → configure until it fits | High |
| Chain solved sub-problems → simple pipeline | Low |
| Train one model to do everything end-to-end | High |
| Ship optimized inference artifact | Low |
| Ship training framework as inference engine | High |

This is gradient descent applied to engineering decisions: find the lowest-energy solution, not the most obvious one.
