+++
id = "01M3AXSD9Y63ETVPHNP3V0WSN0"
title = "SYSDESIGN304: high-fanout cache-fill flow with `stampede_guard` undeclared or unproven"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSDASH31CMNHAQ9JXR1YQ"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-04T22:22:25Z"
aliases = ["T-6462"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["src/frob/strata/_stampede.py (new)", "tests/fixtures/sysdesign/sysdesign304/**"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD8GJ5GX7CMF943DYKWJ"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
title: SYSDESIGN304: high-fanout cache-fill flow with stampede_guard undeclared or unproven
kind: feature
tier: leaf
parent: T-SYS-SE
milestone: 0.539.0
sprint: sysdesign
points: 3
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
scope: src/frob/strata/_stampede.py (new), docs/modules/gates.md (SYSDESIGN304 row),
       tests/fixtures/sysdesign/sysdesign304/**
blocked_by: [T-SYS-A-INFRA-CACHE-QUEUE]
tag: Static: design (declared-vs-observed pair; see dynamic-only note below)

<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its scaffold" -->Research row 8.3 is tagged dynamic-only in scratchpad/sysdesign-research.md ("Hot-key
cache-read code with no single-flight/lock guard around the recompute-on-miss path flags a
stampede risk when the design model marks the key as high-QPS | dynamic-only"). Per the owner
stance, the RUNTIME stampede-under-load behavior itself is a test obligation, not a static
rule, and is filed as a dropped ticket in Story H (T-SYS-DROP-STAMPEDE-DYNAMIC), not
reintroduced here.

This leaf is a distinct, legitimately static companion, the same two-step pattern REL220/221
already uses for backoff: STRATA-EXPRESSIVENESS.md's `stampede_guard` grammar proposal (section
C) states "Enables RULE: high-fanout flow into a cache-fill with no stampede_guard =
thundering-herd risk (pairs with existing `fanout` numeric on the same flow -- REL-family, e.g.
REL262). Authority: Meta/memcached 'leases' paper, Vattani et al. probabilistic early
expiration." SYSDESIGN304 checks DECLARATION and PROOF of `stampede_guard` (does the flow
declare it, does bound code contain a real lock/single-flight/probabilistic-early-expiry
token) -- it does not attempt to detect an actual stampede at runtime, so it does not
contradict row 8.3's dynamic-only tag.

Acceptance criteria: SYSDESIGN304 fires on either of two conditions, folded into one id per
the coordinator's contiguous-numbering directive -- a cache-fill flow with `fanout` above a
threshold and no `stampede_guard` declared flags; a flow declaring `stampede_guard` with no
bound code containing a real lock/single-flight/probabilistic-early-expiry token also flags,
unproven. Positive-control fixture: tests/fixtures/sysdesign/sysdesign304/
high-fanout-no-stampede-guard/**.
