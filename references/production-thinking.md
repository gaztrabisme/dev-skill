# Production Thinking

Mental models for the journey from "my model works" to "this runs reliably in production." Consult during Build mode (inference pipelines, deployment) and Design mode (system architecture). These are the questions a 10-year senior asks reflexively — use them deliberately until they become reflexive.

**Origin:** Distilled from senior engineer feedback on the PDSI inference pipeline. The gap wasn't knowledge of specific tricks — it was operating at the wrong abstraction layer. At the API level, two ONNX model calls look equivalent. At the hardware level, the data movement between them dominates latency.

---

## The Layer Below

Every technology you use in production has a layer below the API you call. That layer is where optimization opportunities and failure modes live. At the API level, everything looks like function calls. One layer down, you see memory copies, synchronization barriers, serialization overhead, and hardware constraints.

### The Rule

**For every production-critical technology, be able to answer: "What happens between my function calls?"**

Not "how does the API work" — that's the layer you're already at. The question is: what invisible operations happen that the API abstracts away?

### Your Stack, One Layer Down

| You call | What actually happens below |
|---|---|
| `ort.InferenceSession.run()` | Input tensor copied to GPU memory (if not already there), CUDA kernels dispatched, output copied back to host |
| `numpy` slicing between two GPU models | Implicit GPU→CPU sync, PCIe memcpy to host, CPU operation, PCIe memcpy back to device |
| `cv2.resize()` on a frame | CPU operation — if the frame came from GPU decode, it already round-tripped through PCIe |
| `docker.containers.run()` | cgroup creation, namespace setup, overlay filesystem mount, GPU device passthrough (nvidia-container-runtime) |
| `subprocess.Popen(ffmpeg)` | Fork + exec, pipe buffer allocation, kernel context switches per write |
| `threading.Thread` in Python | OS thread created, but GIL means only one thread executes Python bytecode at a time |
| `requests.post()` to localhost | Still TCP: SYN/ACK, serialization, kernel buffer copy, deserialization — not a function call |

### Forcing Questions

1. **"Where does my data physically live at each step?"** Draw it: GPU memory → host memory → disk → network → host memory → GPU memory. Every arrow is latency.

2. **"What moves data between devices?"** PCIe bus (GPU↔CPU): ~12 GB/s practical on PCIe 4.0. Network: ~1 Gbps typical. Disk: ~500 MB/s SSD. These are hard ceilings.

3. **"What synchronization happens implicitly?"** GPU operations are async by default. But the moment you touch the result on CPU (numpy, print, save), the runtime inserts a sync barrier — CPU blocks until GPU finishes. One innocent `print(output.shape)` in the hot path serializes your pipeline.

4. **"Can I name the layer below this API?"** If no → you have a blind spot. Doesn't mean you need to master it, but you need to know it exists so you can investigate when something is unexpectedly slow.

### Anti-Pattern: The Invisible Round-Trip

```
# Looks like: three fast operations
persons = yolo_model.run(frame)          # GPU inference
crops = [frame[y1:y2, x1:x2] for ...]   # "just" numpy slicing
ppe = multilabel_model.run(crops)         # GPU inference

# Actually: GPU → sync → PCIe copy → CPU slice → PCIe copy → GPU
# The numpy slicing forces a GPU→CPU sync + memory copy.
# The re-upload for multilabel is another PCIe copy.
# These transfers can take longer than the inference itself.
```

**Fix:** Keep data on the same device. Options:
- Merge models into one ONNX graph with a custom crop op (graph surgery)
- Use GPU-native cropping (CUDA kernel, torchvision.ops on GPU tensors)
- Redesign: single model that does both tasks (RF-DETR approach — one pass, no crop needed)

---

## Graph-Level Thinking

A multi-step inference pipeline is a computation graph. Each step is a node. Each data handoff is an edge. Optimization means: minimize edges (data movement), fuse nodes (eliminate intermediate representations), and keep the whole graph on one device.

### Forcing Questions

1. **"Can I draw my pipeline as a graph?"** If you can't draw it, you can't optimize it. Nodes = operations. Edges = data movement. Color edges by device (GPU=green, CPU=red, network=orange).

2. **"Can any adjacent nodes be fused?"** Two ONNX models in sequence → merge into one graph (`onnx.compose.merge_models`, `onnx-graphsurgeon`). Model + preprocessing → bake resize/normalize into the ONNX graph as initial nodes. Model + postprocessing → add NMS/threshold as final nodes.

