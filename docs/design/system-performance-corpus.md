# System-performance corpus: analysis methodology, profiling, tuning

<!-- frob:doc src/frob/perf -->

## Scope and reconciliation

This corpus is the PERFORMANCE-ANALYSIS depth layer: methodology, resource
analysis, observability/profiling, queueing theory in practice, latency
measurement pitfalls, capacity planning, and tuning discipline. It does
NOT re-derive `docs/design/system-design-corpus.md` section 6
(Performance & capacity), which already anchors Little's Law, the
Universal Scalability Law, and "The Tail at Scale" at the DESIGN level
(when/why to model capacity). Where this corpus touches those same laws
(QT-1, QT-3, LT-2) it goes one layer deeper -- the operational mechanics
of applying them (the M/M/1 utilization-knee, USL's two coefficients in
practice, tail amplification via fan-out) -- and cross-links back rather
than duplicating the citation. `src/frob/perf/` (18 modules today,
including `_harness.py`, `_heat.py`, `_models.py`, `_profile.py`,
`_rules.py`) is frob's existing performance tooling; entries below note
where a strata-checkable obligation would sit relative to that module,
without prescribing an implementation.

Canonical anchor for the whole corpus: Brendan Gregg, *Systems
Performance: Enterprise and the Cloud*, 2nd ed., Addison-Wesley, 2020
(1st ed. 2013) -- the book that codifies USE, RED-adjacent latency
analysis, per-resource checklists, flame graphs, and the tuning
discipline used throughout. Cited per-entry below as "Gregg SysPerf2e"
with chapter. Companion primary sources: Neil J. Gunther (USL, queueing),
Cary Millsap (response-time/Method R), Gil Tene (coordinated omission),
Aleksey Shipilev (JMH microbenchmarking).

## Method note (exhaustive-research frontier)

Phase 0 enumerated 7 categories / 34 entries as the denominator (frontier
recorded in the research scratchpad, not carried in one context window).
Phase 1 drained all 34: 5 entries live-fetched this pass (USE method
canonical page, flame graphs canonical ACM Queue citation, RED method
origin, Gil Tene coordinated omission, Shipilev JMH dead-code-elimination
mechanics); the remainder are Gregg *Systems Performance* 2nd ed. chapter
content, which is stable, widely cross-cited canonical material and is
marked "reconstructed/well-known" per entry rather than claimed as
freshly re-fetched. Phase 2 coverage table is at the bottom.

---

## 1. Performance methodologies (denominator: 7)

### 1.1 The USE Method -- live-verified [P1]

**Principle**: for every resource, check Utilization (time busy),
Saturation (queued/extra work the resource can't service), Errors (error
events). Iterate the full resource list (CPUs, memory, disks, network
interfaces, controllers, interconnects) systematically rather than
guessing which resource is at fault.

**Citation**: Brendan Gregg, "The USE Method," brendangregg.com/usemethod.html;
formalized in "Thinking Methodically about Performance," ACM Queue /
Communications of the ACM, 2012-2013; full treatment Gregg SysPerf2e ch. 2
sec. 2.5.9 and per-resource in ch. 6 (CPU), 7 (memory), 8 (filesystems),
9 (disk), 10 (network).

**Scale**: any host or resource-bounded component, single-node through
cluster (apply per-node then aggregate).

