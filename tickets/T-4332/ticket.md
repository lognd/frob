---
id: T-4332
title: Survey hand-maintained membership lists for derivable-from-usage replacements
state: queued
kind: docs
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- tests/conftest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: remove
  glob: docs/
  reason: research/survey ticket scoped narrowly to its own found-while-working anchor;
    the actual audit work is scope-defined by whatever tickets it spawns, not this
    filing ticket
  actor: logan
  at: '2026-09-08'
- op: add
  glob: tests/conftest.py
  reason: research/survey ticket scoped narrowly to its own found-while-working anchor;
    the actual audit work is scope-defined by whatever tickets it spawns, not this
    filing ticket
  actor: logan
  at: '2026-09-08'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
found while working T-4329.

T-4329 fixed one instance of a recurring defect shape: tests/conftest.py's
_SELF_SCAN_HEAVY_NAME_SUBSTRINGS required a test's NAME to be added by hand to
join the frob_self_scan_heavy xdist group, and three real consumers of the
shared frob_self_scan_artifacts fixture were missing from it -- causing two
concurrent full-repo scans that OOM-killed a Windows CI runner. The fix there
(T-4329) added fixture-use detection (item.fixturenames) alongside the
existing substring list, so a new test that merely requests the shared fixture
joins the group automatically with no conftest edit -- the omission is now
unrepresentable for that specific case, not merely covered by a test.

This is the SECOND time this exact shape (T-1433 first) has caused a real
incident from the same file. The user flagged, while filing T-4329, that this
is the same shape as at least two other defect classes seen in this repo:
a gate registered but never added to its stage group, and a waiver naming a
ticket that has since closed -- all three are 'membership in list A implies
membership in list B, enforced only by someone remembering to edit both.'

Not built here because it is a repo-wide audit (find every hand-maintained
membership list with a derivable-from-usage alternative: stage-group
registration, waiver-ticket liveness, and likely others not yet found) rather
than a single-file fix -- T-4329's own scope is tests/conftest.py only, and a
survey plus fixes across gates/tickets/waive machinery is a materially larger
unit of work than this ticket's fix. Recommend an exhaustive-research pass
over src/frob/gates/ and src/frob/tickets/ for this pattern, then one ticket
per confirmed instance.