3. **"Can I eliminate intermediate materialization?"** Every time you save an intermediate result (to numpy, to disk, to a message queue), you're materializing. Sometimes necessary (for debugging, for fan-out). Often not — it's just how the code evolved.

4. **"What's the minimum data that crosses device boundaries?"** If you must cross CPU↔GPU, send the smallest possible payload. Bounding box coordinates (4 floats) cross cheaper than pixel crops (224×224×3 floats).

### Tools You Should Know Exist

| Tool | What it does | When to reach for it |
|---|---|---|
| `onnx.compose` | Merge multiple ONNX models into one graph | Two models in sequence on same device |
| `onnxruntime` custom ops | Add arbitrary ops (crop, NMS, custom logic) to ONNX graph | CPU logic between GPU model passes |
| `onnx-graphsurgeon` (NVIDIA) | Programmatic ONNX graph editing — add/remove/replace nodes | Modify exported graphs without re-exporting |
| TensorRT plugins | Custom CUDA kernels as TRT layers | When ONNX RT custom ops aren't fast enough |
| NVIDIA DALI | GPU-accelerated data preprocessing pipeline | Preprocessing is the bottleneck, not inference |
| `torch.cuda.Stream` | Overlap GPU compute with data transfers | Pipeline multiple frames through GPU |

### The Pipeline Fusion Ladder

From least fused (slow, easy) to most fused (fast, harder):

```
Level 0: Separate processes, communicate via files/HTTP
Level 1: Same process, separate models, CPU glue code between them
Level 2: Same process, models share GPU memory, minimal CPU involvement
Level 3: Merged ONNX/TRT graph, single forward pass, no intermediate materialization
Level 4: Custom CUDA kernel fusing multiple operations (rarely needed)
```

Most production pipelines should aim for Level 2-3. Level 0-1 is where most people stop because it's how you prototype. The senior's reflex is to ask "why aren't we at Level 3?" immediately.

---

## Systems Interaction

Components that are fast in isolation can be slow together. The senior's instinct: **"What happens when these things run at the same time?"**

### Forcing Questions

1. **"What shared resources are my components competing for?"** Common contenders:
   - **GPU memory** — two models loaded simultaneously may not fit
   - **PCIe bandwidth** — multiple streams copying data to GPU saturate the bus
   - **CPU cores** — Python GIL means threads serialize on CPU-bound work
   - **Memory bandwidth** — multiple preprocessing threads can saturate DRAM
   - **Disk I/O** — logging, saving frames, reading configs all share one disk

2. **"Does this component assume it has exclusive access to a resource?"** GPU inference benchmarks assume exclusive GPU access. In production with N camera containers, each gets 1/N of the GPU. Your 7ms benchmark becomes 7×N ms effective if they contend.

3. **"What's the queuing behavior under load?"** When producer is faster than consumer, queues grow. Unbounded queues → OOM. Bounded queues → backpressure or dropped items. Ask: "Which queue is the pressure valve, and what happens when it activates?"

4. **"What's the GIL situation?"** In Python:
   - CPU-bound threads: GIL serializes them → use `multiprocessing` or C extensions that release GIL
   - I/O-bound threads: GIL released during I/O → `threading` is fine
   - ONNX Runtime: releases GIL during inference → GPU threads truly parallel
   - NumPy: releases GIL for large array ops → parallel for heavy preprocessing
   
   If you don't know which category your threads fall into, you're guessing at concurrency.

### Anti-Pattern: The Benchmark Lie

```
# Benchmarked in isolation:
# - ONNX inference: 7ms
# - Frame capture: 2ms
# - Alert generation: 5ms
# Total: 14ms → "We can do 71 FPS!"

# Reality with 10 cameras on one GPU:
# - GPU contention: 7ms × 3-5x = 21-35ms
# - PCIe saturation: +10ms waiting for bus
# - CPU GIL: alert generation serializes across threads
# - Actual: ~25 FPS on a good day, 15 FPS under alert storms
```

**Fix:** Always benchmark under realistic concurrency. Profile the system, not the component.

---

## Scale Projection

The senior asks: **"What breaks at 10x?"** Not because you'll be at 10x tomorrow, but because it reveals architectural assumptions that are invisible at current scale.

### Forcing Questions

1. **"What's O(1) vs O(N) in my pipeline?"** Model loading is O(1). Per-frame inference is O(N). Alert JPEG saving is O(alerts). Which O(N) operations dominate at 10x the current N?

