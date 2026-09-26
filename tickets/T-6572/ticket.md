---
id: T-6572
title: land --dry-run still skips the scoped ruff check the real land runs, so a dry
  run stays green on a new E501 in a touched file (T-5161 follow-up)
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
flavour: null
due: null
rank: null
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
- src/frob/app/ticket_runner/_land_cmd.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'crunk data point: dry-run and check --ticket miss T-2114'
  actor: logan
  at: '2026-09-26'
  old_length: 875
  new_length: 1624
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26) on frob 0.531.1.dev338, which
already carries T-5161 (dry-run runs the unscoped pre-land sweep): `frob
ticket land --dry-run` for crunk T-0169 reported "DRY RUN clean,
merged=True" and the real land then refused on a NEW ruff E501 in a
touched file. The scoped ruff pass the real land runs on touched files is
not part of the dry run (T-4179 keeps only the format would-rewrite
probe), so the dry run is a false green for lint.

Deliver: --dry-run runs the same scoped ruff check (read-only, same rule
selection and same touched-file set) and reports its findings alongside
the T-5161 sweep preview; the DRY RUN summary names each pre-land probe
it ran so a "clean" is auditable. Positive control: a fixture worktree
with one over-long line in a touched file; the dry run reports E501 and
the real land refuses on the same finding.


Second case (crunk-ba, 2026-09-26, crunk T-0208): `land --dry-run`
reported "DRY RUN clean -- merged=True" and `frob check --ticket` was
fully clean, then the real land refused with T-2114 "new public symbol
... has no frob:tests edge" for 3 symbols in src/crunk/tailwind_runtime/
models.py. Widen this ticket: the dry run runs EVERY pre-land guard that
does not need the merge commit (the scoped ruff pass, T-1907 ty on the
touched set, T-2114/T-5299 new-public-symbol doc/test edges, scope and
cross-ticket checks) against the staged preview, and `frob check
--ticket` surfaces T-2114 too, so a clean ticket check plus a clean dry
run implies the land will not refuse before the merge commit exists.
The DRY RUN summary lists each guard it ran.
