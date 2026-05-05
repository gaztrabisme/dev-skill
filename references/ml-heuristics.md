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

## Label Schema Design

**Your label schema IS your model architecture.** Get this wrong and no amount of training fixes it.

### Mutual Exclusivity Test

Before defining labels, ask: **"Can these values coexist on the same sample?"**

| Answer | Formulation | Loss |
|--------|------------|------|
| No — they're states of the same thing | Multi-class (one task, N classes) | CrossEntropyLoss |
| Yes — genuinely independent attributes | Multi-label (N independent sigmoids) | BCEWithLogitsLoss |

**Anti-pattern:** Splitting mutually exclusive states into independent binary attributes. Example: `no_helmet`, `helmet_backward`, `helmet_no_strap` as three binary sigmoids — but a person can't simultaneously have no helmet AND a backward helmet. These are 3 classes of one `helmet` task, not 3 independent binary tasks. Sigmoid allows contradictory outputs (P(no_helmet)=0.8 AND P(helmet_backward)=0.7). CrossEntropy + softmax enforces mutual exclusivity by design.

### The "Unknown" Class Trap

Ask: **"Is this class a visual pattern learnable from pixels, or a metadata annotation about the image?"**

- "Head not visible in frame" → NOT a visual category. There's no pixel pattern for absence. Use `ignore_index=-1` to produce zero gradient for that task on that sample.
- Having "unknown" as a learnable class creates an escape hatch — the model dumps uncertain predictions into it instead of learning real decision boundaries.
- At inference time, handle uncertainty via softmax confidence threshold (e.g., 0.60), entirely decoupled from training.

### Variable Class Counts

Different tasks can have different numbers of classes. Don't force everything into the same shape:

```python
TASK_NUM_CLASSES = {
    "helmet":  3,   # absent / correct / wrong
    "body":    3,   # absent / correct / worn wrong
    "hand":    2,   # absent / present
    "foot":    2,
    "glasses": 2,
}
```

One `CrossEntropyLoss` per task allows per-task class weights, ignore_index, and independent class counts.

---

## Multi-Task Architecture

When multiple tasks share a backbone, **gradient politics** determines what the backbone learns.

### The Gradient Dominance Problem

Easy tasks (binary, 2-class) converge faster → their gradients become large and confident early → backbone gradient = sum of all task gradients → backbone optimizes for easy tasks, starving hard tasks of signal.

**Fix: Shared projection layer** between backbone and task heads:
```
Backbone [D] → FC(D→P) + BatchNorm1d + Activation + Dropout → task heads
```

BatchNorm normalizes the feature distribution so no single task's loss scale distorts the shared representation. All tasks backpropagate through the projection equally.

### Proportional Head Sizing

Size task heads to match task complexity:

| Task Type | Architecture | Rationale |
|-----------|-------------|-----------|
| Hard (3+ classes, fine-grained visual differences) | Projection → 128 → C | More capacity for subtle distinctions |
| Easy (2 classes, coarse signal) | Projection → 64 → C | Less capacity prevents overfitting |

Oversized heads on simple tasks waste parameters and overfit on small datasets.

### Safety/Priority Weighting

Not all misclassifications are equally costly. Weight the loss by consequence:
```python
TASK_WEIGHTS = {"helmet": 2.0, "body": 2.0, "hand": 1.0, "foot": 1.0, "glasses": 1.0}
loss = sum(TASK_WEIGHTS[task] * CE(logits, labels) for task in tasks)
```

Ask: **"If the model gets this wrong, what's the real-world cost?"** Fatal risk → higher weight.

---

## Training Schedule

### Phased Unfreezing (For Pretrained Backbones)

**Problem:** Randomly initialized heads produce large, noisy gradients. If the backbone is unfrozen from epoch 1, these gradients destroy pretrained features (edge detectors, texture filters, spatial reasoning) — catastrophic forgetting.

**Solution: 3-phase schedule:**

| Phase | Backbone | LR (backbone) | LR (heads) | Purpose |
|-------|----------|--------------|------------|---------|
| 1: Warmup (ep 1-5) | Frozen | 0 | ramp from lr/100 → lr | Stabilize random heads |
| 2: Partial FT (ep 6-20) | Top blocks unfrozen | lr × 0.1 | cosine decay | Adapt task-specific features |
| 3: Full FT (ep 21-40) | All unfrozen | lr × 0.01 | cosine continues | Fine-tune general features conservatively |

**Key detail:** Use `optimizer.add_param_group()` at phase transitions — this preserves momentum states for parameters already being trained. Don't rebuild the optimizer.

### When to Use Phased Unfreezing

Ask: **"Am I fine-tuning a pretrained model with randomly initialized heads?"** If yes → always use phased unfreezing. The 2-4% accuracy improvement on hard tasks is free.

### Class Imbalance

When any class has fewer than ~5% of the most common class, use inverse-frequency class weights:
```
w_c = (1 / count_c) / mean(1 / count_c)
```
This normalizes so mean weight = 1, correcting imbalance without inflating the total loss magnitude.

---

## Metrics

### Global Accumulation, Not Per-Batch Averaging