2. **"What resource is my pipeline really limited by?"** Profile to find out. Common limiters:
   - **Compute-bound:** GPU utilization near 100%, adding cameras makes everything slower
   - **Memory-bound:** GPU VRAM fills up, next model load fails
   - **I/O-bound:** Disk writes (JPEG alerts, HLS segments) saturate
   - **Network-bound:** RTSP streams + Kafka messages + HLS output exceed bandwidth

3. **"What accumulates over time?"** Resources that grow without bound:
   - HLS segments on disk (without cleanup)
   - Log files
   - InfluxDB cardinality (unique tag combinations)
   - Thread handles from leaked threads
   - GPU memory fragmentation
   
   Anything that grows → eventually breaks. The senior's reflex: "where's the cleanup?"

4. **"What's the blast radius of one component failing?"** If one camera stream hangs, does it block others? If Kafka is down, do alerts queue in memory until OOM? Failure isolation = scale resilience.

### The 10x Test

Before deploying, mentally simulate 10x load:
- 10x cameras: Does GPU VRAM fit 10x model instances? (Hint: share one model, not N copies)
- 10x frame rate: Does the queue drop frames gracefully or OOM?
- 10x alerts: Does disk I/O keep up? Does Kafka partition handle it?
- 10x duration: What accumulates after 10x runtime hours?

You don't need to solve all of these. You need to know which ones will bite first.

---

## Cross-Domain Patterns

Many production ML problems are solved problems in other domains. The senior recognizes the pattern from databases, networking, or OS design. You can shortcut years of experience by learning to make these translations.

### Pattern Map

| ML Pipeline Problem | Equivalent In | Solution Pattern |
|---|---|---|
| Two models with CPU glue between them | Database: join across two tables on different servers | Co-locate (merge the graph) or denormalize (single model) |
| Processing every frame when most are identical | Networking: sending full state vs. delta updates | Skip-frame / temporal differencing — only process when something changes |
| Multiple cameras sharing one GPU | OS: multiple processes sharing one CPU | Time-slicing with priority scheduling. Batch across cameras for better GPU utilization |
| Alert storm overwhelming downstream | Networking: packet storm / DDoS | Rate limiting (alert interval), backpressure, circuit breaker |
| Model loading takes 5s on cold start | Database: cold cache after restart | Warm-up: pre-load models at container start, run dummy inference to JIT-compile CUDA kernels |
| Preprocessing bottleneck on CPU | Database: application-side filtering vs. DB-side filtering | Push the work to where the data is (GPU preprocessing with DALI/custom ops) |
| N containers each loading the same model | OS: shared libraries (libc loaded once, mapped into N processes) | Model serving: one inference server (Triton), N camera clients send frames via shared memory |
| Frame queue growing under load | Networking: TCP congestion | Backpressure signal → producer slows down, or explicit drop policy (tail drop, random early drop) |

### Forcing Question

**"What's the equivalent problem in [databases / networking / operating systems]?"**

If you can name the equivalent, the solution patterns from that domain probably transfer. Database people have 40 years of solutions for data movement, caching, and query optimization. Networking people have 40 years of solutions for throughput, backpressure, and multiplexing. Use their vocabulary — it makes Google searches more productive too.

---

## Hardware Constraints

Software optimization hits a ceiling set by physics. The senior knows these ceilings intuitively. You can learn them once and reference them.

### Key Numbers (2024-era hardware)

| Resource | Typical Ceiling | Implication |
|---|---|---|
| PCIe 4.0 x16 bandwidth | ~25 GB/s theoretical, ~12 GB/s practical | A 512×512×3 float32 frame ≈ 3MB → ~0.25ms per transfer. 30 frames/sec = ~90MB/s (fine). But CUDA sync overhead dominates small transfers, not raw bandwidth |
| GPU memory (RTX 5080) | 16 GB VRAM | One RF-DETR ≈ 500MB. 10 copies = 5GB. Leaves 11GB for tensors. Memory fragmentation over time can cause OOM even with headroom |
| GPU compute (RTX 5080) | ~50 TOPS FP16 | Theoretical max. Actual throughput depends on memory access patterns, not just FLOPS |
| DRAM bandwidth | ~50 GB/s DDR5 | CPU preprocessing on large images can be memory-bandwidth-bound, not compute-bound |
| NVMe SSD write | ~3-5 GB/s sequential, ~1 GB/s random | 10 alert JPEGs/sec is fine. 300 HLS segments/sec across 10 cameras — check random write pattern |
| 1 Gbps network | ~100 MB/s after overhead | One 1080p RTSP stream ≈ 5 MB/s. 10 streams = 50 MB/s. 20 streams → consider 10GbE |
| Python GIL | 1 thread executing Python bytecode at a time | N Python threads doing CPU work = 1 core of throughput. C extensions releasing GIL are the escape hatch |

