---
id: T-2448
title: Surface find_unregistered_rule_ids as a standing repo-wide frob check gate
state: queued
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/check/__init__.py
- src/frob/gates/_rule_id_scan.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
frob.gates._rule_id_scan.find_unregistered_rule_ids (T-1937) is a
proven, working, repo-wide completeness scanner -- it has its own
positive-control test (tests/gates/test_rule_id_scan_branches.py::
TestFindUnregisteredRuleIds.test_real_repo_registry_is_complete) and a
real production caller, but that caller
(frob.tickets._new_gate_rule_acceptance.unregistered_rule_ids_in_scope)
deliberately narrows it to ONE ticket's own declared scope at close/
land time (T-1956's own docstring: "deliberately scope-limited, not
repo-wide, so a pre-existing gap this ticket never touched can never
block an unrelated ticket's close").

That is the right call for the close/land preflight, but it leaves a
real gap: a rule id constructed in a branch NOBODY is currently
landing is invisible until something eventually tries to land it (T-
2388's PORT001 and this drive's own T-2447/CLAUDE001 finding, both
found only by manually invoking find_unregistered_rule_ids against
every live worktree by hand -- not by any standing check). This is
exactly the "detected but not surfaced" shape that let three inert CLI
flags sit unnoticed until T-2387.

Proposal: wire find_unregistered_rule_ids into `frob check` (or `frob
verify`) as a standing, repo-wide gate -- run against the CURRENT
worktree's full src/ tree (not diff-scoped), findings reported the
same fail-loudly way every other gate does. Needs a decision on
severity/blocking posture (a currently-unlanded branch's own
in-progress construction is not necessarily an error yet, so this may
want to be advisory until the offending ticket's own close/land time,
or scoped to only the CURRENT worktree's committed diff against main
rather than every uncommitted WIP). Left to whoever picks this up to
design the right invocation point; the detector itself needs no new
code, only a wiring decision.
