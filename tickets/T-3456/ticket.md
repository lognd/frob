---
id: T-3456
title: Promote T-2114 (frob:tests directive)/diff-scoped ARCH001/CrossTicketLeakage
  from land-only assertions to real frob check/close gate rules
state: queued
kind: bug
origin: human
created: '2026-08-29'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_land_parity.py
- src/frob/gates/__init__.py
- src/frob/gates/_waive.py
- docs/modules/gates.md
- tests/unit/test_land_parity_gate.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: true
no_scope_declared_reason: the too-broad glob accepted at creation collided with ~20
  other open tickets; this is a design/investigation-first ticket whose real fix location
  (a new frob.gates module vs extending _land_cmd.py/_land.py) is not yet decided
  -- see body for the concrete functions to reuse (T-3302's own investigation)
scope_changes:
- op: remove
  glob: src/frob/gates/**
  reason: the too-broad glob accepted at creation collided with ~20 other open tickets;
    this is a design/investigation-first ticket whose real fix location (a new frob.gates
    module vs extending _land_cmd.py/_land.py) is not yet decided -- see body for
    the concrete functions to reuse (T-3302's own investigation)
  actor: logan
  at: '2026-08-29'
- op: add
  glob: src/frob/gates/_land_parity.py
  reason: 'smallest-version: expose T-2114 doc/test-edge and diff-scoped ARCH001 as
    real gate rules; _land_cmd.py is leased by T-2642 (in-progress) so the shared
    pure logic is imported FROM it read-only rather than moved out of it, avoiding
    the scope-lease conflict entirely'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/__init__.py
  reason: 'smallest-version: expose T-2114 doc/test-edge and diff-scoped ARCH001 as
    real gate rules; _land_cmd.py is leased by T-2642 (in-progress) so the shared
    pure logic is imported FROM it read-only rather than moved out of it, avoiding
    the scope-lease conflict entirely'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: src/frob/gates/_waive.py
  reason: 'smallest-version: expose T-2114 doc/test-edge and diff-scoped ARCH001 as
    real gate rules; _land_cmd.py is leased by T-2642 (in-progress) so the shared
    pure logic is imported FROM it read-only rather than moved out of it, avoiding
    the scope-lease conflict entirely'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: docs/modules/gates.md
  reason: 'smallest-version: expose T-2114 doc/test-edge and diff-scoped ARCH001 as
    real gate rules; _land_cmd.py is leased by T-2642 (in-progress) so the shared
    pure logic is imported FROM it read-only rather than moved out of it, avoiding
    the scope-lease conflict entirely'
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/unit/test_land_parity_gate.py
  reason: 'smallest-version: expose T-2114 doc/test-edge and diff-scoped ARCH001 as
    real gate rules; _land_cmd.py is leased by T-2642 (in-progress) so the shared
    pure logic is imported FROM it read-only rather than moved out of it, avoiding
    the scope-lease conflict entirely'
  actor: logan
  at: '2026-08-30'
body_changes:
- mode: set
  reason: file the real check/close-wiring fix as its own properly-scoped ticket;
    T-3302 investigated and documented but could not surgically deliver this within
    _verify.py/_land_cmd.py alone
  actor: logan
  at: '2026-08-29'
  old_length: 0
  new_length: 3600
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Filed from T-3302's investigation (F-032/F-051, ../diax FROBLEMS.md).

CONFIRMED: none of these three families exists as a `frob.gates` rule
at all -- each is an ad-hoc CLI-side assertion that logs and calls
`sys.exit(1)`, never a `Violation`-producing gate function `run_gates`
dispatches. This is why `frob check --ticket`/`frob ticket close` never
see them: there is no rule for either command's gate loop to run.

WHERE THE LOGIC LIVES TODAY (reuse, do not reimplement):
- T-2114 (new public symbol missing a source-side frob:tests/frob:doc
  directive): `src/frob/app/ticket_runner/_land_cmd.py::
  _new_public_symbols_missing_doc_or_test_edge` (pure, already returns
  findings without exiting) and its caller
  `_assert_new_public_symbols_have_doc_and_test_edge_pre_land`.
- ARCH001 diff-scoped (a touched function now over the long-function
  threshold): `_land_cmd.py::_long_function_symrefs_over_threshold`
  (pure) and `_assert_diff_does_not_worsen_long_functions_pre_land`.
- CrossTicketLeakage: `src/frob/tickets/_land.py::
  _check_cross_ticket_leakage` (Result-returning, needs `root`,
  `worktree`, `ticket`, `base_ref`).

DRY-RUN ALREADY PREDICTS ALL THREE ON CURRENT MAIN (verified by reading
the call sequence, not by a live repro under time pressure -- worth a
quick real-worktree confirmation before closing this out):
- `_land_core_prepare` (`_land_cmd.py`) calls
  `_assert_new_public_symbols_have_doc_and_test_edge_pre_land` and
  `_assert_diff_does_not_worsen_long_functions_pre_land`
  UNCONDITIONALLY, before `_land`'s dry_run/real branch point -- its own
  docstring: "in dry-run and real mode alike (a dry run should preview
  the exact same landed state a real run would produce)".
- `land()`'s own top-level docstring: "`dry_run` runs every check and
  every git mutation the real run would ... then unwinds it" -- and
  `_check_cross_ticket_leakage` is called from `_land_precheck`, which
  `land()` calls unconditionally before its dry_run/real split.
So F-051's "dry-run passed, real land failed for the same reason" may
predate whichever ticket hardened this (T-1907/T-2114/T-2214 read like
exactly that hardening) -- re-measure with a real two-ticket worktree
before assuming this part still reproduces.

THE REAL FIX (why this is its own ticket, not a T-3302 patch): making
`frob check --ticket <id>` / `frob ticket close` see these findings
means either (a) a NEW frob.gates rule per family (new rule id, registry
entry, docs, waiver support -- the standard shape every other gate in
this repo has), reusing the pure functions named above, or (b) exposing
the CrossTicketLeakage check specifically requires `worktree`/`base_ref`
context `frob check` does not currently thread through generically (it
runs against a single `root`, not a worktree-vs-main comparison) --
scope that part out separately if (a) turns out infeasible for it.
`src/frob/tickets/_land.py` is a hot file (per T-3302's own coordinator
note, another series is concurrently editing it) and
`src/frob/app/ticket_runner/_land_cmd.py` carries 19 open tickets --
plan the new gate module's own scope FIRST (likely `src/frob/gates/
_land_parity.py` or similar, extracting the pure logic to a place both
`_land_cmd.py`/`_land.py` and the new gate can import from) before
claiming a broad `gates/**` glob the way this ticket's own creation
mistakenly did.

MUST-FIRE FIXTURE (from T-3302, still valid): a new public symbol added
with only a test-side `# frob:tests` binding and no source-side
directive -- `frob check --ticket` must report the SAME T-2114 finding
`land` reports today, not 0 errors.