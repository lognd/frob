---
id: T-4072
title: 'M-3: generated-types staleness check plus hand-written-interface ban'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: high
blocked_by:
- T-3991
parent: T-4071
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/policy/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given T-3991's GEN001 mechanism, when it lands, then npm run types --check
    is wired as its first proof-of-concept generator/output pair
  evidence: []
- text: given a hand-written response interface/type literal in src/api/**, when the
    new lint rule runs, then it is flagged
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
M-3 (F-273), FILED FIRST as instructed -- the cheapest high-value item across all eight audit lists so far. The consumer's own framing: "nothing checks TS interfaces against backend/openapi.json, EVEN THOUGH npm run types (frontend/package.json:22) ALREADY GENERATES THE CORRECT TYPES and is simply not wired into check." A capability that exists, is configured, and is never invoked is the cheapest possible gate to add.

TWO PARTS, per the consumer's own rule text:

PART A -- STALENESS CHECK. Make npm run types a check-mode step (--check, exactly like licenses:check and static-assets:check already are in this consumer's own package.json) that fails when the generated TS-interface file is stale against backend/openapi.json. VERIFIED this is the SAME MECHANISM as T-3991 (GEN001: declared-generated-files block plus drift gate, already filed under T-3984) -- do not build a second staleness-check mechanism; this is GEN001's first concrete worked instance (generator: npm run types --check, source: backend/openapi.json, output: the generated TS interfaces file). Cross-reference T-3991 and feed this as GEN001's proof-of-concept case rather than reimplementing generically here.

PART B -- BANNED HAND-WRITTEN RESPONSE INTERFACES. A lint rule banning hand-written response interfaces in src/api/** (a TS interface/type literal manually declaring an API response shape, competing with the generated one). This is NOT covered by GEN001/T-3991 -- it is a distinct structural rule (a hand-authored type declaration in a directory reserved for generated/API-boundary code) with no staleness component. Verified via T-3991's own scope: it is about generator/output drift, not about banning hand-authored duplicates in a reserved directory.

ALSO CLOSES L-3 (fictional/leaky types): the consumer's own audit notes L-3 ("fictional... types") is covered by this same generated-types rule -- do not file it separately.
