---
id: T-draft-7c3f43ea
title: 'DSTACK001: fire the stack merge on every directive stack (threshold 2 by default)'
state: queued
kind: feature
origin: human
created: '2026-09-24'
priority: medium
parent: T-4703
tier: ticket
sprint: null
runs_last: false
milestone: v0.534.0
points: null
unsized_ack: false
unsized_ack_reason: null
tokens_in: null
tokens_out: null
tokens_cache_read: null
usage: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
worktree: null
branch: null
scope:
- src/frob/gates/_directive_stack.py
- frob.toml
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/_directive_stack.py
  reason: lower default threshold
  actor: logan
  at: '2026-09-24'
- op: add
  glob: frob.toml
  reason: make dstack_threshold=2 explicit
  actor: logan
  at: '2026-09-24'
triage_changes:
- field: parent
  old_value: null
  new_value: T-4703
  reason: 'leaf of T-4703 story: lower DSTACK001 threshold per owner decision'
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Owner decision (2026-09-24): DSTACK001 and its Tier-A merge fix (T-4713) must fire on EVERY
directive stack, i.e. any run of 2 or more consecutive same-kind directive lines above one
symbol, not only 4+. Tokens are never broken (owner decision 2 in tickets/T-4703/ticket.md
stands).

Work: change DEFAULT_STACK_THRESHOLD in src/frob/gates/_directive_stack.py from 4 to 2; make
this repo's frob.toml [gates] dstack_threshold = 2 explicit; keep the [gates] dstack_threshold
override read by src/frob/gates/__init__.py::_dstack_threshold; update docs/modules/gates.md's
DSTACK001 and fix_dstack001_merge entries (T-4713 section) and any doc stating the default of
4; add unit tests covering the 2-line stack as the positive control and a single directive line
as the MUST-STAY-QUIET control.

Measure and report in the done report: repo-wide DSTACK001 count at threshold 2 (residue size
for the Tier-A auto-fix to converge as files are touched; no repo-wide apply in this ticket).
