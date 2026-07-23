# System-design corpus: reliability, distributed systems, scale

Exhaustive, cited corpus of system-design knowledge and lessons for
building good systems at every scale (single service/monolith up to
hyperscale), enumerated by category against a denominator per the
`exhaustive-research` frontier method. Extends, and does not duplicate,
two existing documents:

- `docs/design/structural-linter-adversarial-hardening.md` -- the strata
  anti-evasion/conformance-totality structure this corpus's
  STRATA-CHECKABILITY tags feed.
- `docs/design/architecture-check-catalog.md` -- the earlier check
  catalog. Its `5. Systems architecture` section (5.1-5.8) self-flagged
  most systems citations as "general knowledge, not independently
  re-verified via search." This corpus re-derives those same topics
  against live primary sources and records, per entry, which citations
  are now upgraded from folklore/reconstructed to live-verified (see
  "Upgrades over architecture-check-catalog.md" at the end).

This corpus is the evidence base for T-0331 (EPIC strata senior-systems
checks). Every entry carries a STRATA-CHECKABILITY tag: **provable**
(strata/arch could statically model-check or prove this against code or
model), **advisory** (a real lesson, but a matter of judgment/tradeoff,
not a bare-fact proof), or **not-checkable** (a property runtime/chaos
evidence must establish, not statics).

## Method note (exhaustive-research frontier)

Universe enumerated category-by-category (Phase 0) before any sourcing
began; each category's denominator is stated in its heading and
reconciled in the coverage table at the end (Phase 2). Sourcing used
WebSearch against canonical repositories (research.google, usenix.org,
dl.acm.org, arxiv.org, sre.google, aws.amazon.com/builders-library,
jepsen.io, lamport.azurewebsites.net, 12factor.net, brendangregg.com,
perfdynamics.com, engineering blogs) during this pass; results are marked
live-verified where a canonical URL and exact citation were confirmed
via search results in this session, and marked reconstructed/well-known
where the concept is uncontested canon but the exact enumerated
sub-list was not independently re-fetched this pass -- following the
same honesty convention as `architecture-check-catalog.md`.

---

## 1. Distributed-systems fundamentals (denominator: 6 sub-topics)

### 1.1 Eight Fallacies of Distributed Computing -- live-verified [S1]

Original list: L. Peter Deutsch (Sun Fellow) stated 7 in 1994, drawing on
4 fallacies Bill Joy and Dave Lyon had already named in "The Fallacies of
Networked Computing"; James Gosling added the 8th ("the network is
homogeneous") around 1997. Full list: (1) the network is reliable, (2)
latency is zero, (3) bandwidth is infinite, (4) the network is secure,
(5) topology doesn't change, (6) there is one administrator, (7)
transport cost is zero, (8) the network is homogeneous. [S1]

Coincident finding, matching `architecture-check-catalog.md`'s note: the
*current* Microsoft Azure Architecture Center page lists a modified
variant dropping "transport cost is zero" and "the network is
homogeneous" in favor of "component versioning is simple" and
"observability implementation can be delayed" -- both lists are recorded
since they diverge in content, not just phrasing.

| Item | STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|---|
|Network reliability|advisory (backs provable proxies below)|all|--|
|Latency non-zero|**provable**|distributed|declared cross-service edge with no timeout annotation|
|Bandwidth finite|**provable**|distributed|unbounded payload/streaming edge with no size/rate bound declared|
|Network insecure|**provable**|distributed|inter-service edge with no authn/encryption-in-transit annotation|
|Topology changes|**provable**|distributed|hardcoded host/IP instead of service-discovery/DNS reference|
|Single administrator false|advisory|org-scale|--|
|Transport cost nonzero|advisory|hyperscale|--|
|Heterogeneous network / component versioning simple (Azure variant) / observability can be delayed (Azure variant)|**provable**|distributed|version-compat check on wire schema (5.6); instrumentation-presence check (this doc, sec. 7)|

### 1.2 CAP theorem and PACELC -- live-verified [S2][S3]

Eric Brewer conjectured CAP (Consistency, Availability, Partition
tolerance -- pick 2 of 3 under a partition) at PODC 2000; formally proved
by Seth Gilbert and Nancy Lynch, "Brewer's Conjecture and the Feasibility
of Consistent, Available, Partition-Tolerant Web Services," SIGACT News
33(2), 2002. [S2] Daniel Abadi extended it: "Consistency Tradeoffs in
Modern Distributed Database System Design: CAP is Only Part of the
Story," IEEE Computer, 2012 -- PACELC: if Partitioned, choose
Availability or Consistency; Else (no partition), choose Latency or
Consistency -- because CAP is silent on the latency/consistency tradeoff
that exists even when the network is healthy. [S3]

| STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|
|**advisory**|distributed, esp. multi-region|a data store's declared consistency level (5.6) is the checkable artifact; CAP/PACELC itself is a theorem about tradeoffs, not a fact about one store -- proof-mode `reasoned-discharge`|

### 1.3 FLP impossibility -- live-verified [S4]

Michael J. Fischer, Nancy A. Lynch, Michael S. Paterson, "Impossibility
of Distributed Consensus with One Faulty Process," Journal of the ACM
32(2):374-382, April 1985 -- won the Dijkstra Prize. Proves no
deterministic consensus protocol can guarantee termination in a fully
asynchronous system with even one crash-faulty process. [S4]

| STRATA-CHECKABILITY | Scale | Note |
|---|---|---|
|**not-checkable**|any system using consensus|a theorem, not a code fact; it explains WHY every consensus system (2) below trades off liveness/timing assumptions -- it justifies the existence of the provable "declared consensus protocol + failure-detector/timeout assumption" proxy in 2.x, but is not itself checkable|

### 1.4 The end-to-end argument -- live-verified [S5]

J.H. Saltzer, D.P. Reed, D.D. Clark, "End-to-End Arguments in System
Design," ACM Transactions on Computer Systems 2(4):277-288, Nov 1984.
Principle: a function (reliability, security, dedup, crash-recovery)
requiring correctness can only be *completely and correctly* implemented
with the knowledge and help of the endpoints/application; implementing it
lower in the stack alone is redundant or insufficient, though a lower-layer
optimization for performance may still be worthwhile. [S5]

| STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|
|**provable** (presence-of-endpoint-check proxy) / advisory (placement judgment)|all|a reliability/integrity/security property claimed to be provided by infrastructure (TCP, a message broker's "exactly-once") with no corresponding application-level check (checksum, idempotency key, ack) at the endpoint -- infra-only claims are a checkable absence|

### 1.5 Lamport / vector clocks and event ordering -- live-verified [S6]

Leslie Lamport, "Time, Clocks, and the Ordering of Events in a
Distributed System," Communications of the ACM 21(7), July 1978 --
introduced the happened-before relation and logical (Lamport) clocks
without relying on synchronized physical clocks; won the 2000 PODC
Influential Paper (Dijkstra) award. [S6] Vector clocks (Fidge 1988,
Mattern 1989) generalize this to detect concurrency, not just a total
order -- reconstructed/well-known, not independently re-fetched this
pass.

| STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|
|**provable** (presence proxy)|distributed, esp. leaderless/multi-writer (Dynamo-style, 3.3)|a store declared with concurrent multi-writer semantics and no declared conflict-resolution mechanism (LWW-with-physical-clock, vector clock, CRDT) -- physical-clock-only ordering under concurrent writes is the checkable anti-pattern|

### 1.6 Consistency models (linearizable / sequential / causal / eventual / read-your-writes / monotonic) -- reconstructed/well-known

Canon hierarchy from Kleppmann DDIA ch. 9 and Herlihy & Wing's
"Linearizability: A Correctness Condition for Concurrent Objects," ACM
TOPLAS 12(3), 1990 (linearizability's origin paper -- not independently
re-fetched this pass, cited from established knowledge).

| STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|
|**provable** (declaration-presence, not the guarantee itself)|distributed data stores at all scales|a data store/replica edge with no declared consistency-level annotation in the model -- duplicate of architecture-check-catalog.md sec 5.6 "Eventual Consistency" proxy, kept here as the fundamentals-level entry|

---

## 2. Consensus & coordination (denominator: 9 named mechanisms)

| Name | Primary source | STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|---|---|
|Paxos|Leslie Lamport, "The Part-Time Parliament," ACM TOCS 16(2), 1998 (original, notoriously hard to read); "Paxos Made Simple," ACM SIGACT News 32(4), Dec 2001 -- live-verified, canonical PDF at lamport.azurewebsites.net/pubs/paxos-simple.pdf [S7]|**provable** (presence)|distributed coordination, foundational|a component declared as a "singleton"/leader role with multiple replicas and no named consensus protocol (Paxos/Raft/Zab/VR) annotated|
|Multi-Paxos|Lamport's "Paxos Made Simple" describes the multi-instance optimization directly [S7]; also Chubby (below) implements it|**provable**|as above|dup of Paxos proxy|
|Raft|Diego Ongaro, John Ousterhout, "In Search of an Understandable Consensus Algorithm," USENIX ATC 2014, Best Paper -- live-verified [S8]|**provable**|as above|dup of Paxos proxy|
|Zab (ZooKeeper Atomic Broadcast)|Benjamin Reed, Flavio P. Junqueira, "A simple totally ordered broadcast protocol," LADIS 2008 -- reconstructed/well-known, not independently re-fetched this pass|**provable**|as above|dup of Paxos proxy|
|Viewstamped Replication (VR)|Brian Oki, Barbara Liskov, "Viewstamped Replication: A New Primary Copy Method to Support Highly-Available Distributed Systems," PODC 1988; revisited: Liskov & Cowling, "Viewstamped Replication Revisited," MIT-CSAIL-TR-2012-021 -- reconstructed/well-known, not independently re-fetched this pass|**provable**|as above|dup of Paxos proxy|
|2PC (Two-Phase Commit)|Jim Gray, "Notes on Data Base Operating Systems," 1978 (classical database-systems literature) -- reconstructed/well-known|**provable**|distributed transactions|a multi-service business transaction with no declared 2PC/3PC/saga coordinator (dup of architecture-check-catalog.md 5.4 Saga proxy)|
|3PC (Three-Phase Commit)|Dale Skeen, "Nonblocking Commit Protocols," SIGMOD 1981 -- reconstructed/well-known|**provable**|as above|dup of 2PC proxy|
|Leases|Gray & Cheriton, "Leases: An Efficient Fault-Tolerant Mechanism for Distributed File Cache Consistency," SOSP 1989 -- reconstructed/well-known; production use confirmed live via the Chubby paper (Mike Burrows, "The Chubby Lock Service for Loosely-Coupled Distributed Systems," OSDI 2006 -- live-verified [S9], primary use case is leader election for GFS/Bigtable)|**provable** (presence)|distributed coordination|a singleton/leader role held via a lock with no declared lease TTL/expiry (unbounded lock = split-brain risk on holder crash)|
|Quorums|Read/write quorum intersection is classical (Gifford, "Weighted Voting for Replicated Data," SOSP 1979) -- reconstructed/well-known; used directly by Dynamo's N/R/W model (3.3)|**provable**|replicated stores|declared R+W <= N (no read/write quorum overlap guaranteed) on a store claiming strong consistency|
|CRDTs (Conflict-free Replicated Data Types)|Marc Shapiro, Nuno Preguica, Carlos Baquero, Marek Zawirski, "Conflict-free Replicated Data Types," INRIA Research Report 7687 / SSS 2011 -- reconstructed/well-known|**provable** (presence)|leaderless/offline-first multi-writer|a store declared multi-writer with ad hoc merge logic instead of a named CRDT type -- unprincipled merge-function is the checkable anti-pattern|

---

## 3. Replication & partitioning (denominator: 7 topics, anchored on Kleppmann DDIA + Dynamo)

Anchor: Martin Kleppmann, *Designing Data-Intensive Applications*,
O'Reilly, 2017, Part II ("Distributed Data") -- **chapter structure
live-verified this pass** via Playwright against O'Reilly's own hosted
page (`oreilly.com/library/view/designing-data-intensive-applications/9781491903063/`),
confirming the book's own 3-part, 12-chapter structure exactly as cited
throughout this document: Part I "Foundations of Data Systems" (ch. 1-4),
Part II "Distributed Data" (ch. 5-9: Replication, Partitioning,
Transactions, The Trouble with Distributed Systems, Consistency and
Consensus), Part III "Derived Data" (ch. 10-12: Batch Processing, Stream
Processing, The Future of Data Systems) -- full-text content itself was
not re-fetched (no accessible free full-text primary source online; ISBN
978-1491903063, 2nd ed. ISBN 978-1098119058 is the citation of record),
but every DDIA chapter-number citation elsewhere in this document is now
confirmed to point at a real, correctly-numbered chapter rather than a
reconstructed guess. Dynamo anchor live-verified: Giuseppe DeCandia et
al., "Dynamo: Amazon's Highly Available Key-value Store," SOSP 2007
[S10].

| Topic | STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|---|
|Leader-follower (single-leader) replication|**provable**|small-to-mid|a write path that bypasses the declared leader and writes a follower directly|
|Multi-leader replication|**provable** (presence) / advisory (conflict policy quality)|multi-region|multiple write-accepting replicas declared with no conflict-resolution policy (LWW/CRDT/app-level) annotated|
|Leaderless / Dynamo-style replication|**provable**|Dynamo, Cassandra, Riak-class stores|N/R/W parameters declared with R+W <= N (dup of 2.x quorum proxy); Dynamo's own techniques -- consistent hashing, sloppy quorums + hinted handoff, vector clocks for conflict detection, read-repair, anti-entropy via Merkle trees, gossip-based membership -- are the checkable presence/absence set per [S10]|
|Sharding strategies (range, hash, directory-based)|**provable** (presence) / advisory (choice quality)|horizontally-scaled stores|a store declared at high-scale with no partitioning key/strategy annotated|
|Consistent hashing|**provable** (presence)|Dynamo-style, CDNs, caches|a hash-partitioned store with a non-consistent (mod-N) hash function -- full-reshuffle-on-resize is the anti-pattern; Dynamo's use of consistent hashing with virtual nodes is the canonical case [S10]|
|Rebalancing|advisory|any sharded store as it grows|operational; the checkable proxy is presence of a declared rebalancing mechanism vs. manual/ad hoc resharding|
|Hot-partition handling|**provable** (presence) / advisory (mitigation choice)|high-throughput sharded systems|a partition key declared with low cardinality (e.g. boolean, small enum) on a high-write-volume store -- the AWS Builders' Library shuffle-sharding technique (below, sec. 5) is a named mitigation|

---

## 4. Data-intensive systems (Kleppmann DDIA canon, denominator: 8 topics)

| Topic | Primary source | STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|---|---|
|LSM-tree vs B-tree storage engines|Kleppmann DDIA ch. 3; O'Neil et al., "The Log-Structured Merge-Tree (LSM-Tree)," Acta Informatica 33(4), 1996 (LSM origin, reconstructed/well-known) -- storage-engine choice|advisory|storage-engine design|not a per-flow checkable fact; a modeling/tooling choice|
|Transactions & isolation levels|Kleppmann DDIA ch. 7; Berenson et al., "A Critique of ANSI SQL Isolation Levels," SIGMOD 1995 -- reconstructed/well-known|**provable** (declaration presence)|any multi-write op|a multi-row/multi-table mutation with no declared transactional boundary/isolation level|
|Distributed transactions|Kleppmann DDIA ch. 9; dup of sec. 2 2PC/3PC/Saga|**provable**|cross-service writes|dup of Saga/2PC proxy|
|Batch vs stream processing|Kleppmann DDIA ch. 10-11|advisory|data pipelines|architectural choice, not a single checkable fact|
|Exactly-once processing|Kleppmann DDIA ch. 11; in practice achieved via idempotent-receiver + dedup, not a true transport guarantee|**provable**|messaging/event pipelines|dup of Idempotent Receiver proxy (architecture-check-catalog.md 5.4)|
|Idempotency|dup of sec. 6/architecture-check-catalog.md 5.6|**provable**|mutating handlers on retryable edges|dup of Idempotency proxy|
|Outbox / saga patterns|Chris Richardson, microservices.io pattern catalog -- confirmed by architecture-check-catalog.md [C13] to be Richardson-sourced, NOT Azure|**provable**|cross-service writes+events|dup of Outbox/Saga proxies|
|Change data capture (CDC)|Kleppmann DDIA ch. 11 "Change Data Capture" section -- reconstructed/well-known; production examples: Debezium (open-source CDC connector project)|**provable** (presence)|event-driven architectures reading DB state|a service polling another service's database directly instead of consuming a declared CDC/event stream -- direct-DB-read-across-a-service-boundary is the checkable anti-pattern (also a Single-Source-of-Truth / API-boundary violation)|

---

## 5. Reliability & resilience (denominator: 4 primary-source clusters)

### 5.1 Nygard *Release It!* stability patterns -- live-verified this pass

Michael T. Nygard, *Release It! Design and Deploy Production-Ready
Software*, 2nd ed., Pragmatic Bookshelf, 2018. **Resolved this pass**:
Playwright reached O'Reilly's hosted Contents panel directly (the prior
403 was WebFetch-specific, not a real paywall on the TOC) and confirmed
the publisher's own chapter 4/5 headings: **12** stability anti-patterns,
**12** stability patterns (corrected from the prior pass's 13/13
secondary-sourced estimate -- see architecture-check-catalog.md sec. 5.2
and design-pattern-catalog.md sec. 6 for the full corrected name list and
citation [C14], not re-transcribed here to avoid duplication).
STRATA-CHECKABILITY tags per pattern are recorded in
architecture-check-catalog.md sec. 5.2; this corpus does not re-litigate
them.

### 5.2 Google SRE book -- SLI/SLO/SLA, error budgets, toil -- live-verified [S11]

Betsy Beyer, Chris Jones, Jennifer Petoff, Niall Richard Murphy (eds.),
*Site Reliability Engineering: How Google Runs Production Systems*,
O'Reilly, 2016, free at sre.google/sre-book/; ch. 4 "Service Level
Objectives." SLI = a quantitative measure of a service-level aspect
(latency, error rate, throughput, availability); SLO = a target
value/range for an SLI; SLA = a business contract with consequences,
always looser than the internal SLO; error budget = 1 - SLO (e.g. 99.9%
SLO = 0.1% error budget), spent deliberately to balance velocity against
reliability. [S11] The SRE Workbook (sre.google/workbook/) adds worked
error-budget-policy and SLO-document examples.

| STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|
|**provable** (declaration presence)|every service, any scale|a service node declared in the model with no SLO/error-budget annotation -- dup of architecture-check-catalog.md 5.5 SLI/SLO/Error-Budget proxy, elevated here to primary-source-verified|

### 5.3 Chaos engineering -- reconstructed/well-known

Netflix's Chaos Monkey (open-sourced 2012) and the "Principles of Chaos
Engineering" (principlesofchaos.org, authored by the Netflix chaos team
including Casey Rosenthal) are the canonical origin; not independently
re-fetched live this pass.

| STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|
|**not-checkable** (the practice itself is runtime evidence, not a static fact)|services with declared critical dependencies/SPOFs|dup of "Test Harness (failure injection)" proxy in architecture-check-catalog.md 5.2 -- presence of a fault-injection CI target is the *provable* proxy for "chaos testing exists," but whether it caught anything is not-checkable statically|

### 5.4 AWS Builders' Library (Marc Brooker et al.) -- live-verified [S12]

"Timeouts, retries, and backoff with jitter," Marc Brooker, AWS
Builders' Library, aws.amazon.com/builders-library/ -- confirmed live:
Amazon best practice is a timeout (connection + request) on every remote
call, even in-process across a boundary; retries must be used cautiously
because they can amplify load on an already-overloaded dependency; jitter
(randomized delay) prevents synchronized retry storms and should be
applied broadly to periodic/delayed work, not just retries. [S12]
Companion articles in the same series (title-confirmed via search,
content reconstructed/well-known, not independently re-fetched this
pass): "Making retries safe with idempotent APIs," "Avoiding fallback in
distributed systems," "Using load shedding to avoid overload," "Health
checks and load balancing," shuffle sharding (isolating tenants/requests
onto virtual shard subsets to bound blast radius of a hot/bad shard).

| STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|
|Timeout|**provable**|every remote/cross-boundary call|network client construction / call site with no explicit timeout argument -- direct primary-sourced backing for T-0331's REL2xx TIMEOUT check|
|Retry+backoff+jitter|**provable** (presence) / advisory (correctness of backoff math)|as above|a retry loop with fixed-interval or no-jitter backoff, or retry on a non-idempotency-declared op|
|Idempotent receiver|**provable**|mutating handlers reachable by a retryable edge|dup of sec. 4 proxy|
|Load shedding|**provable** (presence)|ingress under burst load|ingress edge with no declared rate-limit/shed policy|
|Shuffle sharding|advisory|multi-tenant high-scale systems|a mitigation strategy, not a single presence/absence fact -- tier 3|

---

## 6. Performance & capacity (denominator: 5 named tools/laws)

| Name | Primary source | STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|---|---|
|Little's Law (L = lambda W)|John D. C. Little, "A Proof for the Queuing Formula: L = lambda W," Operations Research 9(3):383-387, 1961 -- live-verified [S13]|advisory|capacity planning at all scales|a relationship among concurrency/arrival-rate/latency, not itself a single code fact -- feeds capacity-modeling tools, tier 3|
|Universal Scalability Law (USL)|Neil J. Gunther, originally presented at CMG 1993; peer-reviewed as "A General Theory of Computational Scalability Based on Rational Functions," arXiv:0808.1431, 2008 -- live-verified [S14]. Subsumes Amdahl's Law (fixed serial fraction) and adds a coherency-delay (retrograde) term Gunther calls "crosstalk."|advisory|capacity/scalability modeling|a model fit against benchmark data, not a static code fact|
|Queueing theory basics (M/M/1 etc.)|classical (Erlang, Kendall notation) -- reconstructed/well-known|advisory|capacity planning|as above|
|"The Tail at Scale"|Jeffrey Dean, Luiz Andre Barroso, Communications of the ACM 56(2):74-80, Feb 2013 -- live-verified [S15]. Core lesson: at scale, even a rare (e.g. p99) per-component latency hiccup affects a large fraction of aggregate requests because a request commonly fans out to many components; tail-tolerant techniques (hedged requests, tied requests, micro-partitioning, selective replication) treat latency variability the way fault-tolerant computing treats crashes.|**provable** (presence) / advisory (technique choice)|fan-out/scatter-gather services, hyperscale|a fan-out call site issuing N parallel sub-requests with no hedging/cancellation-of-losers policy and no declared p99/p999 SLO (dup of sec. 5.2 SLO proxy, specialized to tail latency)|
|USE Method (Utilization/Saturation/Errors)|Brendan Gregg, "The USE Method," brendangregg.com/usemethod.html -- live-verified [S16]. Checklist: for every resource, check utilization (% busy), saturation (queue-length/wait), errors -- systematic bottleneck-finding, contrasted with the RED method (Rate/Errors/Duration, for request-driven services rather than resources) which Gregg's own site and community sources attribute to Tom Wilkie -- reconstructed/well-known, not independently re-fetched this pass.|**provable** (instrumentation presence)|infra/resource-level monitoring, all scales|a declared resource (CPU/disk/network/pool) with metrics emitted for none of utilization/saturation/errors|

Brendan Gregg's broader performance methodology (USE method, the flame
graph visualization, the "Linux Performance" checklists) is
reconstructed/well-known beyond the USE method page itself; not
independently re-fetched item-by-item this pass.

---

## 7. Observability (denominator: 4 topics)

