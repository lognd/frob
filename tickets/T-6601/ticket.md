---
id: T-6601
title: 'frob check prettier stage passes while CI prettier --check fails: the [warn]
  <path> lines are filtered out and unformatted files are warnings, so a nonzero prettier
  exit never fails the check'
state: queued
kind: bug
origin: agent
created: '2026-09-26'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.534.0
flavour: null
due: null
rank: null
points: 2
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
- src/frob/check/_ts.py
- tests/unit/check/
- docs/modules/check.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-26'
  old_length: 1605
  new_length: 1711
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the project-hullbreach session (2026-09-26) on its platform
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->repo: CI's `npx prettier --check .` failed on docs/backlog.md while `frob
check`'s prettier stage reported "0 files need formatting". Verified on
dev 430899e128 in src/frob/check/_ts.py::_run_prettier: prettier prints
each unformatted file as `[warn] <path>`, and the line filter
`not ln.lstrip().startswith(("[warn]", "Checking"))` discards exactly
those lines, leaving only the "Code style issues found" footer or
nothing; every surviving diagnostic is severity "warning", so even a
correctly parsed result cannot fail the gate although proc.returncode
is 1. A silent zero (the dominant bug class): the stage reports clean
when it could not read its own tool's output.

Deliver: (1) parse the path out of each `[warn] <path>` line and skip
only the "Checking formatting..." line and the "[warn] Code style
issues found ..." summary; (2) a nonzero prettier exit fails `frob
check` the way CI does (unformatted file = error, or a documented
config key to demote it, default error); (3) EOL parity: run prettier
with `--end-of-line auto` (or leave the decision to .gitattributes) so
a core.autocrlf=true working tree does not flag every CRLF file that CI
checks out as LF; (4) positive control: a fixture with one unformatted
file makes the stage report that path as an error and the check exit
nonzero; a clean fixture stays clean; a CRLF fixture under autocrlf
matches CI. Follow the silent-zero rule: when prettier's output has a
nonzero exit but no parsable rows, report one error naming the raw
output rather than zero findings.
