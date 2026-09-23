---
id: T-4737
title: 'gates stop importing the lease store: lease facts become passed-in inputs,
  ARCH104 ratchet burned to zero'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: critical
blocked_by:
- T-4663
parent: T-4656
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
- src/frob/gates/_baseline.py
- tests/unit/test_gates_no_lease_import.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'coordinator supplied T-4663''s actual measurement (why-T-4663.txt): 27
    gates->leases edges of 30 total, 1401 edges checked, ratcheted in frob-ratchet.lock.json;
    reconcile against the planner''s different-denominator git grep count'
  actor: logan
  at: '2026-09-19'
  old_length: 1307
  new_length: 3469
designated_repro_test: null
acceptance:
- text: Given the layering contract declares gates independent of ledger/leases/land,
    when this leaf closes, then the ARCH104 ratchet for gates -> leases edges reads
    ZERO and no module under src/frob/gates imports the lease store.
  evidence: []
- text: 'POSITIVE CONTROL: a test plants an import of the lease store inside a gates
    module and asserts `frob check` reports ARCH104 red. It FAILS on dev today (the
    layering checker is not wired, so the planted edge is reported by nothing -- a
    silent zero) and passes after this leaf.'
  evidence: []
- text: Given a gate that needs a lease fact, when it runs, then it receives that
    fact as an input argument computed by its caller, and the gate module itself has
    no lease import; proven by the ratchet at zero plus the gate's own unit test constructing
    it with injected lease facts.
  evidence: []
- text: Given the re-measurement, when the done report is written, then it states
    the REAL starting edge count measured by T-4663's checker, and explicitly reconciles
    it against the unverified "27" in the brief.
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
LAYERING cut-over leaf (story T-4656), owner-approved amendment 2026-09-19. ~3 points.

The layering contract T-4663 declares says gates is INDEPENDENT of the kernel. Today it is
not: gates reaches directly into the lease store and the ledger. This leaf makes the
declaration true by inverting the dependency -- gates stop IMPORTING the lease store, and
the lease facts a gate needs are PASSED IN as inputs computed by the caller.

MEASUREMENT NOTE (planner, 2026-09-19, measured on dev with git grep, not assumed): the
coordinator's brief cited "27 gates -> leases edges measured by T-4663". That number is not
what is on disk today and T-4663 has not run yet, so it is recorded here as unverified. The
counts actually measured now are:
  - 80 import lines matching frob.tickets inside src/frob/gates
  - 5 files under src/frob/gates importing _leases
    (incl. src/frob/gates/__init__.py:5877 `from frob.tickets._leases import resolve_lease`
     and src/frob/gates/_baseline.py:31 enforce_worktree_lease)
The FIRST task of this leaf is to re-measure with T-4663's own layering checker once it
exists, record the real edge count in the done report, and ratchet THAT number -- not 27 and
not a number copied from this body.

ARCH104 is the ratchet: set at the measured count, burned to zero by this leaf.


MEASUREMENT RESOLVED (planner, 2026-09-19, superseding the "unverified 27" note above).

The 27 IS measured. Agent E wired the layering checker in worktree t-4663 and ran it against
dev + t-4657 with the kernel contract landed in frob.toml: 1401 edges checked, 30 violations,
baselined into frob-ratchet.lock.json via `frob pool snapshot ARCH104` (ratcheted, NOT waived).
Evidence: scratchpad/why-T-4663.txt.

Breakdown of the 30:
  27  src/frob/gates/*.py -> src/frob/tickets/_leases.py   <- THIS TICKET's burn-down
      files: __init__.py, _debt_deprecated.py, _design_invariants.py, _docptr.py,
      _empty_diff_close.py, _fix_engine.py, _fix_engine_scope.py, _fix_engine_sync.py,
      _fix_engine_tier_b.py, _inv.py, _milestone.py, _negexist.py, _prework.py, _sys.py,
      _tickets_gate.py, _todo_fmt.py, _waive.py, _waive_audit_watermark.py,
      _waive_comments.py, _waive_lease.py, _wire.py (21 files), PLUS 3 fail-closed
      dynamic-import flags on _docblocks_shared.py / _flag_coverage.py / _refs.py, which
      count toward the 27 file-level findings but are the dynamic-import channel rather
      than a resolved static edge -- treat those 3 separately when burning down.
   3  src/frob/app/ticket_runner/_rapid_sweep.py -> src/frob/app/*  (land importing up into
      app) -- T-4660's subject matter, NOT this ticket's.
   1  src/frob/lang/_support.py -> src/frob/gates/_docblocks.py (+ a _walk_strata.py dynamic
      flag) -- lang/gates coupling, outside the kernel chain proper; left in the same
      ratchet pool.

Reconciliation with the planner's earlier count: 80 import LINES matching frob.tickets in
src/frob/gates, and 5 files matching a narrow `(from|import).*_leases` regex, is a DIFFERENT
DENOMINATOR -- raw import statements found by git grep, versus layering EDGES the checker
resolves (including dynamic-import channels and re-exports the regex misses). Both numbers
are correct about different things. The checker's 27 is the number this ticket burns down.

FIRST STEP UNCHANGED: re-measure with the LANDED checker before starting, and ratchet that
number. Do not trust either figure in this body once T-4663 is on dev.
