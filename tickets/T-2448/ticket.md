---
id: T-2448
title: Surface find_unregistered_rule_ids as a standing repo-wide frob check gate
state: done
kind: feature
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/gates/_rule_id_scan.py
- tests/gates/test_rule_id_scan_branches.py
- src/frob/gates/_sys.py
- src/frob/gates/_waive.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates/test_rule_id_scan_branches.py
  reason: test coverage for the new standing-gate wrapper lives alongside find_unregistered_rule_ids's
    own existing tests in this file
  actor: logan
  at: '2026-08-18'
- op: remove
  glob: src/frob/check/__init__.py
  reason: 'not needed: wiring point is _ALL_GATES/gates/__init__.py, not check/__init__.py,
    which needs no change'
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_sys.py
  reason: test lease availability check
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/gates/_waive.py
  reason: new _KNOWN_GATE_RULES entry for GATERULE001; dropping docs/modules/gates.md
    from this add (held by T-2437, same T-2390 epic sibling) -- doc anchor moves to
    the gate function's own frob:doc target or a follow-up
  actor: logan
  at: '2026-08-18'
evidence:
- tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_clean_repo_is_silent
- tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_unregistered_id_reported_as_error
- tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_missing_src_dir_is_unresolved_not_silent_zero
- tests/gates/test_rule_id_scan_branches.py::TestGateRuleRegistryGate::test_scan_crash_is_unresolved_not_silently_swallowed
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