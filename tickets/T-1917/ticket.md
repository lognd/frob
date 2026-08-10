---
id: T-1917
title: 'post-land sweep regression from T-1910: 1 new error(s) (TICK002)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- tickets.md
- src/frob/gates/_tickets_gate.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_tickets_gate.py
  reason: 'T-1917: TICK002 must exempt a dropped-and-archived draft (residue, never
    live/referenced going forward) while still firing on a promoted-but-never-renumbered
    (done) draft'
  actor: logan
  at: '2026-08-09'
- op: add
  glob: tests/test_gates.py
  reason: 'T-1917: TICK002 must exempt a dropped-and-archived draft (residue, never
    live/referenced going forward) while still firing on a promoted-but-never-renumbered
    (done) draft'
  actor: logan
  at: '2026-08-09'
evidence:
- tests/test_gates.py::TestFixEngineTierA::test_tick002_dropped_draft_is_exempt
- tests/test_gates.py::TestFixEngineTierA::test_tick002_done_draft_still_fires
designated_repro_test: null
acceptance:
- text: TICK002 exempts a dropped-and-archived draft (residue with no live state to
    renumber out of) while still firing on a draft that reached done without ever
    being renumbered
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_dropped_draft_is_exempt
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_done_draft_still_fires
- text: uv run frob check --only tickets on main's HEAD (or an equivalent on-main
    measurement) reports 0 TICK002 findings after the fix lands
  evidence:
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_dropped_draft_is_exempt
  - tests/test_gates.py::TestFixEngineTierA::test_tick002_done_draft_still_fires
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1910 at commit 5b0ca91f20f7f81c0d30aaa6a096ab3edf01dc7f found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- TICK002  tickets.md

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- TICK002  tickets.md  -> UNATTRIBUTED (no batch commit's touched symbols reach this finding); candidate commits: []

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

## Done report

Verified the coordinator's measurement directly rather than re-deriving
it: `uv run frob check --only tickets` against this REPO'S ROOT checkout
(on real `main`, not a worktree branch -- `_tick002_draft_on_default` is
gated on `on_default_branch(root)`, so running this same check inside a
feature-branch worktree silently reports 0 TICK002 findings regardless of
the underlying state; confirmed the false-negative directly by calling
`on_default_branch` in this worktree and getting False) reproduces
exactly the reported finding: `TICK002: draft id T-draft-d718d443
survived onto the default branch`.

Confirmed the shape via direct inspection, not assumption:
- tickets/archive/T-draft-d718d443/ticket.md front matter: state: dropped.
- `git log` on that path shows exactly ONE commit touching it
  (5b0ca91f2, landing T-1910) -- it was born already inside
  tickets/archive/, never live anywhere in this repo's history. There was
  no promotion window in which `frob ticket renumber`/`promote` could
  have run; the draft was filed, dropped, and archived in one atomic
  commit.
- `load_queue()` (T-0929, active+archive merged) is what `frob check`
  actually threads through as `st.queue` -- confirmed `T-draft-d718d443`
  IS present in that merged queue, so `_tick002_draft_on_default`'s
  `for tid in sorted(queue.tickets)` sees it and fires (once on-default-
  branch is true).

Decision: TICK002 should NOT flag a DROPPED draft, and should keep
flagging every other state (including DONE). Reasoning:

- TICK002 exists to prevent a draft id from being treated as a real,
  referenceable id while anything could still act on it as if it were
  permanent (the "collision-proofing" the module docstring names). A
  DROPPED ticket is terminal by construction -- the ledger's own state
  machine, same as any other dropped ticket, real id or draft -- nothing
  downstream ever treats a dropped ticket as live or references it going
  forward.
- The alternative (renumber a draft to a real id before archiving it,
  even when it was dropped) spends a permanent sequential id on a ticket
  that was never going to be promoted, purely to satisfy a naming rule
  with no ongoing collision risk to prevent. That is a worse trade, not a
  neutral one -- ids are meant to be stable identifiers for real
  decisions, and this repo's `renumber`/`promote` machinery already
  carries real hazards (renumber-no-args incident, promote's content-loss
  guard) that a routine "renumber-then-immediately-drop" call would
  exercise for zero benefit.
- A DONE draft is different in kind: reaching `done` without ever being
  renumbered IS the real promotion-failure this rule exists to catch (the
  Done report and evidence trail need a real id to be citable/durable
  history), so that state must keep firing. Verified with a dedicated
  test (`test_tick002_done_draft_still_fires`) that the DROPPED-only
  exemption does not accidentally widen to swallow this case.

Fix: `_tick002_draft_on_default` (src/frob/gates/_tickets_gate.py) now
additionally requires `queue.tickets[tid].state is not
TicketState.DROPPED` before emitting a finding for a given draft id.

Fail-then-pass proof: `tests/test_gates.py::TestFixEngineTierA::
test_tick002_dropped_draft_is_exempt` (synthetic repo, one DROPPED draft
on `main`, calls the real `tickets_gate(root, queue)`) FAILS against the
pre-fix `_tickets_gate.py` (confirmed directly: swapped in `git show
main:src/frob/gates/_tickets_gate.py`, ran the test, got a real
`AssertionError`-driven failure, then restored the fixed file) and PASSES
with the fix. Its sibling `test_tick002_done_draft_still_fires` (same
shape, state=DONE) passes with the fix and guards against the exemption
over-widening.

Both new tests plus the three pre-existing TICK002 tests in the same
file (`test_tick002_renumbers_draft_and_reverifies_clean`,
`test_tick002_off_default_branch_is_a_no_op`, and the acceptance-shaped
TICK002 test at line ~10914) still pass -- ran `-k tick002` (4 collected,
0 failed) and `-k "TICK or Tickets or tickets_gate"` (88 collected, 0
failed) in this worktree.

### Changed
```
 tickets/T-1916/done-report.md | 110 ++++++++++++++++++++++++++++++++++++++++++
 tickets/T-1916/ticket.md      |  66 ++++++++++++++++++++++++-
 tickets/T-1917/ticket.md      |  32 +++++++++++-
 3 files changed, 206 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/test_gates.py::TestFixEngineTierA::test_tick002_dropped_draft_is_exempt` (pytest node id, verified passing when recorded)
- `tests/test_gates.py::TestFixEngineTierA::test_tick002_done_draft_still_fires` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 8 error(s), 1498 warning(s), 696 waived
- error-findings: COV003@tickets/T-1872, COV003@tickets/T-1895, COV003@tickets/T-1896, COV003@tickets/T-1900, COV003@tickets/T-1906, F401@/home/logan/projects/frob/.claude/worktrees/reg-enforce/src/frob/gates/_fix_engine_sync.py, PARSE001@tests/unit/gates/test_sys_interface_canonical_order.py, PRE001@tickets/T-1917
