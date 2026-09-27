---
id: T-6606
title: frob test --base selects module-level names (tests/...::_TOML) as test ids
  from the touched symbol set and exits 4 while plain pytest passes; selection must
  come only from collected pytest items
state: queued
kind: bug
origin: agent
created: '2026-09-27'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: 0.535.0
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
- src/frob/testing/_collect.py
- src/frob/testing/_select.py
- docs/modules/testing.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: DOC006 inline waivers (T-draft-7ee140de)
  actor: logan
  at: '2026-09-27'
  old_length: 1268
  new_length: 1480
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Reported by the crunk session (2026-09-26, crunk T-0211): `frob test
--base main` selected module-level constants as test ids
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->(tests/integration/test_int_02_ingest_fs.py::_TOML and
<!-- frob:waive DOC006 reason="external, illustrative or future-facing path named in this ticket body" -->tests/integration/test_int_11_jsx.py::_TOML) and exited 4, while plain
pytest on both files passes. The touched-symbol walk hands every changed
symbol in a test file to the runner as `file::name`, so a module-level
constant that changed (or that carries a frob:tests binding) becomes a
node id pytest cannot collect, and the run fails on selection rather
than on a test.

Deliver: test-id selection intersects the touched symbol set with the
items the language collector actually reports (pytest functions,
methods and parametrized ids; NUnit [Test] methods for C#), never bare
module names; a touched non-test symbol inside a test file selects the
tests of that file (a changed fixture or constant means its consumers
must run), and the run log lists the symbols it widened this way. This
is the token/grammar rule (decide from parsed symbols and collected
items, never from names). Positive control: a fixture test module with a
changed module-level constant and two tests; `frob test --base` runs
both tests and exits 0, and the selection log names the constant as
"widened to file".
