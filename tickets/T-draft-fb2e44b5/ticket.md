---
id: T-draft-fb2e44b5
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
sprint: v0.535.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_baseline.py
- tests/unit/test_gates_no_lease_import.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
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
