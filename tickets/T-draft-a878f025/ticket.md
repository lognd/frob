---
id: T-draft-a878f025
title: 'SYSDESIGN: system-design linting and strata architecture expressiveness'
state: queued
kind: feature
origin: agent
created: '2026-09-25'
priority: medium
parent: null
tier: epic
sprint: sysdesign
runs_last: false
milestone: 0.539.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope_breadth_ack: true
scope_breadth_ack_reason: epic parent, no direct code scope
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN: system-design linting and strata architecture expressiveness
kind: feature
tier: epic
parent: (none)
milestone: 0.539.0
sprint: sysdesign
scope: (none -- epic, no direct code scope)
blocked_by: []

Body:

Strata must be able to model any mature, horizontally scaled, distributed system, and frob
must lint toward an optimized design once that system is modeled -- not just toward "does not
crash." This epic covers two coupled gaps found by three research passes (scratchpad/
sysdesign-research.md, scratchpad/SYSDESIGN-INVENTORY.md, scratchpad/STRATA-EXPRESSIVENESS.md):
(1) strata's surface grammar cannot express roughly a third of the taxonomy of mature-system
concerns (serverless lifecycle, deployment cells/multi-region, store sharding/consistency,
request hedging, cache stampede guards, and -- the single highest-leverage item -- a fixed,
Python-hardcoded trust/label lattice that blocks tenancy, compliance zones, and environment
axes all at once); and (2) even where strata IS expressive enough (e.g. the `boundary { admit
{ rate_limit; max_size; } }` six-phase construct), no rule reads the declaration the way
REL200/REL210 read `timeout`/`health`, and frob ingests zero config surfaces (Kubernetes,
Helm, Terraform, docker-compose, Envoy/NGINX/Caddy) that would let a SYSDESIGN rule see the
deployed shape at all.

## Scaling stance (verbatim from scratchpad/sysdesign-research.md, "Scaling stance" section)

**What "plan for horizontal scale from the start" concretely requires, per the sourced
authorities:**

1. **Statelessness is the load-bearing precondition.** 12-Factor: "Twelve-factor processes are
   stateless and share-nothing" (https://12factor.net/processes). AWS Well-Architected REL05-BP06
   makes the same claim from the reliability angle: "Systems that are designed to be stateless are
   more adaptable to horizontal scaling, making it possible to add or remove capacity based on
   fluctuating traffic and demand" (https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_stateless.html).
   Both authorities treat this as a day-one design constraint, not a later refactor -- once session
   state or local caches are load-bearing, retrofitting statelessness requires a migration, not a
   config change.
