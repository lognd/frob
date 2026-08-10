---
id: T-1901
title: 'post-land sweep regression from T-1892: 1 new error(s) (SYS004)'
state: done
kind: bug
origin: agent
created: '2026-08-09'
priority: high
blocked_by:
- T-1900
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- design/frob.strata
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
designated_repro_test: tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
threat: null
component: null
anchor: false
anchor_reason: null
---
The deferred post-land unscoped sweep (T-1684) for T-1892 at commit c8e50a3d878dad4f2de2634ae2ebd3b41235fbb1 found 1 error identit(ies) that were not present in the previous sweep's baseline.

New (rule, file) pairs filed here:

- SYS004  design/frob.strata

Attribution (T-1690, symbolic reachability over the verify queue's touched-symbol sets):

- SYS004  design/frob.strata  -> attributed to T-1892 (commit c8e50a3d878d, already closed/dropped -- filed below) via design/frob.strata::frob.claude_hooks

Under the rapid profile the sweep runs detached and files this ticket rather than reverting an already-published commit. Fix the errors, or -- if they are pre-existing residue the rolling baseline simply had not recorded yet -- close this ticket with that finding stated explicitly.

frob:waive BUG002 reason="the SYS004 corruption this ticket describes was already hand-repaired directly on main in e1a603603e101abb08e624517f3ba72d9c14fcda (\"fix(design): final repair of strata corruption before T-1900's fix takes effect\"), which predates this ticket being picked up and is not associated with any ticket id. The designated repro test genuinely FAILED at e1a603603's own parent (67894869e9366977fad805b0f50c2b3af493e0a2, verified via frob ticket evidence T-1901 --check-repro ... --base-ref e1a603603~1) -- a real repro exists -- but by the time this land runs, main's own tip already contains the fix, so the same test necessarily PASSES at land-time's parent too and BUG002's land-time check cannot distinguish that from confirmatory-only evidence. This is the documented ledger/doc-correction shape: no code change is landing under this ticket id, only recording that the fix (which did happen, and was verified to genuinely reproduce-then-fix) is attributed and closed out."

## Done report

Reproduced the SYS004 finding at the parent of e1a603603e101abb08e624517f3ba72d9c14fcda
(commit 67894869e9366977fad805b0f50c2b3af493e0a2): design/frob.strata's
claude_hooks/scripts_ops/testsuite nodes declared

    attr interface=[
        [],
    ];

which parses as a one-element list containing an empty list, i.e. a call
of a symbol named "[]" -- the same corruption class T-1900 already fixed
elsewhere in this file. sys_gate reports that as SYS004 (design file
load/elaborate failure) against design/frob.strata.

The fix was already applied directly to main by the owner in
e1a603603e101abb08e624517f3ba72d9c14fcda ("fix(design): final repair of
strata corruption before T-1900's fix takes effect"), which collapsed all
three malformed `attr interface=[[],];` blocks to the correct
`attr interface=[];`. That commit predates this dispatch and is already
an ancestor of HEAD; it never cited T-1901.

Verified on the current tree: `uv run frob check --only sys` reports 0
errors/0 warnings, and
tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations
(the repo-live sys_gate regression guard) passes. `frob ticket evidence
T-1901 --check-repro ... --base-ref e1a603603e101abb08e624517f3ba72d9c14fcda~1`
confirms FAILED_AT_PARENT for that same node id, so this is a real
(already-applied) repro, not confirmatory-only evidence.

No code change was needed in this ticket beyond recording the fix and
closing it out -- the corruption was hand-repaired on main before this
ticket was picked up. Per T-1870/T-1916's standing owner directive, no
automatic mutation of design/frob.strata is reintroduced here; this
report only documents a hand-edit that already happened.

### Changed
```
 tickets/T-1901/ticket.md | 4 +++-
 1 file changed, 3 insertions(+), 1 deletion(-)
```

### Evidence
- `tests/system/test_frob_self_model.py::TestFrobSelfModel::test_sys_gate_zero_violations` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 3 error(s), 941 warning(s), 696 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_close_cmd.py, DOC001@docs/design/cli-hygiene.md, SEC110@src/frob/app/ticket_runner/_new.py
