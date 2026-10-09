+++
id = "01M3AXSD8GJ5GX7CMF943DYKWJ"
title = "GRAMMAR: cache `stampede_guard` and queue `partitions`+`keyed_by`"
type = "task"
category = "todo"
priority = "low"
parent = "01M3AXSDBEQGV8V5VHYGXBEQTV"
reporter = "agent"
created = "2026-09-25T00:00:00Z"
updated = "2026-10-09T20:42:11Z"
aliases = ["T-6416"]
labels = ["v1-cluster:B1", "area:grimble", "triage:accepted", "milestone:0.538.0"]
scope = ["strata-core/src/parse/grammar_infra.rs", "docs/strata/surface.md#std-infra", "src/frob/strata/_models.py", "docs/design/grmb-spec.md"]

[[links]]
kind = "blocked-by"
target = "01M3AXSD926S7M96AQB9BTK4E2"

[[links]]
kind = "blocked-by"
target = "01M3AXSD9WQ0QPZJ3E2G99DAXB"
+++

frob:waive DOC006 reason="future-facing paths: every file named here is created by this ticket or its story scaffold, none exists on dev yet"
OWNER-OWNED: strata surface change; owner reviews before dispatch


title: GRAMMAR: cache stampede_guard and queue partitions+keyed_by
kind: feature (OWNER-OWNED)
tier: leaf
parent: T-SYS-SA
milestone: 0.539.0
sprint: sysdesign
points: 3
scope: strata-core/src/parse/grammar_infra.rs, docs/strata/surface.md#std-infra,
       src/frob/strata/_models.py, tests/fixtures/sysdesign/infra-cache-queue/**
blocked_by: [T-SYS-A-INFRA-STORE, T-STORE-301-ATTR]

Findings (STRATA-EXPRESSIVENESS.md, section C "DATA" and B "COMMUNICATION"):

cache stampede -- "NOT EXPRESSIBLE. Proposal (GRAMMAR): cache_prop `stampede_guard IDENT`
(lock|probabilistic_early_expiry|request_coalescing)... Enables RULE: high-fanout flow into a
cache-fill with no stampede_guard = thundering-herd risk (pairs with existing `fanout` numeric
on the same flow -- REL-family, e.g. REL262). Authority: Meta/memcached 'leases' paper, Vattani
et al. probabilistic early expiration."

stream partitions -- "`queue` has `delivery`/`ordering`/`clearance` but no partition-count or
consumer-group concept... Proposal (GRAMMAR): queue_prop addition `partitions INT` and
`keyed_by IDENT` (the second one is already spelled identically on `cache` -- reuse the same
token)... Enables RULE: 'an `ordering` claim on a queue with `partitions > 1` and no
`keyed_by` is an unproven global-ordering claim' -- authority: Kafka partitioning/
consumer-group model, Confluent's ordering guarantees doc."

Acceptance criteria: `stampede_guard` and `partitions`/`keyed_by` land in the same
grammar_infra.rs pass (sequenced after T-SYS-A-INFRA-STORE's store_prop change in the same
file). `partitions` is a typed field (per-partition throughput arithmetic feeds a future
REL-family rule); `stampede_guard` and queue `keyed_by` desugar to attrs. Positive-control
<!-- frob:waive DOC006 reason="future-facing: created by this ticket or its story scaffold" -->
fixture: tests/fixtures/sysdesign/infra-cache-queue/high-fanout-no-stampede-guard/design.strata.
