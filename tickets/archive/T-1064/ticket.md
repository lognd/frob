---
id: T-1064
title: 'WAIVE004 false-positive: file-level/header-position waivers permanently zero-match
  despite suppressing live findings'
state: done
kind: bug
origin: human
created: '2026-07-28'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'T-1072 split moved the WAIVE00x/_match_waiver/_apply_waivers family out
    of

    gates/__init__.py into gates/_waive.py; T-1064''s fix lives entirely in the

    new module, so the scope glob is updated to follow the code.

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: docs/modules/gates.md
  reason: 'WAIVE004''s fix needs its documented known-flaky-classes list updated to

    describe the new structurally-unverifiable-rules exemption (INV006

    self-suppression, DUP001/DUP002/AFFECT001/AFFECT002 diff-scoping).

    '
  actor: logan
  at: '2026-07-28'
- op: add
  glob: tests/test_gates.py
  reason: 'New WAIVE004 unit tests live in TestTestGate in tests/test_gates.py;

    scope coverage for the enclosing class (touched by adding two methods)

    needs the file in scope, not just a per-method frob:ticket directive.

    '
  actor: logan
  at: '2026-07-28'
evidence:
- tests/test_gates.py::TestTestGate::test_waive004_exempts_a_structurally_unverifiable_rule
- tests/test_gates.py::TestTestGate::test_waive004_still_fires_for_a_non_exempt_rule_with_the_same_shape
designated_repro_test: null
threat: null
component: null
---
Found while working T-0874 (stale-waiver purge). WAIVE004's own zero-match
pre-check (`_waive004_violations` / `_match_waiver` in
src/frob/gates/__init__.py) systematically reports a FALSE zero-match for a
specific waiver shape: a standalone, module/function-header-position waiver
comment immediately preceding a chain of `frob:enforces`/`frob:tests`/other
directive lines and then the bound symbol (e.g. INV006's per-file
"first-turn-on pool" waivers at the top of ~209 source files, and three
freshly-landed T-0861 DUP001/AFFECT001 header waivers in
src/frob/gates/__init__.py and src/frob/vet/_capability_registry.py).

Empirically: `frob check --only invariant` (scoped) correctly reports these
INV006 findings as LIVE (not stale) at the exact same sites WAIVE004 (full,
unscoped run) reports as "matches 0 findings this run" for the identical
waiver. Deleting these waivers on the strength of the full-run WAIVE004
report resurfaced ~200 genuine INV006 errors; restoring them verbatim made
the errors disappear again (confirming the waivers DO correctly suppress
real findings via the real `_apply_waivers` pass) while WAIVE004's own
pre-check continues to flag them as zero-match, seemingly indefinitely, on
every full run.

Suspected root cause: `_waive004_violations` matches by
`_match_waiver(v, {rule: [edge]}) is edge`, i.e. it re-derives `edge.src`
per-violation; if the underlying finding is FILE-level (line 0, e.g.
INV006's whole-file exclusivity-claim scan) but violations_by_rule
population or edge-origin resolution disagrees with the real
`_apply_waivers` pass's own site derivation for this specific comment
shape, the two consumers can permanently disagree on the same site. This
needs an isolated repro (a minimal INV006-shaped file-level finding plus a
header waiver) and a fix or a documented is-this-really-flaky
determination -- WAIVE004's own gate:WAIVE never reaches zero while this
class exists, since these waivers are demonstrably still required.