### Forcing Questions

1. **"Am I compute-bound or memory-bound?"** If GPU utilization is high but throughput is low, you're memory-bound — the GPU is waiting for data from VRAM. Smaller batch sizes or model quantization help more than a faster GPU.

2. **"What's the theoretical maximum throughput?"** `Model size / memory bandwidth` gives minimum inference time for a memory-bound model. `FLOPS required / GPU TFLOPS` gives minimum for compute-bound. Your actual time can't beat the worse of these two.

3. **"Am I paying for precision I don't need?"** FP32 → FP16 halves memory bandwidth and often doubles throughput, with negligible accuracy loss for inference. INT8 halves it again but requires calibration. Most detection models work fine in FP16.

---

## Operational Failure Modes

The senior asks: **"How does this fail at 3am?"** Not just "does it work" but "how does it fail, and will I know?"

### Forcing Questions

1. **"What's the failure mode — loud or silent?"**
   - **Loud:** crash, exception, container restart → you know immediately
   - **Silent:** model returns garbage confidences, stream degrades to 2 FPS, alerts stop without error → you find out when the client calls
   
   Silent failures are worse. For every component, ask: "If this degrades, will any monitoring catch it?"

2. **"What happens when an external dependency is temporarily unavailable?"**
   - Kafka down: do alerts buffer in memory (OOM risk) or drop (data loss)?
   - InfluxDB slow: does the writing thread block the inference thread?
   - RTSP stream drops: does reconnection happen, and what happens to pipeline state during the gap?
   
   The answer should be explicit in the code, not "I think it just retries."

3. **"What's the recovery path?"** After a crash, can the system resume automatically? Does it need manual intervention? "Restart container" vs. "restart container, re-pull model, re-authenticate to Kafka, manually check HLS state" — this difference determines whether you can sleep through failures.

4. **"What does graceful degradation look like?"** When GPU runs out of headroom:
   - **Bad:** crash, no video, no alerts
   - **Better:** reduce inference FPS, keep HLS streaming, alert at lower frequency
   - **Best:** automatically shed load (pause low-priority cameras), alert ops team

### The Silent Failure Checklist

For each pipeline component, define:
- [ ] What does "healthy" look like? (metric or heartbeat)
- [ ] What does "degraded" look like? (threshold)
- [ ] What does "failed" look like? (absence of signal)
- [ ] Who/what gets notified at each level?
- [ ] Is recovery automatic or manual?

---

## Common Failure Patterns

The closest encoding of "experience" — patterns a senior has seen fail enough times to recognize instantly.

### GPU Memory Patterns

| Pattern | Symptom | Root Cause | Fix |
|---|---|---|---|
| Gradual VRAM increase | OOM after N hours of stable running | Memory fragmentation, tensors not freed, CUDA context growth | Periodic VRAM monitoring + model reload schedule, or memory pools |
| OOM on startup under load | Model loads alone fine, fails with N containers | Each container allocates VRAM independently | Shared inference server (Triton) or sequential startup with memory check |
| Inference time creep | 7ms → 20ms after 1000 frames | CUDA context pollution, memory fragmentation | Profile with `nvidia-smi dmon`, consider periodic process restart |

### Pipeline Patterns

| Pattern | Symptom | Root Cause | Fix |
|---|---|---|---|
| Queue memory growth | Container memory climbs linearly | Producer faster than consumer, unbounded queue | Bounded queue with drop policy — design decision, not a bug |
| Thread leak on reconnect | Thread count climbs, CPU spikes | Old stream thread not joined on reconnect | Explicit thread lifecycle: cancel → join → restart |
| Timestamp drift | Alerts show wrong time after hours | Wall clock instead of monotonic for intervals, or NTP issues | `time.monotonic()` for intervals, UTC everywhere for timestamps |
| FFmpeg zombie | HLS stops, ffmpeg process still running | Pipe broken but process not killed | Explicit process lifecycle: check returncode, kill on timeout |

### "Works on My Machine" Patterns