**Problem:** Per-batch F1 averaging is a biased estimator. With rare classes and batch_size=32, most batches have 0 positive examples → per-batch F1 = 0.0 → average is systematically lower than true performance.

**Fix:** Store all argmax predictions and labels as CPU int64 tensors during the epoch (negligible memory). Compute F1 once over the full dataset at epoch end. This is unbiased by construction and comparable across runs with different batch sizes.

Ask: **"Does any class have fewer samples than my batch size?"** If yes → per-batch metrics are biased → accumulate globally.

### Primary Metric Selection

Use **macro F1** (unweighted average across classes per task, then averaged across tasks) as the primary checkpoint selection metric. It balances precision and recall and is sensitive to rare-class performance — unlike accuracy, which can be gamed by always predicting the majority class.

---

## Augmentation

### Domain-Specific Augmentations Are Not Optional

Ask: **"What does the real-world input distribution look like? What variations exist that my training data doesn't cover?"**

| Real-World Variation | Augmentation |
|---------------------|-------------|
| Grayscale CCTV cameras | `RandomGrayscale(p=0.05)` |
| Night / low-light | `ColorJitter(brightness=0.3)` + consider CLAHE preprocessing at inference |
| Compression artifacts | Random JPEG compression |
| Variable resolution | `Resize(256) → RandomCrop(224)` not just `Resize(224)` |
| Camera angles | `RandomHorizontalFlip(p=0.5)` (NOT vertical — people don't appear upside down) |

Every variation missing from training is a failure mode in production.

### Augmentation for Resize

Use `Resize(img_size + 32) → RandomCrop(img_size)` for training, not `Resize(img_size)` directly. The extra border gives the crop randomness to work with, simulating slight scale and position variations. Validation uses `Resize(img_size)` directly — no randomness.

---

## Architecture Decisions

### Use Mechanisms, Not Models

Don't default to downloading a full model architecture. Ask: "Which specific mechanism solves my problem?"

| Need | Mechanism | Not |
|------|-----------|-----|
| Spatial focus on image regions | Cross-attention over CNN feature maps | Full Vision Transformer |
| Sequence ordering | Positional encoding + self-attention | Full transformer encoder-decoder |
| Feature comparison | Cosine similarity / contrastive head | Siamese network framework |
| Multi-task classification | Lightweight backbone + shared projection + per-task heads | End-to-end fine-tuned large model |

### Model Sizing Is an Inference Budget Problem

Ask: **"What's my end-to-end latency budget, and how does each component's inference time stack up?"**

```
Example budget: 10ms per person on RTX A4000
  YOLO nano person detection:     ~2ms
  MobileNetV3-Small backbone:     ~1.5ms (fp16)
  Shared projection + 5 heads:    ~0.5ms
  Total:                          ~4ms ✓ (headroom for multi-camera)
```

Choose the backbone AFTER knowing the budget, not before. The fastest model that meets accuracy requirements wins.

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

## Pre-Training Checklist

Before writing any training code, answer these questions:

### Problem Formulation
1. Are my classes mutually exclusive or independent? → CrossEntropy vs Sigmoid
2. Is every class a learnable visual pattern, or are some metadata? → Remove non-visual classes from model output
3. What's the simplest problem type this reduces to?

### Architecture
4. Do I have mixed-difficulty tasks sharing a backbone? → Need gradient balancing (shared projection + BatchNorm)
5. Does each head's capacity match its task complexity? → Size proportionally
6. What's my inference latency budget? → Size the backbone accordingly

### Training
7. Am I fine-tuning pretrained weights? → Phased unfreezing + differential LR
8. Are all errors equally costly? → Task weights in loss
9. Is my dataset class-imbalanced? → Inverse-frequency class weights
10. Is my metric computation biased by batch composition? → Global accumulation

### Data & Augmentation
11. What does the real-world input distribution look like? → Domain-specific augmentations
12. What edge cases exist (grayscale cameras, night, occlusion)? → Cover in augmentation pipeline

### Labels
13. Is `-1`/unknown a visual category or an annotation decision? → `ignore_index`, not a class
14. Are my label granularity and model output granularity aligned? → Don't split mutually exclusive states into independent attributes

---

## Training Mode Workflow

This workflow applies when the dev skill enters **Train mode**. It replaces Build mode's test→implement→verify loop with an experiment loop suited to ML's iterative nature.

### Phase 1: Define Convergence Criteria

Before any training, define what "done" looks like in measurable terms:

```markdown
## Convergence Criteria
- Primary: [metric] [operator] [threshold] (e.g., mean_f1 > 0.85)
- Secondary: [metric] [operator] [threshold] (e.g., inference latency < 10ms)
- Stop condition: [when to stop iterating] (e.g., 3 consecutive experiments with <1% improvement)
```

If you can't define convergence criteria, you're not ready to train — go to Design mode first.

### Phase 2: Validate Data

Before spending compute, verify the data is sound:

- [ ] Class distribution — are classes balanced? If not, enable class weights
- [ ] Label quality — sample 20-50 items and manually verify labels
- [ ] Label schema — mutual exclusivity test passed, no "unknown" class trap
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
| [e.g. mean_f1] | [value] | [key hyperparams] | [path/epoch] |

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