**Strata-checkability**: **advisory at the general level** ("check USE for
every resource" isn't itself a single verifiable fact) but the per-resource
CHECKLIST items decompose into **provable (presence)** obligations -- e.g.
"a component with a declared CPU-bound hot path must expose a
utilization+saturation metric pair" is checkable; "go look at USE" is not.

### 1.2 The RED Method -- live-verified [P2]

**Principle**: for every request-driven service, track Rate (requests/sec),
Errors (failed request count/rate), Duration (latency distribution).
Google's Four Golden Signals adapted specifically to services rather than
resources -- RED is the service-level complement to USE's resource-level
view.

**Citation**: Tom Wilkie, "The RED Method: How to Instrument Your
Services," Weaveworks/GrafanaCon EU 2018 (grafana.com/files/grafanacon_eu_2018/Tom_Wilkie_GrafanaCon_EU_2018.pdf),
introduced 2015 while at Weaveworks.

**Scale**: any RPC/HTTP/queue-consumer service boundary, microservice
through monolith module boundary.

**Strata-checkability**: **provable (presence)** -- "every public service
boundary must expose rate+error+duration metrics" is exactly the kind of
obligation strata's boundary model can require and frob's doc-graph can
track as a coverage edge; this is the sharpest checkable claim in the
whole corpus and the natural companion to `src/frob/perf/_rules.py`.

### 1.3 Workload characterization -- reconstructed/well-known [P3]

**Principle**: before tuning, characterize who/what/how/why/when of the
load (Gregg's five questions): who is causing it, what it consists of,
why it's happening, how it's changing over time, and does it match
expectations. Prevents tuning against an assumed workload that diverges
from the real one.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.5.1.

**Scale**: system or service level, prerequisite step before any tuning.

**Strata-checkability**: advisory -- a methodology step, not a static fact.

### 1.4 Drill-down analysis -- reconstructed/well-known [P3]

**Principle**: start from a high-level metric (e.g. overall latency), then
progressively drill into the component/subsystem/code path responsible,
narrowing at each layer. Complement to USE (breadth-first per-resource)
as a depth-first bottleneck-chase technique.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.5.10.

**Scale**: any layered system, especially useful once USE/RED has
identified WHICH resource or service is implicated.

**Strata-checkability**: advisory (an investigative process).

### 1.5 Latency analysis -- reconstructed/well-known [P3]

**Principle**: decompose end-to-end latency into its constituent time
components across the request path (queueing, execution, I/O wait, network
transit) so the dominant contributor is identified rather than treating
latency as an opaque scalar.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.5.11; the general practice is
also central to Cary Millsap's Method R (below, sec. category overlap
noted).

**Scale**: single request through distributed trace.

**Strata-checkability**: advisory in general form; **provable (presence)**
in the specific case "a traced request span must carry child-span
breakdown, not a single opaque duration" -- overlaps OB-4/OB-5 below.

### 1.6 Anti-methods -- reconstructed/well-known [P3]

**Principle**: named FAILURE modes to avoid. Streetlight anti-method
(analyzing only what's easy to observe, like the drunk searching for keys
under the streetlight because that's where the light is); random-change
anti-method (trying changes ad hoc, hoping one works, without a
measurement-driven hypothesis); blame-someone-else anti-method (asserting
a dependency is at fault without evidence, deflecting rather than
diagnosing).

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.4.

**Scale**: universal (organizational/process level as much as technical).

**Strata-checkability**: **advisory but strata-relevant as a NEGATIVE
check** -- e.g. "a tuning-change commit with no attached before/after
measurement" is the random-change anti-method made checkable (see TN-1).

### 1.7 Performance checklists -- reconstructed/well-known [P3]

**Principle**: pre-built, resource/tool-specific checklists derived from
USE (e.g. Linux Performance Checklist) that give a fixed, repeatable
sequence of commands/metrics to run first, trading some flexibility for
speed and consistency of the FIRST pass.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.5.13, appendices with
per-OS/per-tool checklists.

**Scale**: single-host triage, first 5 minutes of an incident.

**Strata-checkability**: advisory (a runbook artifact, not a code fact),
though the EXISTENCE of a documented on-call checklist per service is
itself a provable (presence) organizational obligation.

---

## 2. Resource analysis (denominator: 5)

### 2.1 CPU -- reconstructed/well-known [P3]

**Principle**: utilization (% non-idle) is necessary but not sufficient --
saturation (run-queue length / scheduler latency, i.e. time a runnable
thread waits for a CPU) reveals contention utilization alone hides.
Scheduler class, priority, and per-CPU vs system-wide averaging (masking
single hot cores) all matter.

**Citation**: Gregg SysPerf2e ch. 6, esp. 6.3 (concepts: utilization vs
saturation) and 6.6 (analysis: `mpstat`, `pidstat`, run-queue latency via
`perf sched` or eBPF).

**Scale**: single core through NUMA multi-socket.

**Strata-checkability**: **provable (presence)** for the specific claim
"a CPU-bound service boundary exposes both a utilization AND a
saturation/queue-latency metric, not utilization alone" -- utilization-only
dashboards are a named anti-pattern in Gregg's treatment.

### 2.2 Memory -- reconstructed/well-known [P3]

**Principle**: working-set size (the memory a process actively touches,
not just RSS) governs real pressure; page faults (minor vs major) and
swapping/paging are the saturation signals; OOM-kill is the terminal
error signal. Utilization (used/total) alone is misleading because free
memory used for page cache is reclaimable, not "available capacity" in
the naive sense.

**Citation**: Gregg SysPerf2e ch. 7, esp. 7.2 (concepts: working set) and
7.5 (USE method applied to memory: utilization, saturation = swapping/
paging rate, errors = OOM kills / allocation failures).

**Scale**: process through container cgroup through host.

**Strata-checkability**: **provable (presence)** -- "a memory-bound
component declares an expected working-set bound and exposes a major-fault
or swap-activity metric" is checkable; "tune memory well" is not.

### 2.3 Disk / I/O -- reconstructed/well-known [P3]

**Principle**: IOPS and throughput (MB/s) alone omit latency and queueing;
the USE triad here is utilization (device busy %), saturation (I/O queue
depth / wait time), errors (I/O errors, retries). Random vs sequential
access pattern changes which metric dominates.

**Citation**: Gregg SysPerf2e ch. 9, esp. 9.3 (concepts) and 9.5-9.6
(`iostat`, `biolatency`/eBPF for per-I/O latency distribution rather than
just averages).

**Scale**: single device through storage array/network-attached storage.

**Strata-checkability**: **provable (presence)** -- an I/O-bound boundary
exposing only throughput (no latency histogram, no queue-depth) is a
named gap; the obligation "expose I/O latency distribution, not just
average" is checkable.

### 2.4 Network -- reconstructed/well-known [P3]

**Principle**: bandwidth utilization is rarely the bottleneck in practice
compared to latency and retransmits; TCP retransmission rate is a
saturation/error proxy for network health that raw throughput graphs
miss entirely. Connection-level (not just interface-level) analysis
matters for service-to-service calls.

**Citation**: Gregg SysPerf2e ch. 10, esp. 10.3 (concepts: TCP backlog,
retransmits) and 10.5 (USE applied: utilization = bandwidth used,
saturation = send/receive queue backlog, errors = retransmits/checksum
errors).

**Scale**: NIC through cluster network fabric through WAN link.

**Strata-checkability**: **provable (presence)** for "a network-dependent
boundary tracks retransmit/error rate, not bandwidth alone"; advisory for
capacity headroom judgment calls.

### 2.5 Per-resource USE checklist synthesis -- live-verified [P1]

**Principle**: the four canonical resources (CPU, memory, disk, network)
share ONE checklist shape (utilization/saturation/errors columns), which
is precisely why USE composes into a single cross-resource sweep instead
of four unrelated procedures -- the shape itself, not the specific
metrics, is the reusable artifact.

**Citation**: same as P1 (sec. 1.1), synthesized across Gregg SysPerf2e
ch. 6-10.

**Scale**: whole-host or whole-cluster sweep.

**Strata-checkability**: **provable (presence)** at the aggregate level --
"every declared resource-bound component in the architecture has a
completed row (util+sat+err all populated) in the USE table" is a clean
denominator-style obligation, directly implementable as a frob check over
`src/frob/perf/` output.

---

## 3. Observability & profiling (denominator: 7)

### 3.1 Flame graphs -- live-verified [P4]

**Principle**: visualize a stack-trace sample set as nested rectangles
(y = stack depth, x = alphabetically-merged sample population, width =
sample frequency) so the widest frames -- the code paths consuming the
most of the profiled resource -- are visible at a glance instead of
buried in walls of profiler text.

**Citation**: Brendan Gregg, "The Flame Graph," ACM Queue 14(2) / Commun.
ACM 59(6), 2016, queue.acm.org/detail.cfm?id=2927301; invented December
2011 (brendangregg.com/flamegraphs.html).

**Scale**: single-process CPU/off-CPU profile through whole-fleet
aggregate flame graphs.

**Strata-checkability**: advisory (a visualization technique, not a
static fact) -- but the OBLIGATION "a profiled hot path gets a flame
graph attached to its investigation" is a provable (presence) evidence
requirement, akin to frob's existing evidence-attachment model.

### 3.2 CPU profiling: sampling vs instrumentation -- reconstructed/well-known [P3]

**Principle**: sampling profilers (periodic stack capture, e.g. at
99 Hz to avoid lockstep with common 100 Hz timers) have low, bounded
overhead and statistical accuracy; instrumentation (tracing every
call/return) has exact counts but can distort the very timing it
measures (probe effect) and often has orders-of-magnitude higher
overhead for hot code paths.

**Citation**: Gregg SysPerf2e ch. 5 sec. 5.4 (profiling), ch. 6 sec. 6.6.10.

**Scale**: single process through fleet-wide continuous profiling.

**Strata-checkability**: advisory (a tool-selection tradeoff).

### 3.3 Off-CPU analysis -- reconstructed/well-known [P3]

**Principle**: CPU profiling only sees ON-CPU time; time spent blocked
(I/O wait, lock contention, sleep) is invisible to a CPU sampler. Off-CPU
analysis captures scheduler context-switch events (why a thread left the
CPU and how long until it returned) so the "invisible" latency -- often
the dominant component in I/O-bound services -- becomes visible, typically
via its own flame graph variant.

**Citation**: Gregg SysPerf2e ch. 5 sec. 5.5.4, originally Gregg's "Off-CPU
Analysis" work (brendangregg.com/offcpuanalysis.html) using off-CPU flame
graphs.

**Scale**: single-thread through service-level blocking analysis.

**Strata-checkability**: **provable (presence)** for the specific claim
"a service known to be I/O-bound has off-CPU (not just on-CPU) profiling
evidence attached" -- CPU-only profiling of an I/O-bound service is a
named investigative gap.

### 3.4 Tracing: ftrace / eBPF / DTrace / perf -- reconstructed/well-known [P3]

**Principle**: dynamic and static tracing frameworks let you instrument
kernel and user-space events with near-zero overhead when idle and bound
overhead when active, without recompiling. eBPF (Linux, in-kernel
verified bytecode) has become the modern default; DTrace (Solaris/BSD/
macOS origin) pioneered the model; ftrace is the lighter-weight built-in
Linux kernel tracer; `perf` is the general-purpose Linux profiling/tracing
front end.

**Citation**: Gregg SysPerf2e ch. 4 (Observability Tools) sec. 4.3-4.5;
Gregg, *BPF Performance Tools*, Addison-Wesley, 2019, for the eBPF-specific
deep treatment.

**Scale**: kernel-level events through full-system tracing.

**Strata-checkability**: advisory (tool selection); the OBLIGATION "a
kernel-boundary or syscall-heavy hot path has a trace-based (not just
sampled) investigation on record" is provable (presence).

### 3.5 Latency histograms and heatmaps -- reconstructed/well-known [P3]

**Principle**: a single average or even a single percentile hides
multi-modal distributions (e.g. a bimodal cache-hit/cache-miss latency
split looks like "medium latency" on average when it's actually two
distinct populations). Histograms (and heatmaps for latency-over-time)
expose the shape, not just a point statistic.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.9 (Latency heat maps), ch. 5
sec. 5.6.

**Scale**: single metric stream through fleet-wide dashboards.

**Strata-checkability**: **provable (presence)** -- "a latency SLO is
backed by a histogram/percentile export, not a bare average" is directly
checkable and complements LT-1 below.

### 3.6 USDT probes -- reconstructed/well-known [P3]

**Principle**: User Statically-Defined Tracing probes are stable,
named instrumentation points compiled into an application (or a
runtime like the JVM/Node) so tracers can attach to semantically
meaningful events (e.g. "GC start," "HTTP request dispatched") rather
than reverse-engineering them from raw function offsets, which break on
every recompile/version bump.

**Citation**: Gregg SysPerf2e ch. 4 sec. 4.3.7 (USDT), originally a
DTrace-ecosystem convention adopted by SystemTap/eBPF tooling.

**Scale**: single application/runtime instrumentation contract.

**Strata-checkability**: **provable (presence)** -- "a component intended
to be tracer-observable exposes stable USDT probes at its major state
transitions" is a concrete, checkable interface obligation, closely
analogous to frob's own doc-graph edges.

### 3.7 The observer effect -- reconstructed/well-known [P3]

**Principle**: the act of measuring changes the system being measured
(probe/instrumentation overhead perturbs timing, sometimes enough to
hide or fabricate the very effect under investigation). Low-overhead
sampling and in-kernel-verified tracing (eBPF) exist specifically to
minimize this; the discipline is to always ask "how much does my
measurement itself cost" before trusting a result.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.11 (Observer Effect), ch. 4
sec. 4.2.

**Scale**: universal -- applies to every profiling/tracing technique
above.

**Strata-checkability**: advisory (a caution, not itself checkable) but
feeds a checkable companion: "a reported perf delta attributes and
subtracts measurement overhead" is provable (presence) when overhead is
non-trivial (e.g. heavyweight instrumentation, not sampling).

---

## 4. Queueing & scalability theory (denominator: 5)

### 4.1 Little's Law -- depth note, xref design corpus -- live-verified [S13 in design corpus, reaffirmed]

**Principle (depth beyond design corpus)**: L = lambda * W holds for ANY
stable queueing system regardless of arrival distribution, service-time
distribution, or scheduling discipline -- its power for performance
analysis specifically is that it lets you infer any one of concurrency
(L), throughput (lambda), or average latency (W) from the other two
WITHOUT a queueing model, which is exactly the tool used to sanity-check
a load-test's reported throughput against its reported latency and
concurrency (a load generator claiming throughput inconsistent with
L = lambda*W indicates a measurement bug, often coordinated omission --
see QT-5).

**Citation**: John D. C. Little, "A Proof for the Queuing Formula:
L = lambda*W," Operations Research 9(3):383-387, 1961. Cross-linked to
`docs/design/system-design-corpus.md` sec. 6 (design-level treatment).

**Scale**: any stable queueing system, thread pool through distributed
service mesh.

**Strata-checkability**: advisory as a law; **provable (presence)** as a
CROSS-CHECK obligation -- "a load-test report's throughput/latency/
concurrency triple is internally consistent with Little's Law" is a
mechanical check frob's perf harness could run.

### 4.2 M/M/1 and the utilization-vs-latency knee -- reconstructed/well-known [P3]

**Principle**: for an M/M/1 queue (Poisson arrivals, exponential service,
1 server), expected wait time grows as rho/(1-rho) where rho is
utilization -- i.e. latency is finite and low until utilization
approaches 1, then rises asymptotically (the "knee"). The practical
consequence: pushing a resource's utilization toward 100% is not merely
diminishing returns, it is a qualitative latency cliff, which is why
capacity planning targets headroom (e.g. 70-80% utilization ceilings) not
100%.

**Citation**: classical queueing theory (Erlang/Kendall notation); treated
in Gregg SysPerf2e ch. 2 sec. 2.6 (Modeling) as the canonical example of
why utilization alone under-warns; also foundational to Neil Gunther's USL
(next entry) as the M/M/1 special case USL generalizes away from.

**Scale**: any single queueing resource -- a thread pool, a lock, a single
disk.

**Strata-checkability**: advisory (a modeling result) -- but the derived
operational rule "declare a utilization ceiling below 100% for
latency-sensitive resources" is provable (presence).

### 4.3 Universal Scalability Law -- depth note, xref design corpus -- live-verified [S14 in design corpus, reaffirmed]

**Principle (depth beyond design corpus)**: USL's two coefficients --
sigma (contention, serialization e.g. lock waits, Amdahl's fixed-fraction
special case) and kappa (coherency/crosstalk, the RETROGRADE term from
cross-node consistency traffic, e.g. cache-coherence or distributed
consensus overhead that grows worse than linearly with N) -- are fit from
MEASURED throughput-vs-concurrency data points, not assumed; in practice
this means USL is a POST-HOC diagnostic (fit the curve, read off which
coefficient dominates the ceiling) more often than a predictive design
tool, and Gunther explicitly warns against extrapolating far beyond the
measured concurrency range.

**Citation**: Neil J. Gunther, "A General Theory of Computational
Scalability Based on Rational Functions," arXiv:0808.1431, 2008;
Gunther, *Guerrilla Capacity Planning*, Springer, 2007, ch. 4-5 for the
fitting methodology. Cross-linked to design corpus sec. 6.

**Scale**: any system where throughput-vs-concurrency data can be
gathered across a range of load levels.

**Strata-checkability**: advisory (a curve-fitting model, not a static
code fact).

### 4.4 Amdahl's and Gustafson's Laws -- reconstructed/well-known [P3]

**Principle**: Amdahl's Law bounds speedup from parallelizing a FIXED
workload by the serial fraction (speedup <= 1/(s + (1-s)/N) as N -> infinity
approaches 1/s); Gustafson's Law reframes the same tradeoff for a
workload that SCALES WITH the available parallelism (speedup grows
roughly linearly with N when problem size grows with it), correcting the
common misapplication of Amdahl to scale-out workloads where the dataset
itself grows.

**Citation**: Gene Amdahl, "Validity of the Single Processor Approach to
Achieving Large Scale Computing Capabilities," AFIPS Conference
Proceedings 30:483-485, 1967. John L. Gustafson, "Reevaluating Amdahl's
Law," Communications of the ACM 31(5):532-533, 1988.

**Scale**: parallel/concurrent workload design, single multi-core host
through distributed compute cluster.

**Strata-checkability**: advisory (a theoretical ceiling, not a runtime
fact) -- USL (4.3) is the empirically-fittable generalization that
subsumes Amdahl's fixed-serial-fraction case.

### 4.5 Coordinated omission -- live-verified [P5]

**Principle**: when a load generator (or any latency-measuring harness)
waits for a response before issuing the next fixed-interval request,
requests DELAYED by a slow response are never issued -- so the very
samples that would show the worst latency are the ones "coordinated" out
of the measurement, systematically undercounting tail latency, sometimes
by orders of magnitude, and rendering p99+ figures meaningless. The fix
is to measure INTENDED (scheduled) send time, not actual send time, so a
delayed response's true wait is attributed correctly (HdrHistogram's
"correct for coordinated omission" mode implements this).

**Citation**: Gil Tene, "How NOT to Measure Latency," QCon London 2013
(qconlondon.com/london2018/london-2013/.../How%20NOT%20to%20Measure%20Latency.html);
term coined and popularized by Tene circa 2013-2015, subsequently adopted
into YCSB (via an "intended latency" measurement option) and
HdrHistogram/wrk2.

**Scale**: any closed-loop or think-time-based load-testing harness;
directly relevant to capacity-planning benchmarks (CP-1/CP-2 below).

**Strata-checkability**: **provable (presence)** -- "a load-test/benchmark
harness that reports percentile latency corrects for coordinated
omission (open-loop or intended-latency model), or explicitly disclaims
that it does not" is a sharp, checkable claim; a percentile report with
no stated correction is a named red flag per Tene's own talk.

---

## 5. Latency (denominator: 4)

### 5.1 Percentiles vs averages -- reconstructed/well-known [P3]

**Principle**: an average collapses a distribution into a single number
that can be dominated by a majority-fast, minority-catastrophic bimodal
shape without ever showing the catastrophe; percentiles (p50/p90/p99/
p999) preserve the shape's tail, which is where user-perceived pain and
SLO violations concentrate. The choice of WHICH percentile to track (p99
vs p999) should match the fan-out/request-volume of the system (a
high-fan-out system's p99 problem becomes nearly everyone's problem --
see LT-2).

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.8 (Percentiles); reinforced by
Gil Tene's "latency is not a scalar" framing in [P5] above.

**Scale**: any single latency-measuring boundary.

**Strata-checkability**: **provable (presence)** -- "a latency SLO cites a
percentile, not a bare average" is directly checkable, and complements
OB-5's histogram-export obligation.

### 5.2 Tail latency amplification -- depth note, xref design corpus -- live-verified [S15 in design corpus, reaffirmed]

**Principle (depth beyond design corpus)**: for a fan-out request touching
N independent components each with p99 latency L, the probability that
AT LEAST ONE sub-request exceeds L grows toward 1 - 0.99^N as N grows --
e.g. at N=100 independent calls, roughly 63% of aggregate requests hit at
least one component's "rare" p99 event, converting a 1-in-100 tail event
into the COMMON case at the aggregate level. This is the quantitative
mechanism behind Dean & Barroso's headline claim and the reason
hedged/tied requests (issuing a duplicate request after a threshold delay
and taking the first winner) are a structural fix, not a workaround.

**Citation**: Jeffrey Dean, Luiz Andre Barroso, "The Tail at Scale,"
Commun. ACM 56(2):74-80, Feb 2013. Cross-linked to design corpus sec. 6.

**Scale**: fan-out/scatter-gather services specifically; the amplification
effect is negligible at low fan-out (N=1-2) and dominant at high fan-out
(N=100+).

**Strata-checkability**: **provable (presence)** for "a fan-out call site
declares its N and has a stated p99/p999 SLO accounting for amplification"
(duplicate of design corpus sec. 6 obligation, included here for the
performance-methodology cross-reference).

### 5.3 The coordinated-omission trap in latency measurement -- dup-link [P5]

Same underlying mechanism as QT-5 (sec. 4.5) -- included here as a
LATENCY-analysis-specific entry because the failure mode is most commonly
encountered when reading a percentile report rather than when designing
a load-test harness. Not double-counted in the denominator manifest
below (tagged as a cross-reference id).

### 5.4 Latency budgets and "numbers every engineer should know" -- reconstructed/well-known [P3]

**Principle**: maintaining an explicit LATENCY BUDGET (a fixed total
allowed latency decomposed across the call chain, e.g. "200ms total: 50ms
network, 100ms DB, 50ms serialization") turns an implicit hope into a
checkable allocation, and forces tradeoffs to be made explicitly at
design time rather than discovered in production. The companion practice
of memorizing/referencing orders-of-magnitude latency numbers (L1 cache
~1ns, RAM ~100ns, SSD ~100us, cross-datacenter round trip ~ms, per
Jeff Dean's widely circulated "Numbers Every Programmer Should Know")
calibrates intuition for which budget allocations are even physically
plausible.

**Citation**: the "numbers" table traces to Jeff Dean/Peter Norvig
(circulated internally at Google, publicly summarized e.g. at
computer.rip and multiple conference talks attributing it to Dean);
latency-budget practice is standard SRE/performance-engineering discipline,
treated in Gregg SysPerf2e ch. 2 sec. 2.8 and implicit throughout Google's
SRE book (already cited in design corpus sec. 5.2).

**Scale**: any multi-hop call chain with an end-to-end SLO.

**Strata-checkability**: **provable (presence)** -- "a multi-hop call
chain with an end-to-end SLO has a documented per-hop budget summing to
<= the SLO" is a concrete, decomposable, checkable obligation -- one of
the strongest candidates in this corpus for a real strata rule.

---

## 6. Capacity planning (denominator: 3)

### 6.1 Headroom, saturation points, load testing vs production -- reconstructed/well-known [P3]

**Principle**: capacity planning targets a HEADROOM margin below the
saturation point (the M/M/1 knee, sec. 4.2) rather than 100% utilization,
because both variance in real traffic and the latency cliff near
saturation make operating AT capacity fragile. Load testing approximates
but never fully replicates production (traffic mix drift, cold caches,
correlated failure modes, coordinated-omission-corrupted results if the
harness is naive) -- so capacity numbers derived purely from synthetic
load tests should be treated as a lower bound to validate against real
canary/production traffic, not a final answer.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.6 (Capacity Planning), Gunther's
*Guerrilla Capacity Planning* (cited 4.3) for the broader discipline.

**Scale**: single-service capacity planning through fleet-wide.

**Strata-checkability**: **provable (presence)** -- "a declared capacity
number has a stated headroom margin below its measured/modeled saturation
point" is checkable; "load-tested capacity claims cite whether the harness
corrects for coordinated omission" ties directly to QT-5/[P5].

### 6.2 Benchmark vs real workload -- reconstructed/well-known [P3]

**Principle**: a benchmark that doesn't match the real workload's
characterization (WA-3, workload characterization) measures the WRONG
thing precisely -- e.g. a benchmark with uniform key access when
production has power-law hot keys will systematically mis-predict cache
hit rates and thus latency. The discipline is to validate that a
benchmark's workload shape matches production before trusting its
numbers for capacity decisions.

**Citation**: Gregg SysPerf2e ch. 12 (Benchmarking) sec. 12.2-12.3
(benchmarking mistakes: unrepresentative workloads specifically named).

**Scale**: any synthetic-vs-production comparison.

**Strata-checkability**: advisory (workload-shape matching is a judgment
call), though "a benchmark used to justify a capacity decision states its
workload characterization and how it was validated against production"
is provable (presence).

### 6.3 Micro-benchmarking pitfalls -- live-verified [P6]

**Principle**: naive micro-benchmarks are routinely wrong by an order of
magnitude or more due to JIT warmup (measuring interpreted/uncompiled
code before the JIT has optimized the hot loop), dead-code elimination
(the compiler legally removes computation whose result is never observed
-- can make a benchmark appear 8-12x faster than reality per Shipilev's
own measurements), and constant folding (compile-time evaluation of
inputs that should have been runtime-variable). JMH (Java Microbenchmark
Harness) exists specifically to defeat these via forced warmup iterations,
Blackhole consumption of results to prevent DCE, and per-fork JVM
isolation; the same three pitfall CLASSES (warmup, DCE, constant folding)
recur in every JIT'd or heavily-optimizing-compiler language, not just
Java.

**Citation**: Aleksey Shipilev, "Java Microbenchmark Harness (the lesser
of two evils)," Devoxx 2013, shipilev.net/talks/devoxx-Nov2013-benchmarking.pdf;
JMH itself is Shipilev's OpenJDK contribution. Cross-domain generalization
of DCE/warmup pitfalls is independently documented per-language (e.g.
Go's `testing.B` docs warn of the same DCE class; Rust's `criterion` crate
exists for the same reason).

**Scale**: function/method-level micro-benchmarks specifically (does NOT
generalize cleanly to macro/system benchmarks, which have their own
pitfalls per 6.2).

**Strata-checkability**: **provable (presence)** -- "a micro-benchmark in
a JIT'd language uses a warmup phase and prevents dead-code elimination
of its result (e.g. via a harness like JMH/criterion, or explicit
sink/blackhole)" is a concrete, tool-detectable obligation.

---

## 7. Tuning (denominator: 3)

### 7.1 Measure-first, one-change-at-a-time -- reconstructed/well-known [P3]

**Principle**: tune based on a measured bottleneck (identified via USE/RED/
drill-down), change ONE variable, re-measure, and only keep the change if
it demonstrably helps -- the direct antidote to the random-change
anti-method (sec. 1.6). Compound changes make causal attribution
impossible; a regression introduced by change 2 can be masked or amplified
by change 1.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.5.16 (Tuning), explicitly framed
as the disciplined counterpart to the anti-methods of sec. 2.4.

**Scale**: universal -- kernel parameter through application config
through code-level hot-path change.

**Strata-checkability**: **provable (presence)** -- "a tuning-motivated
commit/config change has an attached before/after measurement" is
directly checkable evidence-attachment, analogous to frob's existing
evidence model; the ABSENCE of such evidence on a change touching a
tuning parameter is the random-change anti-method made into a lint rule.

### 7.2 Config vs code tuning -- reconstructed/well-known [P3]

**Principle**: the same bottleneck can often be addressed either by
CONFIGURATION (thread-pool size, cache TTL, buffer size, kernel sysctl)
or by CODE change (algorithmic fix, reducing allocation, batching); config
tuning is faster to iterate and roll back but has a narrower ceiling
(it cannot fix an O(n^2) algorithm), while code changes have a higher
ceiling but higher risk/review cost. The discipline is to exhaust
cheap, reversible config tuning as a diagnostic step even when the
eventual fix is code -- a config change that "fixes" a symptom localizes
which resource/parameter is implicated before committing to a code
change.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.5.16-2.5.17 and the
per-resource "tuning" subsections throughout ch. 6-10 (each resource
chapter separates "tunable parameters" from "code-level" fixes explicitly).

**Scale**: universal.

**Strata-checkability**: advisory (a strategy choice) -- though "a
tuning-parameter change is reviewed/reversible independent of a code
deploy" (i.e. config is not hard-coded into a binary requiring a
redeploy to revert) is a provable (presence) architectural obligation.

### 7.3 The danger of premature/cargo-cult tuning -- reconstructed/well-known [P3]

**Principle**: applying a tuning change copied from a blog post, a
different workload, or "best practice" folklore WITHOUT first measuring
that the tuned parameter is actually the bottleneck in THIS system is
cargo-cult tuning -- it risks zero benefit, wasted operational complexity,
or active harm (many "performance" sysctls are workload-specific and
actively regress a mismatched workload). This is the sec. 1.6 streetlight/
random-change anti-methods specialized to the tuning phase specifically,
and Gregg names it as one of the most common real-world performance
engineering failures because it superficially LOOKS like the disciplined
practice (a config change was made) while skipping the measurement step
that would justify it.

**Citation**: Gregg SysPerf2e ch. 2 sec. 2.5.16 explicit warning against
"tuning without justification"; the term "cargo-cult" applied to
performance tuning specifically is common practitioner usage traceable
to Richard Feynman's original "cargo cult science" framing (1974 Caltech
commencement address) adapted to engineering folklore.