| Name | Primary source | STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|---|---|
|Three pillars (metrics/logs/traces)|Industry-canon framing (Distributed Systems Observability, Cindy Sridharan, O'Reilly 2018 report) -- reconstructed/well-known, not independently re-fetched this pass|**provable** (presence)|every service boundary|dup of architecture-check-catalog.md 5.5 RED/USE/Golden-Signals proxy, generalized|
|Distributed tracing (Dapper)|Benjamin H. Sigelman et al., "Dapper, a Large-Scale Distributed Systems Tracing Infrastructure," Google Technical Report, 2010 -- live-verified [S17]. Design goals: low overhead, application-level transparency (no manual per-call instrumentation burden on average developers), ubiquitous deployment; achieved via sampling and instrumenting a small number of common libraries rather than every call site. Directly inspired OpenTracing/OpenTelemetry, Zipkin, Jaeger.|**provable**|distributed/microservice, esp. deep call chains|a cross-service call site with no propagated trace/correlation-id header -- dup + primary-sourced elevation of architecture-check-catalog.md 5.5 Correlation-IDs proxy|
|High-cardinality / structured events (Honeycomb / Charity Majors)|Charity Majors, Liz Fong-Jones, George Miranda, *Observability Engineering*, O'Reilly, 2022; Majors's "Observability != Monitoring" and related Honeycomb engineering blog posts -- reconstructed/well-known, not independently re-fetched live this pass. Core lesson: wide structured events (not pre-aggregated metrics) preserve high-cardinality/high-dimensionality fields needed to debug novel/unknown-unknown failures.|advisory (methodology choice) / **provable** (cardinality-label anti-pattern presence)|services with unpredictable failure modes, esp. multi-tenant|dup of architecture-check-catalog.md 5.5 Cardinality-control proxy: a metric-emission call using a high-cardinality value (user id, request id) as a label/tag|
|SLO-based alerting|Google SRE book ch. 5-6 (Beyer et al. 2016, sre.google/sre-book/) -- same primary source as sec. 5.2 [S11]. Lesson: alert on symptom (SLO burn rate) not cause; multi-window multi-burn-rate alerting avoids both slow-burn misses and noisy short-burn false pages.|**provable** (presence)|any service with a declared SLO|an alerting rule keyed to a raw resource threshold (e.g. "CPU>80%") instead of the declared SLO/error-budget burn rate|

---

## 8. Messaging/eventing & delivery semantics (denominator: 6 topics)

| Name | Primary source | STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|---|---|
|At-most-once|classical messaging-semantics taxonomy -- reconstructed/well-known|**provable** (declaration presence)|any queue/topic edge|a queue/topic edge with no declared delivery-semantics annotation (dup of architecture-check-catalog.md 5.6 Delivery-semantics proxy)|
|At-least-once|as above|**provable**|as above|as above; forces idempotent-consumer requirement on the receiving handler|
|Exactly-once|as above; in practice "effectively-once" = at-least-once delivery + idempotent processing (Kreps, below) -- reconstructed/well-known|**provable** (presence) / not-checkable (true exactly-once transport is not achievable per FLP/end-to-end reasoning, sec 1.3/1.4)|as above|a handler claiming exactly-once semantics with no idempotency key/dedup-store check -- the checkable proxy is the *absence* of the supporting mechanism, not the semantic claim itself|
|Idempotent consumers|dup of sec. 4/5.4|**provable**|as above|dup proxy|
|Ordering guarantees|Kleppmann DDIA ch. 11; per-partition ordering is Kafka's model (see Kreps below)|**provable** (declaration presence)|ordered-processing requirements (e.g. per-key state machines)|a partition/shard key with an ordering requirement declared and no explicit ordering-guarantee/single-partition-key annotation (dup of architecture-check-catalog.md 5.4 Sequential-Convoy proxy)|
|The log abstraction|Jay Kreps, "The Log: What every software engineer should know about real-time data's unifying abstraction," LinkedIn Engineering blog, Dec 2013, engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying -- live-verified [S18]. Core lesson: a log (append-only, totally-ordered-by-time record sequence) is the unifying abstraction underlying databases, replication, Paxos-family consensus, and stream processing, via the State Machine Replication principle -- identical deterministic processes fed the same inputs in the same order reach the same state. Directly motivated Kafka's design.|advisory (conceptual framing) / **provable** (presence, for the DLQ/poison-message corollary)|event-driven architectures, all scales|dead-letter/poison-message handling: a consumer with no declared DLQ/retry-limit for a message that repeatedly fails processing -- the checkable corollary of the log abstraction's "the log is the source of truth, consumers may fall behind or fail" framing|

---

## 9. Deployment/infra at scale (denominator: 6 topics)

| Name | Primary source | STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|---|---|
|12-Factor App|12factor.net -- already live-verified word-for-word in architecture-check-catalog.md [C12]; not re-transcribed here, referenced by pointer to avoid duplication.|**provable** (mixed per-factor, see architecture-check-catalog.md 5.3)|--|--|
|Immutable infrastructure|Kief Morris, *Infrastructure as Code*, O'Reilly (concept popularized by Chad Fowler's 2013 blog post "Trash Your Servers and Burn Your Code") -- reconstructed/well-known, not independently re-fetched this pass|**provable** (presence)|any deployed service|a deployment pipeline/runbook step that SSHes into and mutates a running instance instead of replacing it with a new immutable artifact|
|Blue-green / canary / progressive delivery|Martin Fowler, "BlueGreenDeployment" (martinfowler.com/bliki/BlueGreenDeployment.html) and "CanaryRelease" (martinfowler.com/bliki/CanaryRelease.html) -- reconstructed/well-known, not independently re-fetched this pass|**provable** (presence)|services with a deploy pipeline|a deploy pipeline with no staged/canary rollout step (100%-at-once deploy) for a service declared user-facing/critical|
|Autoscaling|reconstructed/well-known, cloud-provider canon (AWS/GCP/Azure autoscaling docs)|advisory (policy tuning) / **provable** (presence)|elastic-load services|a service declared with variable/bursty traffic and a fixed replica count|
|Multi-region & disaster recovery (RTO/RPO)|Google Cloud Architecture Center / AWS Well-Architected Reliability Pillar define RTO (Recovery Time Objective) and RPO (Recovery Point Objective) as the standard DR metrics -- reconstructed/well-known, not independently re-fetched live this pass|**provable** (declaration presence)|services with a declared criticality/availability tier|a service declared critical/tier-1 with no RTO/RPO annotation or DR runbook reference|
|Cell-based architecture|AWS Builders' Library / Well-Architected: "cell-based architecture" isolates capacity into independent cells to bound blast radius (related to shuffle sharding, sec. 5.4) -- reconstructed/well-known, not independently re-fetched live this pass|**provable** (presence) / advisory (cell-boundary choice)|hyperscale multi-tenant systems|a single shared-capacity pool serving all tenants/customers with no cell/partition isolation despite a declared blast-radius requirement|

---

## 10. Correctness verification (denominator: 2 methodology clusters)

### 10.1 Jepsen (Kyle Kingsbury) -- live-verified [S19]

jepsen.io, "Distributed Systems Safety Research" -- an open-source
testing library plus published in-depth analyses (jepsen.io/analyses) of
real systems' claimed consistency guarantees under partition/failure
injection. Confirmed findings across systems tested (26+ systems over 8+
years per search results, including MongoDB, Cassandra, CockroachDB,
etcd, ZooKeeper, MariaDB Galera, YugabyteDB, NATS JetStream, VoltDB,
ScyllaDB, YDB): consistency violations ranging from stale reads to
committed-data loss, frequently traced to a gap between documented and
actually-implemented guarantees. [S19]

| STRATA-CHECKABILITY | Scale | Note |
|---|---|---|
|**not-checkable** (the findings themselves are empirical, per-system)|any system claiming a consistency/isolation guarantee|the checkable corollary is architecture-check-catalog.md's provability constraint itself: a store's declared consistency level (5.6) must not be asserted "proven" by strata's static model alone -- Jepsen's whole body of work is the empirical proof that documentation-claimed guarantees regularly diverge from implementation, which is exactly why T-0331's provability constraint mandates proof-against-code or reasoned-discharge, never bare declaration|

### 10.2 Formal methods -- TLA+ in practice -- live-verified [S20]

Leslie Lamport, *Specifying Systems: The TLA+ Language and Tools for
Hardware and Software Engineers*, Addison-Wesley, 2002, free at
lamport.azurewebsites.net/tla/book.html. Industrial use page
(lamport.azurewebsites.net/tla/industrial-use.html) and Chris Newcombe et
al., "How Amazon Web Services Uses Formal Methods," Communications of
the ACM 58(4), 2015, document AWS's routine use of TLA+ to specify and
model-check core services (DynamoDB, S3), finding subtle bugs undetected
by testing and enabling aggressive optimizations without sacrificing
correctness. [S20]

| STRATA-CHECKABILITY | Scale | Static proxy |
|---|---|---|
|**advisory** (formal spec is orthogonal to strata's static-analysis approach -- a different, heavier-weight verification tier)|complex distributed protocols (consensus, replication) at any org that can afford it|presence of a TLA+/formal spec for a hand-rolled consensus/replication protocol is a *provable* proxy for "this protocol's design was model-checked," distinct from strata's own code-conformance proofs -- these are complementary tiers (spec-vs-design, not spec-vs-code)|

---

## 11. Foundational papers (denominator: 8 papers) + practitioner engineering blogs (denominator: 7 companies)

### 11.1 Foundational papers -- all live-verified this pass

| Paper | Authors | Venue/year | URL confirmed live | STRATA-CHECKABILITY |
|---|---|---|---|---|
|The Google File System|Ghemawat, Gobioff, Leung|SOSP 2003|research.google.com/archive/gfs-sosp2003.pdf [S21]|advisory (architectural precedent for large-scale distributed storage design, not a per-repo checkable fact)|
|MapReduce: Simplified Data Processing on Large Clusters|Dean, Ghemawat|OSDI 2004 / CACM 51(1) 2008|research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/ [S22]|advisory|
|Bigtable: A Distributed Storage System for Structured Data|Chang, Dean, Ghemawat, Hsieh, Wallach, Burrows, Chandra, Fikes, Gruber|OSDI 2006, Best Paper|research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/ [S23]|advisory|
|Spanner: Google's Globally-Distributed Database|Corbett, Dean, Epstein, et al. (Google)|OSDI 2012, Best Paper|research.google.com/archive/spanner-osdi2012.pdf [S24]|advisory; the TrueTime API concept (bounded clock uncertainty) is a **provable** presence-proxy: a globally-distributed strongly-consistent store declared with no clock-uncertainty/commit-wait mechanism named|
|Dapper, a Large-Scale Distributed Systems Tracing Infrastructure|Sigelman, Barroso, Burrows, Stephenson, Plakal, Beaver, Jaspan, Shanbhag|Google Technical Report, 2010|research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/ [S17]|dup of sec. 7 tracing proxy|
|Large-scale cluster management at Google with Borg|Verma, Pedrosa, Korupolu, Oppenheimer, Tune, Wilkes|EuroSys 2015|research.google/pubs/large-scale-cluster-management-at-google-with-borg/ [S25]|advisory (Borg's lessons -- declarative job spec, admission control, over-commit with isolation -- are the direct ancestor of Kubernetes; not a per-repo checkable fact)|
|The Chubby Lock Service for Loosely-Coupled Distributed Systems|Mike Burrows|OSDI 2006|research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/ [S9]|dup of sec. 2 Leases proxy|
|Dynamo: Amazon's Highly Available Key-value Store|DeCandia, Hastorun, Jampani, Kakulapati, Lakshman, Pilchin, Sivasubramanian, Vosshall, Vogels|SOSP 2007|dl.acm.org/doi/10.1145/1323293.1294281; mirrored at allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf [S10]|dup of sec. 2/3 quorum + consistent-hashing proxies|

### 11.2 Practitioner "scaling war story" engineering blogs (substantive engineering only, no marketing) -- live-verified this pass

Denominator 7 per the task's named list (Netflix, Uber, Discord, Shopify,
Stripe, Slack, Figma). **Resolved this pass**: each post below was
confirmed to exist at a real, current URL via WebSearch this session
(title, host, and publication context all cross-checked; full body text
was not re-transcribed for all seven, but existence/URL/host and lesson
content were confirmed, upgrading these from "reconstructed/well-known"
to "existence-verified, URL-confirmed").

| Company | Representative substantive post(s) | Lesson | STRATA-CHECKABILITY |
|---|---|---|---|
|Netflix|"The Netflix Simian Army," Netflix TechBlog, July 2011, `techblog.netflix.com/2011/07/netflix-simian-army.html` -- URL-confirmed live this pass|Chaos engineering at scale, dup of sec. 5.3|not-checkable (practice), provable (presence of fault-injection harness)|
|Uber|"Designing Schemaless, Uber Engineering's Scalable Datastore Using MySQL" (Parts One and Two) and "Evolving Schemaless into a Distributed SQL Database," Uber Engineering blog, `uber.com/.../schemaless-part-one-mysql-datastore/` -- URL-confirmed live this pass|Sharded, schema-flexible storage under extreme write load; cell-based isolation|advisory|
|Discord|"How Discord Stores Billions of Messages" (Discord Engineering, 2017, `medium.com/discord-engineering/...`) and its 2023 successor "How Discord Stores Trillions of Messages" (`discord.com/blog/how-discord-stores-trillions-of-messages`) -- both URL-confirmed live this pass, documenting the Cassandra -> ScyllaDB migration|Storage-engine migration under real production load; the "boring tech first, migrate when measured" lesson (ties to sec. 12)|advisory|
|Shopify|"How we Prepare Shopify for BFCM" and "Capacity Planning at Scale" (Shopify Engineering blog, `shopify.engineering/bfcm-readiness-2025`, `shopify.engineering/capacity-planning-shopify`) -- URL-confirmed live this pass; 2024 BFCM run cited at 57.3 PB data / 10.5 trillion DB queries / 1.19 trillion edge requests|Capacity planning and load-shedding for extreme predictable-burst traffic (Flash Sale/BFCM), dup of sec. 5.4 load-shedding|provable (presence) / advisory (capacity model)|
|Stripe|"Designing robust and predictable APIs with idempotency," `stripe.com/blog/idempotency` -- URL-confirmed live this pass; Stripe's public API idempotency-key design (client-generated key, 24h server-side response cache keyed by account+key) is a widely-cited reference implementation of sec. 4/8 idempotent-receiver|Idempotency-key API design as a production reference implementation|provable (presence, dup proxy)|
|Slack|"Scaling Slack's Job Queue," Slack Engineering blog, Dec 2017, `slack.engineering/scaling-slacks-job-queue/` -- URL-confirmed live this pass; documents the Redis-coupling incident and decoupling job execution from Redis via Kafka|Queue-based load leveling and backpressure under real incident conditions, dup of architecture-check-catalog.md 5.4 Queue-Based-Load-Leveling|provable (presence)|
|Figma|"How Figma's multiplayer technology works," Figma Blog, `figma.com/blog/how-figmas-multiplayer-technology-works/` -- URL-confirmed live this pass; documents the custom (non-OT) CRDT-inspired sync protocol over WebSockets and offline-edit reconciliation|CRDT-based real-time collaboration (dup of sec. 2 CRDT proxy) and a documented custom sync-protocol design|advisory|

---

## 12. Scale-range lessons: when NOT to distribute (denominator: 4 practitioner sources)

Matches the design-pattern-traps corpus's "El Dorado" theme (premature
abstraction) applied to infrastructure rather than code.

**Live-verified this pass**: all 4 sources below were directly navigated
via Playwright this session (not merely search-confirmed) -- each page
loaded and rendered successfully, upgrading all 4 from
"reconstructed/well-known" to "live-verified."

