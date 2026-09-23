---
id: T-4484
title: 'parsed-artifact cache keyed without parser identity: stale directive folds
  surface 10 local-only TEST010 errors that CI cannot see'
state: queued
kind: bug
origin: agent
created: '2026-09-14'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/cache.py
- src/frob/lang/__init__.py
- tests/unit/graph/test_cache_parsed_artifact_version.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.535.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
threat: null
component: graph
anchor: false
anchor_reason: null
land_commit: null
---
## Observed (2026-09-15, main 5af4128ac + 4 ledger commits)

Three consecutive local `frob check --only gates` runs reported 10 TEST010
errors ("bad attribute syntax: 'reason=\"single-line frob:tests directive
naming a long test node id ... \\'") at src/frob/graph/dsl.py:797/1147/
1152/1157/1162, src/frob/app/ticket_runner/_verify.py:2296/2301 and
tests/unit/test_verify_language_buckets.py:293/298/303. Every site is a
`frob:tests ... # noqa: E501` line followed by a backslash-continued
`frob:waive FMT001 reason="..."` block. The CI self-gate on the SAME
commit (run 34907833921, ubuntu job 104188483072) reported 0 errors.

Discriminator: parsing dsl.py directly through frob.lang.parse_file plus
frob.graph.dsl.parse_directives returned 0 malformed, both for the in-repo
path and for an uncacheable scratch copy. Only the GraphSnapshot.malformed
list the gate reads carried the records. `frob clean --deep -y` followed by
the same check: 0 errors.

## Diagnosis

The serialized ParsedFile in the graph cache is looked up by
(content_hash, fingerprint) (frob.graph.cache.load_parsed_artifact). A
directive-parser change that alters how continuation lines fold (the
T-4475/T-4480 noqa-suffixed over-limit handling is the likely one) moved
neither key, so artifacts parsed under the OLD folding kept answering for
unchanged files. A fresh CI checkout never sees them; a long-lived local
checkout does, and reports ten hard errors that no code change can clear.

This is the derived-artifact trap: the cache key must cover the parser
identity (dsl/lang module digests, or an explicit parser-version constant
bumped with every fold/attr change), or the stored payload must carry it
and be rejected on mismatch.

## Acceptance

- A test that stores a parsed artifact, changes the directive parser's
  version marker, and shows the next load MISSES (re-parses) instead of
  returning the stale payload.
- The key or payload carries the parser identity; docs/modules for the
  graph cache describe it.
