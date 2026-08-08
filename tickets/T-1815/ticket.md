---
id: T-1815
title: Re-land T-1508's z3-solver upper bound (verifies T-1814)
state: done
kind: bug
origin: human
created: '2026-08-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- pyproject.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_smt.py::test_proves_equivalent_bounded_functions
- tests/unit/test_dup_smt.py::test_finds_counterexample_for_non_equivalent_functions
designated_repro_test: null
threat: null
component: null
---
frob:waive BUG002 reason="same posture T-1508's own Done report already established for this identical defect class: the defect is an INSTALL-TIME dependency-resolution outcome (an unbounded pyproject.toml specifier resolving to a z3-solver release with no compatible aarch64/glibc-2.35 wheel), not application code a pytest node id can differ between pre-fix and post-fix -- pytest only runs inside an ALREADY-INSTALLED environment. The bound evidence (the existing z3 equivalence-probe tests) demonstrates the fix's real-world effect: z3 now actually installs and these tests exercise it for real instead of skipping, which is the strongest evidence this class of environment-provisioning fix can carry."

T-1508 is DONE/terminal on main (landed at 48e7a23ed) but that land is the
FOURTH confirmed instance of the exact hole T-1814 just fixed: the land
commit changed uv.lock (the derived fix) but left pyproject.toml's
`smt = ["z3-solver>=4.13"]` unbounded -- landed BEFORE T-1814's
field-granular reset fix reached main (verified: 2302ff25e is not an
ancestor of 48e7a23ed).

`TicketState.DONE` has zero outbound transitions in this repo's state
machine (`frob.tickets._TRANSITIONS`) -- it cannot be reopened, and
hand-editing the ledger to force it is forbidden. This mirrors the exact
precedent already recorded in this repo's own history
(`git show fdd80686a:pyproject.toml`'s comment block cites
"T-draft-1f06042b: re-landed after T-1508's own land silently dropped
this exact edit"): the sanctioned recovery here is a fresh ticket that
re-applies the dropped edit and cites T-1508, not reopening T-1508
itself.

Fix: land the bound pin

    smt = ["z3-solver>=4.13,<4.15.5"]

into pyproject.toml, with the full T-1508-authored explanatory comment
(the two glibc/wheel-availability boundaries on this fleet's aarch64
hosts) restored. uv.lock is NOT hand-edited here -- land's own
`_sync_uv_lock_for_land` re-derives it from the bumped pyproject.toml in
the same land, so the two artifacts land coherent by construction
(T-1814's fix and this land are the end-to-end proof of each other).

This ticket exists specifically to verify T-1814 (Land silently drops
non-release pyproject.toml edits) against the exact failure it was
written for.