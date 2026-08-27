---
id: T-3132
title: Pre-land lint gate (T-3061) attributes findings to the file, not the diff,
  same as T-1907's ty gate did
state: queued
kind: bug
origin: human
created: '2026-08-27'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/app/ticket_runner/_land_cmd.py
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
MEASURED 2026-08-27 while auditing T-3116 (ty gate diff-attribution fix).
T-3116's own ticket explicitly asked: "whether other pre-land stages
attribute by FILE rather than by DIFF. If ty does it, siblings may too."

_assert_touched_files_lint_clean_pre_land (T-3061) has the identical
shape as the pre-T-3116 _assert_touched_files_type_check_pre_land: it
runs ruff check scoped to touched .py files and refuses on ANY violation
in those files, with no comparison against the file's content at the
ticket's merge-base with main. A ruff violation that existed before this
ticket's diff -- including one whose line merely shifted -- refuses the
land exactly like the T-3116 incident did for ty.

WHAT IS WANTED: apply the same diff-attribution fix T-3116 built for the
ty gate (_ty_diagnostic_identity / _ty_baseline_diagnostic_identities:
baseline ty/ruff pass at merge-base via a detached snapshot worktree,
multiset-count comparison of (file, code, message) identity, ignoring
line/col) to _assert_touched_files_lint_clean_pre_land. The two gates
already share _touched_py_files; a ruff-specific
_ruff_baseline_diagnostic_identities mirroring the ty one, plus the same
multiset-excess comparison in _assert_touched_files_lint_clean_pre_land,
should be nearly a direct port.

ACCEPTANCE
- A land that touches a file carrying a pre-existing ruff violation,
  without introducing or worsening it, succeeds with no new suppression
  (must-stay-quiet fixture, including a line-shift case).
- A land that introduces a genuinely new ruff violation still refuses
  (must-fire fixture).
- A second genuinely-new violation sharing (file, code, message) with an
  existing pre-existing one still refuses (multiset, not set,
  comparison -- T-3116 hit this exact bug during its own implementation).