2. **Idempotency and retry discipline must exist before the first retry is written**, because Google
   SRE's cascading-failures chapter documents that naive, unbounded, un-jittered retries are what
   *cause* the outages horizontal scaling is meant to survive (https://sre.google/sre-book/addressing-cascading-failures/):
   "retries can destabilize a system... This pattern has contributed to several cascading failures."
   Retry budgets, backoff+jitter, and idempotency keys (Stripe, https://stripe.com/blog/idempotency)
   are cheap to add at day one and expensive to retrofit once every client has its own retry logic.
3. **Externalizing state to a shared-nothing-friendly backing service** (queue, cache, DB with
   replicas) is a day-one decision per AWS REL05-BP01: writes can be buffered "so that write
   requests from customers can still be accepted even if the primary is temporarily unavailable"
   (https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/rel_mitigate_interaction_failure_graceful_degradation.html).
4. **Health checks, readiness/liveness distinction, graceful shutdown, and resource requests/limits
   are the minimum viable Kubernetes-native horizontal contract** -- without them, an autoscaler or
   rolling deploy actively drops traffic instead of smoothly redistributing it (Kubernetes Pod
   Lifecycle docs, https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/; PDB docs,
   https://kubernetes.io/docs/tasks/run-application/configure-pdb/).
5. **Criticality/priority propagation and admission control (load shedding) should be designed in
   from the start** per Google SRE's "Handling Overload" chapter, because retrofitting criticality
   tagging into an existing RPC fabric after the fact requires touching every call site
   (https://sre.google/sre-book/handling-overload/).

**What can be deferred:**

- **Sharding/partitioning of the data tier** can be deferred until a single primary's write
  capacity is empirically approaching its ceiling -- AWS explicitly frames the single-writer
  limitation as a scaling constraint to *mitigate when it bites* (Multi-AZ, read replicas, Aurora
  Serverless), not as a day-one requirement.
- **CQRS and event sourcing** are explicitly *not* general-purpose starting points. Azure's own
  pattern catalog frames CQRS as applicable "where warranted" -- a targeted response to a
  measured read/write scaling or model-complexity divergence, not a default architecture.
- **Full microservice decomposition** can be deferred behind a modular monolith. 12-Factor's
  "Concurrency" factor frames horizontal scale-out as "scale out via the process model" -- run
  more stateless processes of the same codebase, which does not require service decomposition.
  Google Cloud's Architecture Framework reliability pillar lists "Take advantage of horizontal
  scalability" as a top-level recommendation independent of any microservices recommendation.
  AWS and Azure Well-Architected guidance never states "start with microservices"; every
  resilience pattern cited (circuit breaker, bulkhead, throttling, retry, cache-aside, CQRS,
  outbox) is presented as a pattern to *apply to a service* once a concrete need is identified.

**Known anti-patterns of premature microservices:** splitting a write-path into multiple
services before a distinct scaling/ownership/fault-isolation reason exists multiplies the exact
retry-amplification hazard Google SRE describes ("a single user action may create 64 attempts
(4^3) on the database"); more hops means more independent retry/timeout/circuit-breaker surfaces
to get right. Applying CQRS/event sourcing with no stated divergent-scaling or audit/replay
rationale is filed as a lint condition (sec. 8.7/8.10 of the research) precisely because these
patterns are targeted tools, not defaults.

## Coverage tallies (from scratchpad/SYSDESIGN-INVENTORY.md and STRATA-EXPRESSIVENESS.md)

Research catalogue: 76 rows across 10 sections (10/10/10/8/10/10/13/10/10/8) plus the closing
Scaling Stance section. 2 rows are tagged dynamic-only (8.3 cache stampede, 9.8 chaos testing).
Sections 3, 5, 6 are strongly sourced with direct verbatim quotes; sections 1, 2, 4, 8, 9, 10
mix directly-quoted rows with pillar/title-level citations (flagged inline per row). Netflix,
Shopify, Discord, Uber engineering blogs (all explicitly requested authorities) were not
successfully incorporated -- Netflix was attempted and blocked by Cloudflare bot protection;
Shopify/Discord/Uber were not attempted. NIST SP 800-41 is cited by title only (csrc.nist.gov
served a frame-buster page).

Existing frob coverage inventory (SYSDESIGN-INVENTORY.md sec 4 "Completeness checklist"):
COVERED -- load balancer policy/sticky, CDN, cache ttl/staleness/invalidation, queue delivery/
ordering, queue load leveling (REL260/261), capacity/demand/growth/fanout/skew (CAP001),
replicas/redundancy/SPOF (REL250), health checks/timeouts/retries/backoff/circuit-breaker/
bulkhead (the full REL2xx/3xx family), deploy strategies (DEPLOY001-003), crash/breach
contracts, idempotency keys (REL221), RPO (store rpo QUANTITY), observability (REL270/271/272),
secrets (SEC001-005/SEC110). NONE -- rate limiting (WEBSEC reserved-not-shipped), WAF/firewall/
segmentation/zero-trust/mTLS, DNS, request size/header limits (WEBSEC reserved), graceful
shutdown/SIGTERM, autoscaling (HPA) by name, PodDisruptionBudget, multi-AZ/region, RTO,
connection pooling (SQL106 reserved), migrations expand/contract, outbox/event sourcing.
PARTIAL -- TLS/cert, deadline propagation, statelessness/session externalization, resource
requests/limits.

Strata expressiveness audit tallies (STRATA-EXPRESSIVENESS.md, ~85 taxonomy rows): EXPRESSIBLE
28, PARTIAL 32, NOT EXPRESSIBLE 25. Single highest-leverage finding: the fixed TRUST/LABELS
lattice (_models.py:67-76, hardcoded Python constants with no surface-grammar production) is
the root cause behind roughly a third of the PARTIAL/NOT rows -- tenancy isolation, compliance
zones, environments (dev/stage/prod), and multi-region active-active semantics all want "one
more rung" on either axis and currently cannot get one without an owner-level Python change.
The `lattice` GRAMMAR proposal (Story A, first leaf) is triaged ahead of every other proposal
for this reason.

Correction carried from STRATA-EXPRESSIVENESS.md: rate limiting and request-size limits ARE
expressible in the surface grammar today (`boundary`'s `admit { rate_limit; max_size; }`
six-phase construct, T-0069) -- the gap is that no REL-family rule reads it yet, not that the
grammar is missing it. Surface expressiveness and shipped enforcement are two different layers
and must not be conflated when filing leaves (see Story D).

## Owner stance encoded in every child ticket

- Strata must be able to model any mature, horizontally scaled, distributed system -- Story A.
- frob lints toward an optimized design, not just "does not crash" -- every rule leaf in
  Stories C-G.
- Plan for horizontal (shared-nothing, microservices-style) scale from the start -- reflected in
  which rows are filed as day-one static rules vs. deferred (sharding/CQRS/event-sourcing stay
  RULE-ONLY completeness checks on an explicit declaration, never a default requirement).
- Every rule cites its authority in the reason text -- every leaf body below carries its
  research-row quote verbatim; rows with a weak/gap citation are marked as such and, where the
  gap itself blocks confident rule authorship, routed through Story H's research leaf first.
- Dynamic-only rows become test obligations, never static rules -- Story H's two dropped
  tickets (T-SYS-DROP-STAMPEDE-DYNAMIC, T-SYS-DROP-CHAOS-DYNAMIC) cover research rows 8.3/9.8.
  Where a declared-vs-observed STATIC companion is separately justified (e.g. SYSDESIGN304
  checking that `stampede_guard` is declared and proven, the same REL220/221 two-step pattern),
  that companion is filed as its own rule leaf and is not a re-statement of the dynamic-only row.
- Cut scope is a dropped ticket with a reason, never deleted -- see Story H.

## Children

Story A (T-SYS-SA): strata expressiveness -- model any scaled system.
Story B (T-SYS-SB): config-surface ingestion.
Story C (T-SYS-SC): edge and network (SYSDESIGN101+).
Story D (T-SYS-SD): admission and rate limiting (SYSDESIGN201+).
Story E (T-SYS-SE): resilience gaps not in REL (SYSDESIGN301+).
Story F (T-SYS-SF): horizontal-scaling readiness (SYSDESIGN401+).
Story G (T-SYS-SG): data tier and operations (SYSDESIGN501+).
Story H (T-SYS-SH): authority gaps and dropped rows.