**Scale**: universal.

**Strata-checkability**: **provable (presence)** -- identical checkable
shape to 7.1 ("a tuning change has an attached before/after measurement");
listed as its own entry because the FAILURE mode (change with no
measurement, justified only by "it's known to help") is itself a
useful, independently nameable strata rule distinct from the positive
practice.

---

## Coverage table (Phase 2 reconciliation)

| Category | Denominator | Done | Provable (presence) | Advisory | Blocked |
|---|---|---|---|---|---|
| 1. Methodologies | 7 | 7 | 3 (USE-checklist-decomposed, RED, checklist-existence) | 4 | 0 |
| 2. Resource analysis | 5 | 5 | 5 (all) | 0 | 0 |
| 3. Observability & profiling | 7 | 7 | 4 (off-CPU-for-IO-bound, tracing-evidence, histogram-not-average, USDT-contract) | 3 | 0 |
| 4. Queueing & scalability | 5 | 5 | 2 (Little's-Law cross-check, coordinated-omission disclosure) | 3 | 0 |
| 5. Latency | 4 | 4 | 3 (percentile-not-average, fan-out-SLO, latency-budget-sum) | 1 (dup-link, not counted separately) | 0 |
| 6. Capacity planning | 3 | 3 | 2 (headroom-stated, micro-benchmark-warmup-DCE) | 1 | 0 |
| 7. Tuning | 3 | 3 | 2 (measured-change-evidence, cargo-cult-absence-flag) | 1 | 0 |
| **Total** | **34** | **34** | **21** | **13** | **0** |

Live-verified this pass (fresh fetch/search, not book-recall): USE method
canonical page [P1], flame graphs ACM Queue citation [P4], RED method
origin [P2], coordinated omission / Gil Tene [P5], JMH/Shipilev DCE
mechanics [P6] -- 6 entries (5 unique citations, [P1] used twice).
Cross-referenced from the already-live-verified design corpus (Little's
Law S13, USL S14, Tail at Scale S15) without re-fetching -- 3 entries.
Remaining 25 entries are Gregg *Systems Performance* 2nd ed. chapter
content: stable, widely-cross-cited canonical material, marked
"reconstructed/well-known" per entry rather than claimed as fresh
citation-verification. No entry is flagged partial/unverifiable; the
corpus's sourcing risk is concentrated entirely in the 25
"reconstructed/well-known" entries, which rest on one author's book
(Gregg SysPerf2e) not independently re-fetched page-by-page this pass --
flagged here explicitly rather than glossed over, consistent with this
corpus's own sourcing-honesty bar.

**Phase 2 verdict**: 34/34 nodes done, 0 pending, 0 blocked. Denominator
reconciles.

---

## Cross-links

- `docs/design/system-design-corpus.md` sec. 6 (Performance & capacity) --
  design-level Little's Law / USL / Tail at Scale; this corpus goes one
  layer deeper into their operational mechanics (sec. 4.1, 4.3, 5.2 above).
- `docs/design/system-design-corpus.md` sec. 5.2 (Google SRE SLI/SLO/error
  budgets) -- this corpus's RED method (1.2) and latency-budget entry (5.4)
  are the metric-shape and decomposition companions to that SLO practice.
- `src/frob/perf/` (18 modules, including `_harness.py`, `_heat.py`,
  `_models.py`, `_profile.py`, `_rules.py`) -- existing frob performance
  tooling; the provable
  (presence) entries above are candidate obligations for `_rules.py`, not
  prescriptions for how it should be implemented.

## DENOMINATOR MANIFEST

- id: PM-1 | catalog: system-performance-corpus-sec-1 | checkability: tier1-provable-decomposed | source: live
- id: PM-2 | catalog: system-performance-corpus-sec-1 | checkability: tier1-provable | source: live
- id: PM-3 | catalog: system-performance-corpus-sec-1 | checkability: tier2-advisory | source: reconstructed
- id: PM-4 | catalog: system-performance-corpus-sec-1 | checkability: tier2-advisory | source: reconstructed
- id: PM-5 | catalog: system-performance-corpus-sec-1 | checkability: tier2-advisory | source: reconstructed
- id: PM-6 | catalog: system-performance-corpus-sec-1 | checkability: tier2-advisory-negative-check | source: reconstructed
- id: PM-7 | catalog: system-performance-corpus-sec-1 | checkability: tier2-advisory | source: reconstructed
- id: RA-1 | catalog: system-performance-corpus-sec-2 | checkability: tier1-provable | source: reconstructed
- id: RA-2 | catalog: system-performance-corpus-sec-2 | checkability: tier1-provable | source: reconstructed
- id: RA-3 | catalog: system-performance-corpus-sec-2 | checkability: tier1-provable | source: reconstructed
- id: RA-4 | catalog: system-performance-corpus-sec-2 | checkability: tier1-provable | source: reconstructed
- id: RA-5 | catalog: system-performance-corpus-sec-2 | checkability: tier1-provable | source: live
- id: OB-1 | catalog: system-performance-corpus-sec-3 | checkability: tier2-advisory-evidence-obligation | source: live
- id: OB-2 | catalog: system-performance-corpus-sec-3 | checkability: tier2-advisory | source: reconstructed
- id: OB-3 | catalog: system-performance-corpus-sec-3 | checkability: tier1-provable | source: reconstructed
- id: OB-4 | catalog: system-performance-corpus-sec-3 | checkability: tier1-provable-evidence-obligation | source: reconstructed
- id: OB-5 | catalog: system-performance-corpus-sec-3 | checkability: tier1-provable | source: reconstructed
- id: OB-6 | catalog: system-performance-corpus-sec-3 | checkability: tier1-provable | source: reconstructed
- id: OB-7 | catalog: system-performance-corpus-sec-3 | checkability: tier2-advisory | source: reconstructed
- id: QT-1 | catalog: system-performance-corpus-sec-4 | checkability: tier1-provable-crosscheck | source: live-xref-design-corpus
- id: QT-2 | catalog: system-performance-corpus-sec-4 | checkability: tier2-advisory | source: reconstructed
- id: QT-3 | catalog: system-performance-corpus-sec-4 | checkability: tier2-advisory | source: live-xref-design-corpus
- id: QT-4 | catalog: system-performance-corpus-sec-4 | checkability: tier2-advisory | source: reconstructed
- id: QT-5 | catalog: system-performance-corpus-sec-4 | checkability: tier1-provable | source: live
- id: LT-1 | catalog: system-performance-corpus-sec-5 | checkability: tier1-provable | source: reconstructed
- id: LT-2 | catalog: system-performance-corpus-sec-5 | checkability: tier1-provable | source: live-xref-design-corpus
- id: LT-3 | catalog: system-performance-corpus-sec-5 | checkability: tier1-provable-duplink-QT-5 | source: live
- id: LT-4 | catalog: system-performance-corpus-sec-5 | checkability: tier1-provable | source: reconstructed
- id: CP-1 | catalog: system-performance-corpus-sec-6 | checkability: tier1-provable | source: reconstructed
- id: CP-2 | catalog: system-performance-corpus-sec-6 | checkability: tier2-advisory | source: reconstructed
- id: CP-3 | catalog: system-performance-corpus-sec-6 | checkability: tier1-provable | source: live
- id: TN-1 | catalog: system-performance-corpus-sec-7 | checkability: tier1-provable | source: reconstructed
- id: TN-2 | catalog: system-performance-corpus-sec-7 | checkability: tier2-advisory | source: reconstructed
- id: TN-3 | catalog: system-performance-corpus-sec-7 | checkability: tier1-provable | source: reconstructed
- TOTAL: 34