| Source | Lesson | STRATA-CHECKABILITY | Scale |
|---|---|---|---|
|"MonolithFirst," Martin Fowler, `martinfowler.com/bliki/MonolithFirst.html`, 2015 -- **live-verified this pass** (Playwright navigation, page loaded successfully, title "Monolith First" confirmed)|Almost all successful microservice architectures started as a monolith that grew too large and were then split; starting with microservices makes it hard to get the service boundaries right before the domain is well understood|advisory|small-to-mid, pre-product-market-fit|
|"Choose Boring Technology," Dan McKinley, `mcfunley.com/choose-boring-technology` -- **live-verified this pass** (Playwright navigation, page loaded successfully, title "Dan McKinley :: Choose Boring Technology" confirmed)|An organization has a limited "innovation budget" -- spend it on the 1-2 things that differentiate the product, not on chasing new infra for every component; boring/proven tech (a single Postgres instance, cron) is usually correct until measurement proves otherwise|advisory|all scales, esp. pre-scale|
|"Goodbye Microservices," originally Segment Engineering blog (2018), now hosted at `twilio.com/en-us/blog/developers/best-practices/goodbye-microservices` following Twilio's acquisition of Segment -- **live-verified this pass** (Playwright navigation redirected from the original `segment.com/blog/goodbye-microservices/` URL to the current Twilio-hosted mirror; page loaded successfully, title "Goodbye Microservices \| Twilio" confirmed -- the content moved but was not deleted)|Premature microservice decomposition (one service per data source, ~140 services) created more operational burden than it solved and was consolidated back into a single monolith once the actual scaling bottleneck (not organizational boundary) was identified|advisory|mid-scale, cautionary case study|
|"Deconstructing the Monolith" and "Under Deconstruction: The State of Shopify's Monolith," Shopify Engineering blog, `shopify.engineering/deconstructing-monolith-designing-software-maximizes-developer-productivity` and `shopify.engineering/shopify-monolith` -- **live-verified this pass** (Playwright navigation, page loaded successfully, title "Deconstructing the Monolith - Shopify" confirmed); documents the 2.8M-line-of-Ruby, 500K-commit monolith's move to enforced internal module boundaries via Rails Engines/Packwerk rather than service extraction|A very-large-scale system (Shopify's core commerce platform) can remain a single deployable while enforcing internal module boundaries -- distribution and modularity are orthogonal; module-boundary enforcement (the kind arch's dependency-cycle/layering checks already provide) buys most of microservices' organizational benefit without the operational cost|advisory; the underlying module-boundary-enforcement mechanism is **provable** and already implemented as arch's DIP/layering-contract check (architecture-check-catalog.md sec. "DIP: LAYERING CONTRACT")|

Cost-of-premature-distribution checklist (advisory, synthesized from the
above, not itself a citation): a network hop introduces the sec. 1
fallacies, sec. 5 timeout/retry obligations, sec. 6 tail-latency risk,
and sec. 7 cross-process observability cost that a function call does
not; each service boundary drawn should be justified by an
organizational or genuine independent-scaling need, not drawn by default.

---

## 13. Cross-layer boundary best practices (denominator: 5 seams)

The contract discipline at each seam from hardware up to service. Each
seam gets a best-practice, its primary failure mode, cited, with a
strata-checkability tag.

### 13.1 Hardware <-> firmware/software: the ISA/ABI contract

The Instruction Set Architecture (ISA) is the hardware/software contract:
software addresses hardware only through the vocabulary the ISA defines
(registers, instructions, memory model), which is what lets compiled code
and OS kernels target a processor family without knowing its
microarchitectural implementation. Canonical text: John L. Hennessy,
David A. Patterson, *Computer Architecture: A Quantitative Approach*
(6th/7th ed., Morgan Kaufmann) -- Hennessy and Patterson jointly won the
2017 ACM A.M. Turing Award for this body of work; the ISA-as-contract
framing is confirmed via general reference material this pass (the exact
ABI/calling-convention chapter content was not independently re-fetched
from the book's text). [S26] The Application Binary Interface (ABI)
layer -- calling conventions, struct layout, syscall numbers -- is the
software-to-software analog of the same seam and is what breaks when a
compiler or syscall table changes without a version bump.

| Best practice | Failure mode | STRATA-CHECKABILITY | Scale |
|---|---|---|---|
|A declared ABI/ISA target is stable across a compatibility window (a compiled artifact keeps running unmodified)|Silent ABI break: a struct layout, syscall number, or calling convention changes without a major-version bump, corrupting any binary still linked against the old layout|**provable** (declaration presence)|any compiled artifact / cross-language FFI boundary; a symbol/struct exported across an ABI boundary with no declared stability tier (stable/unstable/experimental) and no version-bump-on-change enforcement|

### 13.2 Firmware <-> OS: measured/secure boot and firmware-update safety

UEFI (Unified Extensible Firmware Interface) is the specification
connecting firmware to the OS, replacing legacy BIOS. Secure Boot (added
in UEFI 2.3.1) enforces that firmware only transfers control to
boot-chain binaries matching entries in the firmware's signature
databases (PK/KEK/db, blocked by dbx); Measured Boot instead hashes each
stage (firmware, bootloader, drivers) into a TPM and allows comparison
against a known-good state rather than gating execution outright --
confirmed via UEFI Forum / NSA UEFI Secure Boot technical-report search
results this pass. [S27] The governing discipline -- "firmware is
software and must be treated as such" -- means firmware needs the same
update/rollback/signing discipline as any other deployed artifact: an
unsigned or unversioned firmware update path is as dangerous as an
unsigned software deploy, and typically has a much higher blast radius
(a bad firmware flash can brick hardware, where a bad software deploy can
be rolled back).

| Best practice | Failure mode | STRATA-CHECKABILITY | Scale |
|---|---|---|---|
|Every boot-chain stage is signed (secure boot) or measured into an attestable log (measured boot); firmware updates are versioned, signed, and have a declared rollback path|An unsigned/unmeasured boot stage; a firmware-update mechanism with no signature check or no rollback-on-failure path|**provable** (presence)|firmware/embedded/hardware-adjacent systems; a firmware-update flow declared in the model with no signing/rollback annotation|

### 13.3 Kernel <-> userspace: the syscall/HAL boundary

Linux's governing rule, stated repeatedly by Linus Torvalds on the kernel
mailing list: "we do not break userspace" -- a kernel change that breaks
a previously-working userspace program is, by definition, a kernel bug,
regardless of whether the change was otherwise a correctness fix;
confirmed live via LWN.net's "Never break userspace" article and the
kernel's own `Documentation/ABI` directory (github.com/torvalds/linux),
which documents the relative stability tier (stable/testing/obsolete) of
every kernel-userspace interface. [S28] This is the same discipline as
13.1's ABI contract, specialized to the syscall/procfs/sysfs boundary:
the stable-vs-unstable split is explicit and load-bearing -- kernel
*internal* APIs (driver-facing) are explicitly NOT covered by this
guarantee and may change freely, which is itself a documented, checkable
distinction.

| Best practice | Failure mode | STRATA-CHECKABILITY | Scale |
|---|---|---|---|
|Every kernel<->userspace interface (syscall, procfs/sysfs entry, ioctl) is classified into a stability tier, and a change to a "stable" interface preserves existing userspace behavior|A syscall/sysfs field changes meaning or is removed without a stability-tier check, breaking programs built against the old contract|**provable** (presence, tier-declaration proxy)|kernel/driver/OS-adjacent systems; a public kernel-userspace interface with no declared stability tier in `Documentation/ABI`-equivalent tracking|

### 13.4 OS <-> service: the process/container contract

Two complementary primary sources: (a) 12-Factor App's process model
(already live-verified in architecture-check-catalog.md [C12] and sec. 9
above) -- a service is a stateless process reading config from the
environment; (b) the Linux kernel primitives that make containers
possible -- namespaces (isolating a process's view of PIDs, mounts,
network) and cgroups (bounding a process group's resource consumption) --
are the OS-level mechanism the 12-factor process contract is built on.
Canonical kernel documentation: `Documentation/admin-guide/cgroup-v2.rst`
and the `namespaces(7)` man page (Linux man-pages project) -- reconstructed
from established knowledge, not independently re-fetched live this pass.

| Best practice | Failure mode | STRATA-CHECKABILITY | Scale |
|---|---|---|---|
|Every deployed process declares its resource bounds (cgroup limits: CPU/memory/IO) and its isolation boundary (namespace scope)|A process/container declared in the model with no resource-limit annotation -- an unbounded process can starve co-located neighbors (the "noisy neighbor" failure)|**provable** (presence)|containerized/multi-tenant deployment, all scales; dup + specialization of architecture-check-catalog.md 5.3 "Backing Services"/"Processes" proxies|

### 13.5 Service <-> service: API contracts and Postel's Law

Jon Postel, RFC 761 (1980), later codified in RFC 1122: "be conservative
in what you send, be liberal in what you accept" -- the robustness
principle. Confirmed live this pass, along with its now-substantial
critique: Martin Thomson and David Schinazi,
"The Harmful Consequences of the Robustness Principle,"
IETF Internet-Draft (datatracker.ietf.org/doc/html/draft-thomson-postel-was-wrong-03),
and Eric Allman, "The Robustness Principle Reconsidered," ACM Queue /
Communications of the ACM, 2011 -- both confirmed live via WebSearch.
[S29] The critique's core argument: liberal acceptance lets a
non-conformant sender's quirks become a de facto standard other
implementations must replicate ("bug-for-bug compatibility") to stay
interoperable, and silently accepting-or-discarding malformed input makes
failures hard to debug and opens a security surface (parser
differentials). Net practitioner position, synthesized from both sides:
be strict on the wire (validate against a declared schema), and reserve
liberality for additive, explicitly-versioned extension points (e.g.
unknown-field tolerance in a schema built for forward-compatible
evolution), not for tolerating malformed core fields.

| Best practice | Failure mode | STRATA-CHECKABILITY | Scale |
|---|---|---|---|
|Every service-to-service API declares an explicit schema/contract with a versioning policy (backward/forward compatibility rules stated, not implied)|An API boundary with no declared schema version, or with silent lenient-parsing of malformed core fields that becomes an undocumented de facto contract|**provable** (declaration presence)|any service boundary, all scales; dup of architecture-check-catalog.md 5.6 Schema-Evolution/Versioning proxy, specialized to the API-contract seam and directly informed by the Postel's-Law critique above|

---

## 14. Lessons from verified primary contributors to famous systems (denominator: 8 people)

Hard authenticity gate applied per instruction: each person below is
included only where this pass could cross-check them as a verifiable
creator or principal engineer of the named system (not a commentator
about it). Sourcing is each person's own talk, paper, or documented
mailing-list/interview record where possible.

| Person | System | Verified-contributor evidence | Distilled lesson | Citation | STRATA-CHECKABILITY |
|---|---|---|---|---|---|
|Linus Torvalds|Linux kernel, git|Creator and lead maintainer of both projects; the "never break userspace" rule is his own repeatedly-stated policy, confirmed via his own kernel-mailing-list posts (lkml.org, e.g. the December 2012 "WE DO NOT BREAK USERSPACE!" thread) and the kernel's own `Documentation/ABI` he governs. [S28]|A stable public interface is a promise that outlives the implementation detail behind it; a "correct" internal change that breaks a real external consumer is still a bug -- the interface's stability is the actual contract, not the implementation's internal correctness.|LKML thread, Dec 2012, https://lkml.org/lkml/2012/12/23/75; LWN.net, "Never break userspace," https://lwn.net/Articles/962527/|**provable**: dup of sec. 13.3 ABI-stability-tier proxy -- this is the primary-source origin of that check|
|Barbara Liskov|CLU (data abstraction), Liskov Substitution Principle, Argus (distributed/fault-tolerant computing)|2008 ACM Turing Award laureate specifically for "contributions to practical and theoretical foundations of programming language and system design... data abstraction, fault tolerance, and distributed computing"; led CLU's design and implementation at MIT, 1973-78, confirmed via the ACM Turing Award citation and her own Turing Lecture. [S30]|Data abstraction -- separating a type's interface from its implementation, with the interface as the sole point of contact -- is the mechanism that makes large systems modifiable without whole-system re-verification; a subtype must be substitutable for its supertype without breaking caller-side correctness (the Liskov Substitution Principle).|Barbara Liskov, ACM A.M. Turing Award Lecture, "The Power of Abstraction," OOPSLA 2009 keynote, video at https://www.youtube.com/watch?v=qAKrMdUycb8; bibliography at https://amturing.acm.org/award_winners/liskov_1108679.cfm|**provable**: dup of architecture-check-catalog.md's ISP/LSP-family static proxies (interface-implementation separation, subtype-contract violation)|
|Butler Lampson|Alto, Dorado, Bravo, Star -- Xerox PARC systems; broader systems-design methodology|Personal-computing systems pioneer at Xerox PARC; author of the paper in his own name, drawing directly on his own design experience with the named systems, published at SOSP '83 and republished in IEEE Software. [S31]|A short, explicit list of design "hints" (keep it simple, plan to throw one away, use a good idea again, safety-first, timing assumptions should be explicit, ...) drawn from direct implementation experience beats abstract principles; a system's external interface is far less precisely defined than an algorithm's, is more subject to change, and needs many more internal interfaces than a single algorithm -- so interface discipline compounds at every internal seam, not just the external one.|Butler Lampson, "Hints for Computer System Design," ACM SIGOPS Operating Systems Review 17(5), Oct 1983 (also IEEE Software 1(1), 1984); confirmed live at https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/acrobat-17.pdf|advisory (a design-heuristics list, mostly judgment-tier) / **provable** slice: "timing assumptions should be explicit" maps directly to the sec. 5.4/13 timeout-declaration proxy|
|Leslie Lamport|Distributed-systems theory (logical clocks, Paxos), TLA+|Already the anchor citation of secs. 1.5, 2, 10.2 above -- author of the Lamport-clocks paper (CACM 1978), Paxos papers (1998/2001), and the TLA+ book/tool (2002), all in his own name; 2013 ACM Turing Award laureate for "fundamental contributions to the theory and practice of distributed and concurrent systems."|A distributed system's correctness should be *specified* precisely enough to be model-checked before it is implemented; "if you're going to write a program without first stating what it's supposed to do, you might as well not bother" is the practical form of this lesson borne out by AWS's own reported TLA+ bug-finds (sec. 10.2). Not re-cited redundantly here beyond the cross-reference.|dup of [S6][S7][S20] above|**advisory** (formal-spec presence, dup of sec. 10.2 tag)|
|Werner Vogels|Amazon.com / AWS -- Dynamo (co-author), Amazon's distributed-systems architecture as CTO|Amazon.com CTO since 2005; co-author of the Dynamo paper itself (DeCandia et al., SOSP 2007, sec. 3/11 above) -- confirmed as a named author on the primary paper, not merely a commentator. [S10]|"Everything fails all the time" -- design for failure as the default assumption, not an edge case, and prefer eventual consistency + application-level conflict resolution over unavailability when a partition makes strong consistency and availability mutually exclusive (the practical instantiation of CAP, sec. 1.2, in a real production system he co-designed).|Werner Vogels, "Amazon.com CTO Werner Vogels talks about scaling," multiple All Things Distributed blog posts (allthingsdistributed.com), and his Dynamo co-authorship [S10] -- the "design for failure" framing is reconstructed/well-known from his public talks/posts, not independently re-fetched live this pass beyond the Dynamo paper itself|**provable** slice: dup of sec. 1.2/3.3 consistency-declaration and conflict-resolution-presence proxies|
|James Hamilton|MySQL/SQL Server (Microsoft), then Amazon/AWS distributed-systems infrastructure|Authored "On Designing and Deploying Internet-Scale Services" in his own name, drawing on his own operational experience (at the time, Windows Live Services Platform, later Amazon/AWS Distinguished Engineer); paper confirmed live. [S32]|Design and operate services around automated, "admin-light" operability from day one -- the system-to-administrator ratio is the real cost metric of a service at scale, not raw feature count; recovery-oriented design (assume things fail, make fast automated recovery the primary correctness mechanism) beats trying to prevent all failure.|James Hamilton, "On Designing and Deploying Internet-Scale Services," LISA '07, https://s3.amazonaws.com/systemsandpapers/papers/hamilton.pdf|**provable** slice: dup of sec. 5 health-check/graceful-degradation and sec. 9 autoscaling/operability proxies|
|Bryan Cantrill|DTrace (co-creator), illumos, Oxide Computer (co-founder/CTO)|Co-created DTrace with Mike Shapiro and Adam Leventhal at Sun Microsystems (shipped in Solaris 10, 2004); later CTO/co-founder of Oxide Computer building vertically-integrated rack-scale hardware+firmware+OS -- confirmed via Wikipedia's biographical entry, cross-checked against his own bio page (bcantrill.dtrace.org/about/) and Oxide's own public engineering material. [S33]|Production systems must be observable *in production*, not only in a lab/staging environment -- DTrace's design goal was zero-disabled-probe-effect instrumentation safe to run on a live system, because a debugger/profiler you can't run in prod doesn't actually help you when prod is broken; at Oxide, this extends the observability-by-default discipline down into firmware, which Cantrill argues must be engineered, versioned, and treated with the same rigor as any other software layer, not as an opaque vendor blob (backs sec. 13.2's firmware-as-software framing).|Bryan Cantrill's own talks are the primary record (e.g. his USENIX/Papers We Love talks on DTrace's design and Oxide's firmware approach); this pass confirmed his contributor role and the Oxide firmware-in-Rust approach via Wikipedia and grokipedia.com biographical summaries rather than fetching a specific talk transcript -- flagged as contributor-role-verified but lesson-content reconstructed/well-known, not independently re-fetched from a specific talk this pass|**provable** slice: dup of sec. 7 instrumentation-presence proxy, specialized to "safe-in-production" (near-zero overhead when disabled) and extended to sec. 13.2 firmware-as-software|
|Rob Pike|Unix (Bell Labs team member), Plan 9 (co-creator), UTF-8 (co-creator with Ken Thompson), Go (co-creator)|Bell Labs Computing Sciences Research Center member; co-led Plan 9's design; co-created UTF-8 with Ken Thompson (1992); co-created Go at Google -- confirmed via Wikipedia's biographical entry and Pike's own conference talks (e.g. "Concurrency is Not Parallelism," Heroku Waza 2012). [S34]|Concurrency (structuring a program as independently-executing components) and parallelism (running computations simultaneously for speed) are different concerns that are frequently conflated; a well-structured concurrent decomposition (Go's goroutines+channels, in Pike's own account) can make a program simpler even on a single core, and is a design tool independent of whether it happens to also buy you parallel speedup.|Rob Pike, "Concurrency is Not Parallelism," Heroku Waza 2012 (video widely referenced, talk itself not independently re-fetched this pass) -- title/venue/content confirmed via secondary biographical sources this pass|advisory (a design-clarity lesson, not itself a bare-fact static proxy)|
|Ken Thompson|Unix (co-creator, Bell Labs), B language (predecessor to C), UTF-8 (co-creator with Pike)|1983 ACM Turing Award laureate jointly with Dennis Ritchie "for their development of generic operating systems theory and specifically for the implementation of the UNIX operating system"; his own 1984 Turing Award lecture is a primary, first-person, on-point source -- **resolved this pass** via WebSearch confirming the paper's existence and multiple mirrors (ACM Digital Library DOI, Internet Archive, and university course-reading copies), title/venue/year cross-checked against ACM's own record.|"Reflections on Trusting Trust": a compiler can be built to recognize a specific pattern (e.g. the `login` source) and insert a backdoor, then further modified to recognize and re-insert itself when recompiling the *compiler's own* source -- so a trusted-toolchain compromise can be undetectable from source-code inspection alone, no matter how carefully the source is audited, because the audit trusts the compiler that built it. Direct primary-source origin of any supply-chain/build-provenance obligation this repo's own checks encode.|Ken Thompson, "Reflections on Trusting Trust," Communications of the ACM 27(8), Aug 1984, pp. 761-763 (1983 Turing Award Lecture), DOI `10.1145/358198.358210`; confirmed live-accessible at `dl.acm.org/doi/10.1145/358198.358210` and mirrored full-text at `cl.cam.ac.uk/teaching/2324/R209/Reflections-Trusting-Trust.pdf` (University of Cambridge teaching mirror) -- existence and metadata confirmed via WebSearch this pass, not independently re-rendered page-by-page|**provable** (presence): dup of a build-provenance/reproducible-build proxy -- a CI pipeline with no pinned/reproducible-build attestation on its compiler/toolchain stage is the checkable analog of this lesson|
|Dennis Ritchie|Unix (co-creator, Bell Labs), C language (creator)|1983 ACM Turing Award laureate jointly with Ken Thompson, for the same UNIX citation; author in his own name of the retrospective history paper on Unix's evolution -- confirmed via ACM's own Turing Award bibliography and Bell Labs' own archived hosting of the paper.|"The Evolution of the Unix Time-sharing System": a system's design should stay small and orthogonal (a few general mechanisms -- files, pipes, processes -- composed by the user, rather than many special-cased features) -- the same "do one thing well" philosophy Unix pipes encode, in Ritchie's own retrospective account of why the early design decisions held up.|Dennis M. Ritchie, "The Evolution of the Unix Time-sharing System," AT&T Bell Laboratories Technical Journal 63(8), Oct 1984 (an expanded version of a 1979 conference paper); confirmed live-hosted at Bell Labs' own archive, `www.bell-labs.com/usr/dmr/www/hist.html` -- existence and hosting confirmed via WebSearch this pass|advisory (a design-philosophy lesson); dup of the sec. 13 seam-minimization framing where applicable|
|Michael Stonebraker|Ingres, Postgres/PostgreSQL (co-creator), and a line of later database systems (Aurora/Borealis, C-Store, H-Store)|2014 ACM A.M. Turing Award laureate "for fundamental contributions to the concepts and practices underlying modern database systems"; his own Turing Award lecture, delivered at VLDB 2015 -- **resolved this pass** via Playwright navigation directly to VLDB's own hosted lecture page (`vldb.org/2015/turing-award-talk.html`), which loaded live and confirmed the talk's existence, venue, and year as VLDB's own record.|"One size does not fit all": the single general-purpose relational engine that dominated from the 1980s onward is the wrong architecture for many modern workloads (OLTP, data warehousing, streaming, scientific/array data each want a specialized engine) -- a direct database-architecture instantiation of "match the storage/processing engine to the actual workload shape," which generalizes to this repo's own storage-engine-choice advisory (sec. 4).|Michael Stonebraker, ACM A.M. Turing Award Lecture, delivered at VLDB 2015, San Francisco; VLDB's own hosted page confirming the talk, `https://www.vldb.org/2015/turing-award-talk.html` -- live-verified via Playwright this pass; full lecture bibliography also at `amturing.acm.org/vp/stonebraker_1172121.cfm`|advisory (an architecture-fit heuristic, not itself a bare-fact static proxy)|
|David Cutler|VMS (lead architect, DEC), Windows NT (chief architect, Microsoft)|Led VMS's development at DEC on the VAX architecture team; joined Microsoft in 1988 to lead the portable-OS effort that became Windows NT -- confirmed via the Computer History Museum's own oral-history program, which recorded a dedicated, named interview with Cutler himself (interviewed by Grant Saviers, Feb 25 2016) as part of its verified subject roster -- **resolved this pass** via WebSearch confirming the interview's existence, interviewer, date, and CHM's own catalog/archive hosting.|A small, disciplined core team with a strict internal design-review and code-quality bar (Cutler's well-documented management style across both VMS and NT) produces a more reliable kernel than a large, loosely-coordinated one -- direct lived experience shipping two production OS kernels used at planetary scale, in his own account of his management/engineering philosophy.|Computer History Museum, "Oral History of David Cutler," interviewed by Grant Saviers, Feb 25 2016, catalog #102717163, full transcript PDF at `archive.computerhistory.org/resources/access/text/2018/10/102717163-05-01-acc.pdf`; video parts on CHM's own YouTube channel -- existence, interviewer, and hosting confirmed via WebSearch this pass, not independently re-transcribed|advisory (a team/process-discipline lesson, not itself a bare-fact static proxy)|
|Andrew S. Tanenbaum|MINIX (creator), author of the Tanenbaum-Torvalds microkernel-vs-monolithic-kernel Usenet debate (1992)|Sole creator of MINIX (1987) and its 30-years-later retrospective is published in his own name -- **resolved this pass** via WebSearch confirming the paper is hosted on Tanenbaum's own institutional page at Vrije Universiteit Amsterdam.|A small, well-isolated microkernel (each driver/server as an unprivileged, independently-restartable process) trades some raw performance for fault isolation and live-patchability -- MINIX 3's own design goal was a kernel small enough to be exhaustively verified, and componentized enough that a crashed driver doesn't crash the whole system; a direct instantiation of this repo's own bulkhead/blast-radius-isolation checks (dup of architecture-check-catalog.md 5.2 Bulkhead) applied at the OS-kernel-architecture level.|Andrew S. Tanenbaum, "Lessons Learned from 30 Years of MINIX," Communications of the ACM 59(3), March 2016, pp. 70-78, DOI `10.1145/2795228`; author's own institutional mirror confirmed live-hosted at `https://www.cs.vu.nl/~ast/Publications/Papers/cacm-2016.pdf` -- existence and hosting confirmed via WebSearch this pass|**provable** slice: dup of architecture-check-catalog.md 5.2 Bulkhead presence-proxy, specialized to process/component isolation at the kernel level|
|Margaret Hamilton|Apollo Guidance Computer software (director of the Software Engineering Division, MIT Instrumentation Laboratory)|Led the team that wrote the on-board flight software for the Apollo program, including the priority-scheduling/error-handling logic that let the AGC recover from the 1202/1201 program alarms during the Apollo 11 landing rather than aborting; credited with coining the term "software engineering." Held out in the prior pass for lacking a single citable primary talk/paper with a confirmable URL -- **resolved this pass**: her own ICSE 2018 keynote is confirmed as a real, dated, named conference session via ICSE 2018's own official program page (`conf.researchr.org/track/icse-2018/icse-2018-Keynotes` and her own speaker profile `conf.researchr.org/profile/icse-2018/margarethamilton`), delivered May 31 2018 at the 40th International Conference on Software Engineering, Gothenburg -- a primary, first-person, conference-hosted record, not a secondary summary.|Design the system to handle "the asynchronous unknown" -- prioritize and gracefully degrade under unexpected/overload conditions rather than crash or silently fail; the AGC's priority-display/restart mechanism (letting lower-priority Apollo 11 landing-radar-data tasks be dropped so the landing-critical tasks kept running through the 1202 alarms) is the direct historical ancestor of this repo's own load-shedding/graceful-degradation checks (dup of architecture-check-catalog.md 5.2 Shed Load/Governor).|Margaret Hamilton, ICSE 2018 keynote ("The Language as a Software Engineer"), 40th International Conference on Software Engineering, Gothenburg, Sweden, May 31 2018; official conference program record at `https://conf.researchr.org/track/icse-2018/icse-2018-Keynotes` and speaker profile at `https://conf.researchr.org/profile/icse-2018/margarethamilton` -- session existence, date, and venue confirmed via WebSearch this pass against ICSE's own program site, not independently re-watched/transcribed|**provable** slice: dup of architecture-check-catalog.md 5.2 Shed-Load/Governor presence-proxy, specialized to priority-preemption under overload|

Note on denominator (corrected this pass): the coordinator's original
candidate list actually named **14** distinct people across the two
research passes (Torvalds, Liskov, Lampson, Lamport, Vogels, James
Hamilton, Cantrill, Pike, Thompson, Ritchie, Stonebraker, Cutler,
Tanenbaum, Margaret Hamilton) -- the prior pass's own "11 candidates"
figure undercounted by 3 and is corrected here rather than carried
forward silently. The prior pass authenticated and included 8 with a
direct, checkable contributor link; **this pass resolves the remaining
6** (Thompson, Ritchie, Stonebraker, Cutler, Tanenbaum, and Margaret
Hamilton) with their own primary talk/paper/conference-session citations
-- each one's own verified-contributor evidence and citation is now a
full row in the table above. Zero people remain blocked in this
category: **14 of 14 candidates now included**, all with a
contributor-role citation, and 6 of the 14 (Thompson, Ritchie,
Stonebraker, Cutler, Tanenbaum, Margaret Hamilton) have their lesson
content newly traced to a specific citable primary source this pass
rather than carried as reconstructed/well-known.

---

## Coverage proof (denominator table, Phase 2)

| Category | Denominator | Entries covered | Live-verified | Reconstructed/well-known | Not independently checked this pass |
|---|---|---|---|---|---|
|1. Distributed-systems fundamentals|6|6|4 (1.1 Fallacies, 1.2 CAP/PACELC, 1.3 FLP, 1.4 end-to-end, 1.5 Lamport clocks = 5 actually)|1 (1.6 consistency models)|0|
|2. Consensus & coordination|9|9|3 (Paxos, Raft, Chubby/Leases)|6 (Multi-Paxos dup, Zab, VR, 2PC, 3PC, Quorums, CRDTs)|0|
|3. Replication & partitioning|7|7|2 (Dynamo anchor; DDIA chapter-structure live-verified this pass)|5 (DDIA content itself not re-fetched -- structure only)|0|
|4. Data-intensive systems|8|8|1 (DDIA chapter-structure live-verified this pass, confirming the ch. 3/7/9/10-11 citations used throughout this section)|7 (DDIA per-topic content itself not re-fetched)|0|
|5. Reliability & resilience|4 clusters|4|3 (SRE book, AWS Builders' Library, Release It! -- resolved this pass via Playwright, was 403-blocked)|1 (Chaos engineering)|0|
|6. Performance & capacity|5|5|4 (Little's Law, USL, Tail at Scale, USE Method)|1 (queueing theory basics)|0|
|7. Observability|4|4|2 (Dapper, SLO-alerting via SRE book)|2 (three pillars, high-cardinality/Honeycomb)|0|
|8. Messaging/eventing|6|6|1 (The Log, Kreps)|5 (delivery-semantics taxonomy is classical, not independently re-fetched)|0|
|9. Deployment/infra|6|6|1 (12-Factor, by pointer to prior verified doc)|5 (immutable infra, blue-green/canary, autoscaling, multi-region DR, cell-based)|0|
|10. Correctness verification|2|2|2 (Jepsen, TLA+/AWS)|0|0|
|11. Foundational papers + blogs|8 papers + 7 companies = 15|15|15 (all 8 papers; all 7 company blog posts URL-confirmed live this pass, upgraded from reconstructed)|0|0|
|12. Scale-range / don't over-engineer|4|4|4 (all 4 sources live-verified this pass via Playwright)|0|0|
|13. Cross-layer boundary practices|5 seams|5|5 (all 5 seams cite at least one live-confirmed source: S26 partial/general-reference, S27, S28, S29, plus dup of S10/C12)|5 (each seam also carries reconstructed detail beyond its live-confirmed anchor citation)|0|
|14. Verified primary-contributor lessons|14 (corrected this pass from the prior pass's undercounted "11")|14 included, 0 blocked (all 6 previously-blocked/held-out people resolved this pass: Thompson, Ritchie, Stonebraker, Cutler, Tanenbaum, Margaret Hamilton)|10 fully live-verified contributor role + own-source citation (Torvalds, Liskov, Lampson, James Hamilton, Thompson, Ritchie, Stonebraker, Cutler, Tanenbaum, Margaret Hamilton)|4 contributor-role-verified, lesson-content reconstructed (Vogels beyond Dynamo co-authorship, Cantrill beyond bio, Pike beyond bio, Lamport is a dup-reference not re-verified again)|0|

**Total entries enumerated and closed: 14 categories, 103 denominator
items counted (84 from categories 1-12, 5 seams in category 13, 14
candidates in category 14, corrected up from the prior pass's
undercounted 97/11), 103 covered, 0 explicitly blocked as of this pass
(category 14's 6 previously-blocked/held-out people -- Thompson, Ritchie,
Stonebraker, Cutler, Tanenbaum, Margaret Hamilton -- are now all
resolved with their own primary-source citations).** 47 items
live-verified against a primary source with a confirmed canonical URL
this pass (25 from categories 1-12, +3 for DDIA structure/Release
It!/12-Factor cross-refs now resolved, +7 company blog posts in category
11, +4 scale-range sources in category 12, S26-S29 anchoring category 13,
plus 10 of category 14's rows -- the prior pass's 4 already-verified
contributors [Torvalds, Liskov, Lampson, James Hamilton] plus the 6
newly-resolved this pass [Thompson, Ritchie, Stonebraker, Cutler,
Tanenbaum, Margaret Hamilton]); the remainder are reconstructed/well-known
canon carried at the same confidence level as
`architecture-check-catalog.md`'s own general-knowledge sections (that
document's own honesty convention followed identically here -- concepts
and static proxies are sound; exact sub-list names or full lesson-content
in the not-independently-verified rows should get a follow-up
verification pass before being treated as page-exact, same caveat as
that document's own closing note).

**STRATA-CHECKABILITY tally across all entries** (counting each row's
primary tag, "provable (presence)" counted as provable):
- provable: 53 entries (including all dup-proxy cross-references, which
  is intentional -- most systems obligations recur across categories
  because the same underlying flow/store/edge carries multiple
  properties, e.g. a queue edge carries both delivery-semantics AND
  idempotency AND ordering obligations; category 13 adds 5 provable
  boundary-declaration proxies, category 14 adds 7 provable dup-proxy
  lesson rows: the prior pass's Torvalds/James-Hamilton/Vogels/Cantrill
  plus this pass's Thompson, Tanenbaum, and Margaret Hamilton)
- advisory: 39 entries (category 14 adds 6 this pass: Lampson,
  Lamport-dup, Pike, Ritchie, Stonebraker, Cutler)
- not-checkable: 5 entries (FLP, Jepsen findings themselves, chaos
  engineering practice itself, TLA+ as a complementary-not-substitute
  tier, exactly-once-as-a-true-guarantee)

---

## Upgrades over architecture-check-catalog.md

Citations that document self-flagged as "general knowledge, not
independently re-verified via search" (its sec. 5.1, 5.2 partial, 5.5,
5.6, 5.7, 5.8) and this corpus now backs with a live-confirmed canonical
primary source and URL:

- **8 Fallacies of Distributed Computing** (5.1): upgraded from "Azure
  page confirms a variant" to full historical provenance (Deutsch 1994 +
  Joy/Lyon predecessor + Gosling's 8th item, 1997) -- sec. 1.1 above.
- **CAP theorem** (underlies 5.6 Consistency/data): upgraded to Brewer's
  PODC 2000 talk + Gilbert & Lynch's 2002 SIGACT News proof + Abadi's
  2012 PACELC IEEE Computer paper -- sec. 1.2 above.
- **SLI/SLO/SLA/Error Budget** (5.5 Observability): upgraded from
  "general knowledge" to the Google SRE book (Beyer et al. 2016,
  sre.google/sre-book/ ch. 4) -- sec. 5.2 above.
- **Timeout/Retry/Jitter, Idempotent Receiver** (5.2 Nygard-adjacent, 5.6
  Idempotency): upgraded from Nygard-secondary-source-only to the AWS
  Builders' Library primary source (Marc Brooker) -- sec. 5.4 above.
- **Distributed tracing / correlation IDs** (5.5 Observability): upgraded
  from "general knowledge" to the Dapper technical report -- sec. 7
  above.
- **Consistent hashing, quorum, vector-clock conflict resolution** (5.6,
  underlying the Sharding entries in 5.8): upgraded to the Dynamo SOSP
  2007 paper directly -- sec. 3 above.
- **Foundational infra precedent** for several strata-modeled Azure
  patterns (Leader Election -> Chubby/Paxos, Materialized View ->
  Bigtable/Spanner precedent): now backed by GFS/Bigtable/Spanner/Chubby/
  Borg/Dapper primary sources -- sec. 11.1 above.

Citations NOT upgraded this pass (carried at the same
reconstructed/well-known confidence as architecture-check-catalog.md,
flagged per-entry above rather than silently presented as verified):
Release It! full pattern list (O'Reilly TOC still 403s to WebFetch),
DDIA's exact chapter-level sub-claims (book has no accessible full-text
primary source to fetch), the 7 named practitioner engineering-blog
posts (would need per-post WebFetch beyond this pass's scope), and the
4 scale-range/"don't over-engineer" posts.

---

## Sources

- [S1] Wikipedia, "Fallacies of distributed computing"
  (https://en.wikipedia.org/wiki/Fallacies_of_distributed_computing) --
  cross-checked against Microsoft Learn, "Cloud Design Patterns - Azure
  Architecture Center" (https://learn.microsoft.com/en-us/azure/architecture/patterns/),
  both surfaced via WebSearch this pass; historical provenance
  (Deutsch/Joy/Lyon/Gosling) confirmed consistently across multiple
  independent secondary sources returned in search results.
- [S2] Seth Gilbert, Nancy Lynch, "Brewer's Conjecture and the
  Feasibility of Consistent, Available, Partition-Tolerant Web
  Services," ACM SIGACT News 33(2), 2002 -- citation confirmed via
  WebSearch aggregate result.
- [S3] Daniel Abadi, "Consistency Tradeoffs in Modern Distributed
  Database System Design: CAP is Only Part of the Story," IEEE Computer,
  2012 -- citation and PACELC formulation confirmed via WebSearch.
- [S4] Michael J. Fischer, Nancy A. Lynch, Michael S. Paterson,
  "Impossibility of Distributed Consensus with One Faulty Process,"
  Journal of the ACM 32(2):374-382, 1985 -- citation confirmed via
  WebSearch (multiple academic aggregator results).
- [S5] J.H. Saltzer, D.P. Reed, D.D. Clark, "End-to-End Arguments in
  System Design," ACM Transactions on Computer Systems 2(4):277-288,
  1984 -- full text confirmed live at
  https://web.mit.edu/saltzer/www/publications/endtoend/endtoend.pdf via
  WebSearch result.
- [S6] Leslie Lamport, "Time, Clocks, and the Ordering of Events in a
  Distributed System," Communications of the ACM 21(7), July 1978 --
  confirmed via WebSearch, including
  https://www.cs.cmu.edu/afs/cs/academic/class/15712-f08/www/lectures/Lamport78lecture.pdf.
- [S7] Leslie Lamport, "Paxos Made Simple," ACM SIGACT News 32(4),
  Dec 2001 -- PDF confirmed live at
  https://lamport.azurewebsites.net/pubs/paxos-simple.pdf via WebSearch.
- [S8] Diego Ongaro, John Ousterhout, "In Search of an Understandable
  Consensus Algorithm," USENIX ATC 2014 -- confirmed live at
  https://raft.github.io/raft.pdf and https://raft.github.io/ via
  WebSearch.
- [S9] Mike Burrows, "The Chubby Lock Service for Loosely-Coupled
  Distributed Systems," OSDI 2006 -- confirmed via
  https://research.google/pubs/the-chubby-lock-service-for-loosely-coupled-distributed-systems/
  via WebSearch.
- [S10] Giuseppe DeCandia et al., "Dynamo: Amazon's Highly Available
  Key-value Store," SOSP 2007 -- confirmed via
  https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf
  and https://dl.acm.org/doi/10.1145/1323293.1294281 via WebSearch.
- [S11] Betsy Beyer, Chris Jones, Jennifer Petoff, Niall Richard Murphy
  (eds.), *Site Reliability Engineering*, O'Reilly, 2016, free at
  https://sre.google/sre-book/service-level-objectives/ and
  https://sre.google/workbook/ -- confirmed live via WebSearch.
- [S12] Marc Brooker, "Timeouts, retries, and backoff with jitter," AWS
  Builders' Library -- confirmed live at
  https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
  via WebSearch.
- [S13] John D. C. Little, "A Proof for the Queuing Formula: L = lambda
  W," Operations Research 9(3):383-387, 1961 -- citation confirmed via
  WebSearch.
- [S14] Neil J. Gunther, "A General Theory of Computational Scalability
  Based on Rational Functions," arXiv:0808.1431, 2008 -- confirmed live
  at https://arxiv.org/abs/0808.1431 via WebSearch; original 1993 CMG
  presentation date confirmed via perfdynamics.com secondary source.
- [S15] Jeffrey Dean, Luiz Andre Barroso, "The Tail at Scale,"
  Communications of the ACM 56(2):74-80, Feb 2013 -- confirmed live at
  https://research.google/pubs/the-tail-at-scale/ and
  https://www.barroso.org/publications/TheTailAtScale.pdf via WebSearch.
- [S16] Brendan Gregg, "The USE Method,"
  https://www.brendangregg.com/usemethod.html -- confirmed live via
  WebSearch.
- [S17] Benjamin H. Sigelman et al., "Dapper, a Large-Scale Distributed
  Systems Tracing Infrastructure," Google Technical Report, 2010 --
  confirmed via
  https://research.google/pubs/dapper-a-large-scale-distributed-systems-tracing-infrastructure/
  via WebSearch.
- [S18] Jay Kreps, "The Log: What every software engineer should know
  about real-time data's unifying abstraction," LinkedIn Engineering
  blog, 2013 -- confirmed live at
  https://engineering.linkedin.com/distributed-systems/log-what-every-software-engineer-should-know-about-real-time-datas-unifying
  via WebSearch.
- [S19] Kyle Kingsbury, Jepsen, https://jepsen.io/ and
  https://jepsen.io/analyses -- confirmed live via WebSearch; per-system
  finding counts drawn from WebSearch result summaries of Jepsen's own
  published analyses index.
- [S20] Leslie Lamport, *Specifying Systems*, Addison-Wesley, 2002, free
  at https://lamport.azurewebsites.net/tla/book.html; AWS industrial-use
  confirmation via
  https://lamport.azurewebsites.net/tla/industrial-use.html and
  secondary sources citing Newcombe et al., "How Amazon Web Services
  Uses Formal Methods," CACM 58(4), 2015 (the CACM paper itself not
  independently re-fetched this pass) -- confirmed via WebSearch.
- [S21] Sanjay Ghemawat, Howard Gobioff, Shun-Tak Leung, "The Google File
  System," SOSP 2003 -- confirmed live at
  https://research.google.com/archive/gfs-sosp2003.pdf via WebSearch.
- [S22] Jeffrey Dean, Sanjay Ghemawat, "MapReduce: Simplified Data
  Processing on Large Clusters," OSDI 2004 -- confirmed live at
  https://research.google/pubs/mapreduce-simplified-data-processing-on-large-clusters/
  via WebSearch.
- [S23] Fay Chang et al., "Bigtable: A Distributed Storage System for
  Structured Data," OSDI 2006, Best Paper -- confirmed via
  https://research.google/pubs/bigtable-a-distributed-storage-system-for-structured-data/
  via WebSearch.
- [S24] James C. Corbett et al., "Spanner: Google's Globally-Distributed
  Database," OSDI 2012, Best Paper -- confirmed live at
  https://research.google.com/archive/spanner-osdi2012.pdf via
  WebSearch.
- [S25] Abhishek Verma et al., "Large-scale cluster management at Google
  with Borg," EuroSys 2015 -- confirmed via
  https://research.google/pubs/large-scale-cluster-management-at-google-with-borg/
  via WebSearch.

- [S26] John L. Hennessy, David A. Patterson, *Computer Architecture: A
  Quantitative Approach* -- ISA-as-hardware/software-contract framing
  confirmed via WebSearch aggregate result (2017 ACM Turing Award
  citation confirmed); the book's own ABI/calling-convention chapter text
  was not independently re-fetched this pass -- reconstructed/well-known
  for that detail level.
- [S27] UEFI Forum specification framing + NSA Cybersecurity Technical
  Report, "UEFI Secure Boot Customization"
  (https://media.defense.gov/2023/Mar/20/2003182401/-1/-1/0/CTR-UEFI-SECURE-BOOT-CUSTOMIZATION-20230317.PDF)
  -- confirmed live via WebSearch; Secure Boot vs. Measured Boot
  distinction confirmed via multiple aggregate WebSearch results this
  pass.
- [S28] Linus Torvalds, kernel mailing list, Dec 2012,
  https://lkml.org/lkml/2012/12/23/75 ("WE DO NOT BREAK USERSPACE!");
  LWN.net, "Never break userspace," https://lwn.net/Articles/962527/;
  Linux kernel `Documentation/ABI` directory,
  https://github.com/torvalds/linux/tree/master/Documentation/ABI --
  all confirmed live via WebSearch this pass.
- [S29] Jon Postel, RFC 761 (1980) / RFC 1122 -- robustness principle
  origin, confirmed via WebSearch aggregate result; critique confirmed
  live via Martin Thomson & David Schinazi,
  https://datatracker.ietf.org/doc/html/draft-thomson-postel-was-wrong-03
  and Eric Allman, "The Robustness Principle Reconsidered," ACM Queue,
  https://queue.acm.org/detail.cfm?id=1999945 -- both confirmed live via
  WebSearch this pass.
- [S30] Barbara Liskov, ACM A.M. Turing Award citation and bibliography,
  https://amturing.acm.org/award_winners/liskov_1108679.cfm; Turing
  Award Lecture "The Power of Abstraction," OOPSLA 2009 keynote video,
  https://www.youtube.com/watch?v=qAKrMdUycb8 -- both confirmed live via
  WebSearch this pass.
- [S31] Butler Lampson, "Hints for Computer System Design," ACM SIGOPS
  Operating Systems Review 17(5), Oct 1983 -- confirmed live at
  https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/acrobat-17.pdf
  via WebSearch this pass.
- [S32] James Hamilton, "On Designing and Deploying Internet-Scale
  Services," LISA '07 -- confirmed live at
  https://s3.amazonaws.com/systemsandpapers/papers/hamilton.pdf via
  WebSearch this pass.
- [S33] Bryan Cantrill biographical/contributor-role confirmation via
  Wikipedia (https://en.wikipedia.org/wiki/Bryan_Cantrill) and
  grokipedia.com summary, cross-checked against his own site
  (https://bcantrill.dtrace.org/about/) -- confirmed via WebSearch this
  pass; a specific talk transcript was not independently fetched this
  pass (lesson content is reconstructed/well-known from his publicly
  known DTrace/Oxide positions, not page/transcript-verified).
- [S34] Rob Pike biographical/contributor-role confirmation via Wikipedia
  (https://en.wikipedia.org/wiki/Rob_Pike) -- confirmed via WebSearch
  this pass; UTF-8 co-creation with Ken Thompson (1992) and Plan 9
  co-leadership confirmed via the same source. "Concurrency is Not
  Parallelism" talk (Heroku Waza 2012) title/venue confirmed via
  WebSearch aggregate result, talk content not independently re-fetched
  this pass.
- [S35] Margaret Hamilton biographical confirmation via Wikipedia
  (https://en.wikipedia.org/wiki/Margaret_Hamilton_(software_engineer))
  and IEEE Computer Society
  (https://www.computer.org/publications/tech-news/events/what-to-know-about-the-scientist-who-invented-the-term-software-engineering)
  -- confirmed via WebSearch this pass; held out of the full lesson
  table (sec. 14) pending a directly citable primary talk/paper URL,
  per this corpus's own honesty gate.

Companion documents (not re-cited per-entry, referenced by pointer per
the no-duplication instruction): `docs/design/structural-linter-adversarial-hardening.md`,
`docs/design/architecture-check-catalog.md`, and the T-0331 EPIC ticket
body in `tickets.md`.

---

## DENOMINATOR MANIFEST

Machine-readable, one entry per named row across every markdown table
in sections 1-14 above (mechanically extracted; checkability inferred
from each row's own STRATA-CHECKABILITY cell text: 'provable' ->
tier1-static, 'not-checkable' -> tier3-not-checkable, else
tier2-advisory). Format: `- id: <STABLE-ID> | catalog: <section> |
checkability: <tag> | trap-ref: <section number>`, with an optional
trailing `| artifact: true | artifact-reason: <why>` on rows below that
are not real named entries. This is what the exhaustiveness drift-lock
test binds against.

**Manifest-extraction-artifact disposition (RECONCILIATION.md finding
(d), T-0677)**: the mechanical extraction that built this list re-scans
every markdown table row in sections 1-14 by first-column text, with no
special-casing for a table that has no dedicated "Name"/"Item"/"Topic"
column of its own. For a table whose first column is literally the
`STRATA-CHECKABILITY` header (sections 1.2-1.6, 5.2-5.3, 10.1) or the
`Best practice` header (section 13's five seam tables), the extractor
picked up the *header cell text itself* as if it were a distinct named
row, on top of the table's real (possibly single) data row -- and for
two of section 1's headerless tables, the data row's own checkability
value (`advisory`, `not-checkable`) was short enough to be
indistinguishable from a second header-artifact once slugified. **14 of
the 119 ids below are these mechanical-extraction artifacts, not real
catalogued entries** -- each is marked `| artifact: true |
artifact-reason: mechanical-extraction (header-cell/short-cell-value
mis-scanned as a named row)` in place, rather than deleted, so a diff of
this doc still shows exactly what changed and why (never silently drop a
discrepancy). The genuine content is **105 entries**; `system-
design.yaml` mirrors this exact split with
`disposition: "out-of-scope(manifest-extraction-artifact)"` on the same
14 ids. A parser can therefore either sum `TOTAL` as-is (119, matching
this doc's own historical manifest count) or filter on `artifact: true`
to get the genuine 105 -- no hardcoded exclusion list is required either
way.

- id: SDC-1-NETWORK-RELIABILITY | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-1-LATENCY-NON-ZERO | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-1-BANDWIDTH-FINITE | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-1-NETWORK-INSECURE | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-1-TOPOLOGY-CHANGES | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-1-SINGLE-ADMINISTRATOR-FALSE | catalog: system-design-corpus-sec-1 | checkability: tier2-advisory | trap-ref: 1
- id: SDC-1-TRANSPORT-COST-NONZERO | catalog: system-design-corpus-sec-1 | checkability: tier2-advisory | trap-ref: 1
- id: SDC-1-HETEROGENEOUS-NETWORK-COMPONENT-VERSIONING-SIMPLE-AZURE-VARIANT-OBSERVABILITY-CAN-BE | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-1-STRATA-CHECKABILITY | catalog: system-design-corpus-sec-1 | checkability: tier2-advisory | trap-ref: 1 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-1-ADVISORY | catalog: system-design-corpus-sec-1 | checkability: tier2-advisory | trap-ref: 1 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-1-STRATA-CHECKABILITY-2 | catalog: system-design-corpus-sec-1 | checkability: tier2-advisory | trap-ref: 1 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-1-NOT-CHECKABLE | catalog: system-design-corpus-sec-1 | checkability: tier3-not-checkable | trap-ref: 1 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-1-STRATA-CHECKABILITY-3 | catalog: system-design-corpus-sec-1 | checkability: tier2-advisory | trap-ref: 1 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-1-PROVABLE-PRESENCE-OF-ENDPOINT-CHECK-PROXY-ADVISORY-PLACEMENT-JUDGMENT | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-1-STRATA-CHECKABILITY-4 | catalog: system-design-corpus-sec-1 | checkability: tier2-advisory | trap-ref: 1 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-1-PROVABLE-PRESENCE-PROXY | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-1-STRATA-CHECKABILITY-5 | catalog: system-design-corpus-sec-1 | checkability: tier2-advisory | trap-ref: 1 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-1-PROVABLE-DECLARATION-PRESENCE-NOT-THE-GUARANTEE-ITSELF | catalog: system-design-corpus-sec-1 | checkability: tier1-static | trap-ref: 1
- id: SDC-2-PAXOS | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-MULTI-PAXOS | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-RAFT | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-ZAB-ZOOKEEPER-ATOMIC-BROADCAST | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-VIEWSTAMPED-REPLICATION-VR | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-2PC-TWO-PHASE-COMMIT | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-3PC-THREE-PHASE-COMMIT | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-LEASES | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-QUORUMS | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-2-CRDTS-CONFLICT-FREE-REPLICATED-DATA-TYPES | catalog: system-design-corpus-sec-2 | checkability: tier1-static | trap-ref: 2
- id: SDC-3-LEADER-FOLLOWER-SINGLE-LEADER-REPLICATION | catalog: system-design-corpus-sec-3 | checkability: tier1-static | trap-ref: 3
- id: SDC-3-MULTI-LEADER-REPLICATION | catalog: system-design-corpus-sec-3 | checkability: tier1-static | trap-ref: 3
- id: SDC-3-LEADERLESS-DYNAMO-STYLE-REPLICATION | catalog: system-design-corpus-sec-3 | checkability: tier1-static | trap-ref: 3
- id: SDC-3-SHARDING-STRATEGIES-RANGE-HASH-DIRECTORY-BASED | catalog: system-design-corpus-sec-3 | checkability: tier1-static | trap-ref: 3
- id: SDC-3-CONSISTENT-HASHING | catalog: system-design-corpus-sec-3 | checkability: tier1-static | trap-ref: 3
- id: SDC-3-REBALANCING | catalog: system-design-corpus-sec-3 | checkability: tier2-advisory | trap-ref: 3
- id: SDC-3-HOT-PARTITION-HANDLING | catalog: system-design-corpus-sec-3 | checkability: tier1-static | trap-ref: 3
- id: SDC-4-LSM-TREE-VS-B-TREE-STORAGE-ENGINES | catalog: system-design-corpus-sec-4 | checkability: tier2-advisory | trap-ref: 4
- id: SDC-4-TRANSACTIONS-ISOLATION-LEVELS | catalog: system-design-corpus-sec-4 | checkability: tier1-static | trap-ref: 4
- id: SDC-4-DISTRIBUTED-TRANSACTIONS | catalog: system-design-corpus-sec-4 | checkability: tier1-static | trap-ref: 4
- id: SDC-4-BATCH-VS-STREAM-PROCESSING | catalog: system-design-corpus-sec-4 | checkability: tier2-advisory | trap-ref: 4
- id: SDC-4-EXACTLY-ONCE-PROCESSING | catalog: system-design-corpus-sec-4 | checkability: tier1-static | trap-ref: 4
- id: SDC-4-IDEMPOTENCY | catalog: system-design-corpus-sec-4 | checkability: tier1-static | trap-ref: 4
- id: SDC-4-OUTBOX-SAGA-PATTERNS | catalog: system-design-corpus-sec-4 | checkability: tier1-static | trap-ref: 4
- id: SDC-4-CHANGE-DATA-CAPTURE-CDC | catalog: system-design-corpus-sec-4 | checkability: tier1-static | trap-ref: 4
- id: SDC-5-PROVABLE-DECLARATION-PRESENCE | catalog: system-design-corpus-sec-5 | checkability: tier1-static | trap-ref: 5
- id: SDC-5-STRATA-CHECKABILITY | catalog: system-design-corpus-sec-5 | checkability: tier2-advisory | trap-ref: 5 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-5-NOT-CHECKABLE-THE-PRACTICE-ITSELF-IS-RUNTIME-EVIDENCE-NOT-A-STATIC-FACT | catalog: system-design-corpus-sec-5 | checkability: tier3-not-checkable | trap-ref: 5
- id: SDC-5-STRATA-CHECKABILITY-2 | catalog: system-design-corpus-sec-5 | checkability: tier2-advisory | trap-ref: 5 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-5-TIMEOUT | catalog: system-design-corpus-sec-5 | checkability: tier1-static | trap-ref: 5
- id: SDC-5-RETRY-BACKOFF-JITTER | catalog: system-design-corpus-sec-5 | checkability: tier1-static | trap-ref: 5
- id: SDC-5-IDEMPOTENT-RECEIVER | catalog: system-design-corpus-sec-5 | checkability: tier1-static | trap-ref: 5
- id: SDC-5-LOAD-SHEDDING | catalog: system-design-corpus-sec-5 | checkability: tier1-static | trap-ref: 5
- id: SDC-5-SHUFFLE-SHARDING | catalog: system-design-corpus-sec-5 | checkability: tier2-advisory | trap-ref: 5
- id: SDC-6-LITTLE-S-LAW-L-LAMBDA-W | catalog: system-design-corpus-sec-6 | checkability: tier2-advisory | trap-ref: 6
- id: SDC-6-UNIVERSAL-SCALABILITY-LAW-USL | catalog: system-design-corpus-sec-6 | checkability: tier2-advisory | trap-ref: 6
- id: SDC-6-QUEUEING-THEORY-BASICS-M-M-1-ETC | catalog: system-design-corpus-sec-6 | checkability: tier2-advisory | trap-ref: 6
- id: SDC-6-THE-TAIL-AT-SCALE | catalog: system-design-corpus-sec-6 | checkability: tier1-static | trap-ref: 6
- id: SDC-6-USE-METHOD-UTILIZATION-SATURATION-ERRORS | catalog: system-design-corpus-sec-6 | checkability: tier1-static | trap-ref: 6
- id: SDC-7-THREE-PILLARS-METRICS-LOGS-TRACES | catalog: system-design-corpus-sec-7 | checkability: tier1-static | trap-ref: 7
- id: SDC-7-DISTRIBUTED-TRACING-DAPPER | catalog: system-design-corpus-sec-7 | checkability: tier1-static | trap-ref: 7
- id: SDC-7-HIGH-CARDINALITY-STRUCTURED-EVENTS-HONEYCOMB-CHARITY-MAJORS | catalog: system-design-corpus-sec-7 | checkability: tier1-static | trap-ref: 7
- id: SDC-7-SLO-BASED-ALERTING | catalog: system-design-corpus-sec-7 | checkability: tier1-static | trap-ref: 7
- id: SDC-8-AT-MOST-ONCE | catalog: system-design-corpus-sec-8 | checkability: tier1-static | trap-ref: 8
- id: SDC-8-AT-LEAST-ONCE | catalog: system-design-corpus-sec-8 | checkability: tier1-static | trap-ref: 8
- id: SDC-8-EXACTLY-ONCE | catalog: system-design-corpus-sec-8 | checkability: tier3-not-checkable | trap-ref: 8
- id: SDC-8-IDEMPOTENT-CONSUMERS | catalog: system-design-corpus-sec-8 | checkability: tier1-static | trap-ref: 8
- id: SDC-8-ORDERING-GUARANTEES | catalog: system-design-corpus-sec-8 | checkability: tier1-static | trap-ref: 8
- id: SDC-8-THE-LOG-ABSTRACTION | catalog: system-design-corpus-sec-8 | checkability: tier1-static | trap-ref: 8
- id: SDC-9-12-FACTOR-APP | catalog: system-design-corpus-sec-9 | checkability: tier1-static | trap-ref: 9
- id: SDC-9-IMMUTABLE-INFRASTRUCTURE | catalog: system-design-corpus-sec-9 | checkability: tier1-static | trap-ref: 9
- id: SDC-9-BLUE-GREEN-CANARY-PROGRESSIVE-DELIVERY | catalog: system-design-corpus-sec-9 | checkability: tier1-static | trap-ref: 9
- id: SDC-9-AUTOSCALING | catalog: system-design-corpus-sec-9 | checkability: tier1-static | trap-ref: 9
- id: SDC-9-MULTI-REGION-DISASTER-RECOVERY-RTO-RPO | catalog: system-design-corpus-sec-9 | checkability: tier1-static | trap-ref: 9
- id: SDC-9-CELL-BASED-ARCHITECTURE | catalog: system-design-corpus-sec-9 | checkability: tier1-static | trap-ref: 9
- id: SDC-10-NOT-CHECKABLE-THE-FINDINGS-THEMSELVES-ARE-EMPIRICAL-PER-SYSTEM | catalog: system-design-corpus-sec-10 | checkability: tier3-not-checkable | trap-ref: 10
- id: SDC-10-STRATA-CHECKABILITY | catalog: system-design-corpus-sec-10 | checkability: tier2-advisory | trap-ref: 10 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-10-ADVISORY-FORMAL-SPEC-IS-ORTHOGONAL-TO-STRATA-S-STATIC-ANALYSIS-APPROACH-A-DIFFERENT | catalog: system-design-corpus-sec-10 | checkability: tier1-static | trap-ref: 10
- id: SDC-11-THE-GOOGLE-FILE-SYSTEM | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-MAPREDUCE-SIMPLIFIED-DATA-PROCESSING-ON-LARGE-CLUSTERS | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-BIGTABLE-A-DISTRIBUTED-STORAGE-SYSTEM-FOR-STRUCTURED-DATA | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-SPANNER-GOOGLE-S-GLOBALLY-DISTRIBUTED-DATABASE | catalog: system-design-corpus-sec-11 | checkability: tier1-static | trap-ref: 11
- id: SDC-11-DAPPER-A-LARGE-SCALE-DISTRIBUTED-SYSTEMS-TRACING-INFRASTRUCTURE | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-LARGE-SCALE-CLUSTER-MANAGEMENT-AT-GOOGLE-WITH-BORG | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-THE-CHUBBY-LOCK-SERVICE-FOR-LOOSELY-COUPLED-DISTRIBUTED-SYSTEMS | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-DYNAMO-AMAZON-S-HIGHLY-AVAILABLE-KEY-VALUE-STORE | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-COMPANY | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-NETFLIX | catalog: system-design-corpus-sec-11 | checkability: tier3-not-checkable | trap-ref: 11
- id: SDC-11-UBER | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-DISCORD | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-11-SHOPIFY | catalog: system-design-corpus-sec-11 | checkability: tier1-static | trap-ref: 11
- id: SDC-11-STRIPE | catalog: system-design-corpus-sec-11 | checkability: tier1-static | trap-ref: 11
- id: SDC-11-SLACK | catalog: system-design-corpus-sec-11 | checkability: tier1-static | trap-ref: 11
- id: SDC-11-FIGMA | catalog: system-design-corpus-sec-11 | checkability: tier2-advisory | trap-ref: 11
- id: SDC-12-MONOLITHFIRST-MARTIN-FOWLER-MARTINFOWLER-COM-BLIKI-MONOLITHFIRST-HTML-2015-LIVE-VER | catalog: system-design-corpus-sec-12 | checkability: tier2-advisory | trap-ref: 12
- id: SDC-12-CHOOSE-BORING-TECHNOLOGY-DAN-MCKINLEY-MCFUNLEY-COM-CHOOSE-BORING-TECHNOLOGY-LIVE-VE | catalog: system-design-corpus-sec-12 | checkability: tier2-advisory | trap-ref: 12
- id: SDC-12-GOODBYE-MICROSERVICES-ORIGINALLY-SEGMENT-ENGINEERING-BLOG-2018-NOW-HOSTED-AT-TWILIO | catalog: system-design-corpus-sec-12 | checkability: tier2-advisory | trap-ref: 12
- id: SDC-12-DECONSTRUCTING-THE-MONOLITH-AND-UNDER-DECONSTRUCTION-THE-STATE-OF-SHOPIFY-S-MONOLIT | catalog: system-design-corpus-sec-12 | checkability: tier1-static | trap-ref: 12
- id: SDC-13-A-DECLARED-ABI-ISA-TARGET-IS-STABLE-ACROSS-A-COMPATIBILITY-WINDOW-A-COMPILED-ARTIFA | catalog: system-design-corpus-sec-13 | checkability: tier1-static | trap-ref: 13
- id: SDC-13-BEST-PRACTICE | catalog: system-design-corpus-sec-13 | checkability: tier2-advisory | trap-ref: 13 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-13-EVERY-BOOT-CHAIN-STAGE-IS-SIGNED-SECURE-BOOT-OR-MEASURED-INTO-AN-ATTESTABLE-LOG-MEA | catalog: system-design-corpus-sec-13 | checkability: tier1-static | trap-ref: 13
- id: SDC-13-BEST-PRACTICE-2 | catalog: system-design-corpus-sec-13 | checkability: tier2-advisory | trap-ref: 13 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-13-EVERY-KERNEL-USERSPACE-INTERFACE-SYSCALL-PROCFS-SYSFS-ENTRY-IOCTL-IS-CLASSIFIED-INT | catalog: system-design-corpus-sec-13 | checkability: tier1-static | trap-ref: 13
- id: SDC-13-BEST-PRACTICE-3 | catalog: system-design-corpus-sec-13 | checkability: tier2-advisory | trap-ref: 13 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-13-EVERY-DEPLOYED-PROCESS-DECLARES-ITS-RESOURCE-BOUNDS-CGROUP-LIMITS-CPU-MEMORY-IO-AND | catalog: system-design-corpus-sec-13 | checkability: tier1-static | trap-ref: 13
- id: SDC-13-BEST-PRACTICE-4 | catalog: system-design-corpus-sec-13 | checkability: tier2-advisory | trap-ref: 13 | artifact: true | artifact-reason: mechanical-extraction (header-cell/short-cell-value mis-scanned as a named row)
- id: SDC-13-EVERY-SERVICE-TO-SERVICE-API-DECLARES-AN-EXPLICIT-SCHEMA-CONTRACT-WITH-A-VERSIONING | catalog: system-design-corpus-sec-13 | checkability: tier1-static | trap-ref: 13
- id: SDC-14-LINUS-TORVALDS | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
- id: SDC-14-BARBARA-LISKOV | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
- id: SDC-14-BUTLER-LAMPSON | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
- id: SDC-14-LESLIE-LAMPORT | catalog: system-design-corpus-sec-14 | checkability: tier2-advisory | trap-ref: 14
- id: SDC-14-WERNER-VOGELS | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
- id: SDC-14-JAMES-HAMILTON | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
- id: SDC-14-BRYAN-CANTRILL | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
- id: SDC-14-ROB-PIKE | catalog: system-design-corpus-sec-14 | checkability: tier2-advisory | trap-ref: 14
- id: SDC-14-KEN-THOMPSON | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
- id: SDC-14-DENNIS-RITCHIE | catalog: system-design-corpus-sec-14 | checkability: tier2-advisory | trap-ref: 14
- id: SDC-14-MICHAEL-STONEBRAKER | catalog: system-design-corpus-sec-14 | checkability: tier2-advisory | trap-ref: 14
- id: SDC-14-DAVID-CUTLER | catalog: system-design-corpus-sec-14 | checkability: tier2-advisory | trap-ref: 14
- id: SDC-14-ANDREW-S-TANENBAUM | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
- id: SDC-14-MARGARET-HAMILTON | catalog: system-design-corpus-sec-14 | checkability: tier1-static | trap-ref: 14
TOTAL: 119 (105 genuine + 14 artifact: true rows, per RECONCILIATION.md
finding (d) / T-0677 -- filter on `artifact: true` for the genuine-only
count, no hardcoded exclusion list needed)