| Dev Environment | Production Reality | Why |
|---|---|---|
| One model, exclusive GPU | N models, shared GPU | GPU contention changes latency entirely |
| Local filesystem, fast SSD | Docker overlay, shared volume | Overlay fs has write amplification. Shared volumes add network latency |
| Clean restart every debug session | 30-day uptime between updates | Everything that accumulates matters |
| Single RTSP stream, stable | 10 streams, some flaky | Network jitter, camera firmware bugs, WiFi cameras dropping |

---

## Pre-Deployment Checklist

Before pushing an inference pipeline to production, answer these:

### Data Movement
1. Where does data physically live at each pipeline step? Can I draw the device transitions?
2. Are there any GPU→CPU→GPU round-trips that could be eliminated?
3. Is preprocessing happening on the same device as inference?

### System Interactions
4. What shared resources do my components compete for? (GPU, PCIe, disk, CPU cores)
5. Under realistic concurrency (N cameras), what's the actual throughput?
6. Where is the GIL a bottleneck, and where does it not matter?

### Scale
7. What breaks at 10x cameras? 10x frame rate? 10x runtime duration?
8. What accumulates over time without cleanup? (files, memory, connections, queue depth)
9. What's the blast radius of one component failing?

### Hardware
10. Am I compute-bound or memory-bound? (Profile, don't guess)
11. Am I paying for precision I don't need? (FP32 when FP16 works)
12. Do I know the ceiling numbers for my hardware? (PCIe bandwidth, VRAM, disk I/O)

### Operations
13. For each component: how does it fail silently? What monitoring catches it?
14. When an external dependency goes down, what happens? (Explicit, not "I think it retries")
15. Can the system recover from a crash without manual intervention?
16. After 30-day uptime, what state has accumulated that a fresh start doesn't have?

---

## The Meta-Principle

**Optimize the pipeline, not the model.**

Most ML engineers spend 90% of optimization effort on model architecture and 10% on the pipeline around it. In production, it's usually the opposite: the pipeline (data movement, concurrency, I/O, failure handling) determines real-world performance more than model inference time.

A 7ms model in a 200ms pipeline means the model is 3.5% of your latency. Making the model 2x faster saves 3.5ms. Eliminating one unnecessary GPU→CPU round-trip saves 5-50ms. The senior optimizes the pipeline first because that's where the time actually goes.

| Optimization | Typical Savings | Effort |
|---|---|---|
| Model FP32 → FP16 | 1.5-2x inference speedup | Low (one export flag) |
| Eliminate CPU preprocessing round-trip | 5-50ms per frame | Medium (ONNX graph surgery or GPU preprocessing) |
| Merge two models into one graph | 10-100ms per frame (eliminates transfer + sync) | Medium-High (graph surgery, custom ops) |
| Batch inference across cameras | 2-5x throughput improvement | Medium (architecture change) |
| Shared model server (Triton) | Eliminates per-container model loading, 60-80% VRAM savings | High (infrastructure change) |

Ask: **"Where does the time actually go?"** Profile first. Then optimize the biggest bar in the profile, not the most intellectually interesting component.

---

## How to Close Your Own Gaps

This document encodes specific patterns. But the meta-skill — the ability to discover blind spots proactively — requires a learning strategy, not a bigger checklist.

### The "Layer Below" Audit

Periodically (monthly, or when starting with a new technology), list your production stack and check:

| Technology | Can I name the layer below? | Do I know the failure modes? | Last time I read the internals? |
|---|---|---|---|
| ONNX Runtime | ONNX graph format, execution providers, memory arenas | ? | ? |
| Docker | cgroups, namespaces, overlay fs, GPU passthrough | ? | ? |
| FFmpeg | codec internals, keyframes, GOP structure | ? | ? |
| FastAPI/Uvicorn | ASGI, event loop, worker model | ? | ? |
| PostgreSQL | query planner, indexes, WAL, vacuum | ? | ? |

A "?" means you have a blind spot. Not an emergency — but when something breaks in that component, you'll be debugging from the API level instead of the root cause level.

### Where to Learn the Layer Below

Not tutorials (they teach the API you already know). Read:
- **The "internals" or "architecture" page** of the official docs (every major project has one)
- **Performance tuning guides** — they expose what knobs exist and why, which teaches the layer below
- **Post-mortems** from companies running at scale — they describe failures you haven't hit yet
- **Source code** of the hot path — even skimming teaches you what actually happens per call

One hour of reading ONNX Runtime's execution provider docs would have revealed that custom ops exist and that graph surgery is a normal workflow — surfacing the senior's insight before he had to point it out.
