---
id: T-4381
title: rapid-profile lands skip the pre-commit sweep, so format drift on touched files
  ships unchecked
state: queued
kind: bug
origin: human
created: '2026-09-09'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/tickets/_land.py
- src/frob/tickets/_profile.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-4088 and T-4365 both landed under the rapid profile (T-1575/T-1681,
override_ratchet=true) and each left one touched file unformatted
(src/frob/perf/_rules.py, tests/system/test_cli_doctor.py respectively) --
fixed as T-4380. Root cause: rapid profile's land path deliberately skips
the T-1514 pre-commit sweep (src/frob/tickets/_land.py's own docstring:
"a supplied pre_commit_sweep ... wired only when the land profile does
NOT set override_ratchet -- i.e. every profile except rapid"), and that
sweep is the step that normally runs a full-tree frob format pass before
commit. The land's own Tier-A gate fixes do not include general
ruff-format/frob-format drift, so a rapid-profile land can silently ship
a touched file that is not `ruff format`-clean.

This is a mechanism gap, not a one-off: EVERY rapid-profile land is
exposed to it, not just these two. Needs a decision: either (a) rapid
profile should still run a scoped, touched-files-only format check/fix
(cheap, no full-tree frob check needed) before commit, or (b) land
should refuse if the touched set is not ruff-format-clean regardless of
profile, or (c) this is an accepted rapid-profile tradeoff and should be
documented as such in T-1575/T-1681's own docs. Out of scope for T-4380
(which only fixed the two already-landed files).