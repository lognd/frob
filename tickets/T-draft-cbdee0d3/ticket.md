---
id: T-draft-cbdee0d3
title: 'verify: ruff-format drift (warning-only nonzero exit) classified unmeasurable,
  watermark never advances'
state: queued
kind: bug
origin: human
created: '2026-09-24'
priority: medium
parent: null
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
- src/frob/check/_python.py
- src/frob/verify/_worker.py
- tests/unit/verify/test_worker.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/check/_python.py
  reason: verify format-drift fix
  actor: logan
  at: '2026-09-24'
- op: add
  glob: src/frob/verify/_worker.py
  reason: verify format-drift fix
  actor: logan
  at: '2026-09-24'
- op: add
  glob: tests/unit/verify/test_worker.py
  reason: verify format-drift fix
  actor: logan
  at: '2026-09-24'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Measured 2026-09-24 in /home/logan/projects/crunk: `frob verify now` logs
"`frob check --json` run had 1 tool result(s) (ruff-format) that exited
nonzero with NO error-severity diagnostic explaining why -- error-finding
identities are unmeasured" and then "the verification pass produced no
parsable result -- watermark left untouched". The watermark has sat at
5e4e46ae5688 since 2026-09-06 (46 commits behind); every land there now
trips the standard-profile backpressure ceiling (depth 5) and blocks for
the full 30-minute timeout.

Root cause: `src/frob/check/_python.py::_run_ruff_format` returns
exit_code=1 with WARNING-severity "needs formatting" diagnostics, while
the T-2521 completeness check in the verify worker path only accepts an
ERROR-severity diagnostic as the explanation of a nonzero exit. A real,
fully explained result (N files would be reformatted) is therefore
classified as a crashed tool stage, and the watermark can never advance
while any queue tip has format drift -- which is exactly the case where
verification should REPORT the drift as a finding, not refuse to measure.

Fix (pick one, prefer the first): make the completeness check accept any
diagnostic (warning included) attributable to the tool as explaining its
nonzero exit; or emit the drift diagnostic at error severity when the
exit is nonzero. Positive control: a fixture repo whose tip has one
unformatted file must produce a measured verify pass with one
ruff-format finding and an advanced watermark, not Unmeasurable.
Also cover `frob check`'s own summary path so a format-only failure is
never a silent zero.
