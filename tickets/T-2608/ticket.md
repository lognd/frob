---
id: T-2608
title: 'gate:SCOPE002 closure debt: narrow-scope tickets touching _gate_cache.py/_python.py
  trip 850+ pre-existing cross-file doc/test scope warnings'
state: done
kind: bug
origin: human
created: '2026-08-19'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/_python.py
- src/frob/gates/_gate_cache.py
- src/frob/gates/__init__.py
- tests/test_gates.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/gates/__init__.py
  reason: SCOPE002's implementation lives here; grouping fix requires editing it
  actor: logan
  at: '2026-08-30'
- op: add
  glob: tests/test_gates.py
  reason: new grouping-behavior test for SCOPE002's fix lives here
  actor: logan
  at: '2026-08-30'
evidence:
- tests/test_gates.py::TestScope002ClosureGate::test_groups_many_symbols_pointing_at_the_same_missing_file
- tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_doc_target
- tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_private_helper
- tests/test_gates.py::TestScope002ClosureGate::test_warns_on_unscoped_test_target
- tests/test_gates.py::TestScope002ClosureGate::test_silent_on_closed_scope
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Problem

Found while working T-2585 (whole-run replay for `frob check`), out of that
ticket's declared scope, not fixed there.

T-2585's scope is `['src/frob/check/_python.py', 'src/frob/gates/_gate_cache.py',
'docs/modules/serve.md']`. Running `uv run frob ticket scope T-2585 --add
'tests/test_gate_cache.py'` (a genuinely needed, in-scope addition -- new
tests for T-2585's own new symbols) surfaced 852 scope-closure warnings, all
PRE-EXISTING: every already-existing public symbol in `_gate_cache.py`
(`TrackedSnapshot`, `evaluate_cacheable_gate`, `invalidate`,
`load_root_gate_cache`, `root_content_key`, `store_root_gate_cache`, ...) and
in `_python.py` (`_diag_severity`, `_unresolved_count`, ...) has its
`frob:doc`/`frob:tests` target in a file NOT in T-2585's scope --
`docs/modules/gates.md` and roughly two dozen test files
(`tests/unit/test_check.py`, `tests/test_gate_cache.py` itself before being
added, `tests/system/test_cli_check.py`, several cycle-regression test
files, `src/frob/serve/*.py`, `design/frob.strata`, etc).

`gate:SCOPE`'s SCOPE002 rule enforces closure over a ticket's declared
scope: once a file is in scope, every public symbol IN it must have its
doc/test targets also in scope, or SCOPE002 fires for each one. This is
correct behavior for the rule -- the problem is structural: `_gate_cache.py`
and `_python.py` are large, heavily cross-referenced files whose existing
symbols point at `docs/modules/gates.md` and ~20 test files. ANY ticket
that scopes narrowly to just these two files (a normal, minimal scope for
a small, targeted change -- exactly what T-2585 did) will trip this same
850+-line closure warning on the very first `frob ticket scope --add` or
`frob check --ticket` call, independent of what the ticket's own diff
touches.

Confirmed pre-existing, not caused by T-2585's diff: the flagged symbols
(`TrackedSnapshot`, `evaluate_cacheable_gate`, `_diag_severity`, etc.) all
predate T-2585 -- `git show HEAD:<file>` before T-2585's edits already
defines them with the same out-of-scope doc/test targets.

## Why this matters

- A narrow, well-scoped ticket touching either of these two files cannot
  achieve a genuinely clean `frob check --ticket` without either (a)
  ballooning its own scope to `docs/modules/gates.md` plus ~20 unrelated
  test files (defeats the purpose of scoping narrowly at all), or (b)
  accepting hundreds of SCOPE002 warnings it did not cause and cannot fix
  within its own declared scope.
- `--ticket`-scoped SCOPE/PREWORK output is exactly the family playbook
  section 6c says IS meaningfully scoped to the ticket -- so an agent
  correctly trusting that scoping (per the playbook) walks straight into
  this wall for these two files specifically.

## Suggested directions (not investigated in depth -- this is a filing,
not a diagnosis)

- A "scope closure" mode that treats a file already fully covered by an
  EXISTING, unrelated ticket's historical scope as pre-closed, rather than
  re-flagging every symbol for every new ticket that touches the same
  file.
- Splitting `_gate_cache.py`/`_python.py`'s doc anchors so each symbol's
  cross-reference lives in a docs file scoped closer to it (harder, a real
  refactor).
- A scope-closure warning that distinguishes "this symbol's doc/test
  target is out of scope AND this ticket's diff touched the symbol" from
  "the symbol is untouched by this diff but happens to share a file with
  something that was touched" -- only the former seems like a genuine
  closure gap for THIS ticket's own change.

Not fixed in T-2585: fixing this is a design decision (which of the
directions above, if any) outside a bug-fix ticket's scope.