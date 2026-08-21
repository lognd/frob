---
id: T-draft-5b20cab8
title: 'COV007 burn-down batch 1/N: src/frob/strata/_multifile.py duplicate doc anchors'
state: in-progress
kind: bug
origin: human
created: '2026-08-21'
priority: medium
parent: T-2370
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/strata/_multifile.py
evidence_scope:
- tests/unit/strata/test_fragments.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/unit/strata/test_fragments.py::TestResolveFragments::test_widens_existing_grant
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Batch 1/N of T-2370 (Burn COV006/COV007 WARN gates to zero, then promote
to error). Batched per the T-2359/T-2373 precedent: real narrow scope per
batch, landed independently, parent stays open until every batch lands,
severity promotion (WARN -> error) deferred to the LAST batch.

Measured via one reused unbudgeted `frob check --json` (2026-08-21,
docs/investigations/T-2796-backlog-reproduction.md's own check run),
filtered to severity=warning (excluding already-waived note-level
findings, which is most of COV007's raw count -- see that investigation
doc for the split). Live count at the time of this ticket: COV006 = 2
warnings (both in tests/test_gates.py), COV007 = 44 warnings across 25
files.

This batch: src/frob/strata/_multifile.py only (7 of the 44 live COV007
warnings -- the highest-density single file). All 7 are the private
step-functions of `resolve_fragments` (_widen_node_grants,
_group_targeted_roots, _group_fragments_by_name, _resolve_unique_roots,
_seed_grants_by_root_node, _apply_fragment_extends,
_rebuild_resolved_files), each individually carrying a duplicate
`# frob:doc docs/strata/surface.md#fragments-t-2502` comment -- the SAME
anchor already carried by the public `resolve_fragments` function
directly below them (line ~421) and by `SealedGrantSet` above them.

Verified this is genuine duplication, not distinct documented behavior:
docs/strata/surface.md's "Fragments (T-2502)" section (grep-verified)
`frob:describes` only `resolve_fragments` and `SealedGrantSet` -- it does
NOT name any of these 7 private helpers individually anywhere in its
prose (unlike the vet.md "Public API" section's genuinely-deliberate
per-helper `frob:describes` pattern, which is why several other COV007
findings that pattern-match it are already correctly waived, not fixed --
see the investigation doc). Fix: remove the 7 duplicate private-symbol
`frob:doc` comments; the public entry point's own anchor already covers
the documented behavior, so no documentation coverage is lost.

Remaining batches for T-2370 (not this ticket's scope): the other 24
files carrying live COV007 warnings, plus the 2 live COV006 warnings in
tests/test_gates.py, plus the WARN->error promotion once every batch
lands. Each of those needs its own individual read (public-caller-move,
or a justified per-symbol waiver, on the vet.md precedent) before a fix
is safe to land -- not attempted here to keep this batch's verification
real rather than broad.