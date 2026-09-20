---
id: T-4760
title: 'Derived wrappers: scaffold apply regenerates Makefile and make.bat as managed
  blocks of run calls, plus a drift gate'
state: in-progress
kind: feature
origin: human
created: '2026-09-19'
priority: high
parent: T-4757
tier: ticket
sprint: v1.1.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/_managed.py
- src/frob/gates/_wrapper_drift.py
- src/frob/scaffold/data/shared/cpp/Makefile.j2
- src/frob/scaffold/data/shared/python/Makefile.j2
- src/frob/scaffold/data/types/pybind11-library/Makefile.j2
- src/frob/scaffold/data/types/pyo3-library/Makefile.j2
- src/frob/scaffold/data/types/web-app/Makefile.j2
- docs/commands/scaffold.md
- tests/unit/test_wrapper_drift.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/scaffold/project.py
  reason: make.bat is a new derived wrapper file; its manifest entry per type lives
    in project.py's render manifest, required by the ticket's own acceptance criteria
  actor: logan
  at: '2026-09-19'
- op: remove
  glob: src/frob/scaffold/project.py
  reason: never touched; earlier scope-add attempt landed after a retry once ticket
    work had already moved on without needing it
  actor: logan
  at: '2026-09-19'
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.533.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
- field: sprint
  old_value: v0.533.0
  new_value: v1.1.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/unit/test_wrapper_drift.py::TestWrapperDriftGate::test_inline_sequence_in_target_body_is_wrap001
- tests/unit/test_wrapper_drift.py::TestWrapperDriftGate::test_target_for_removed_commands_entry_is_wrap002
- tests/unit/test_wrapper_drift.py::TestApplyGeneratesWrapperBlocks::test_second_apply_is_byte_identical
- tests/unit/test_wrapper_drift.py::TestApplyGeneratesWrapperBlocks::test_makefile_and_makebat_target_sets_are_equal
designated_repro_test: null
acceptance:
- text: Given a rendered project whose Makefile target body expands two steps inline,
    when frob check runs, then the drift gate reports it and names the target
  evidence:
  - tests/unit/test_wrapper_drift.py::TestWrapperDriftGate::test_inline_sequence_in_target_body_is_wrap001
- text: Given a Makefile target for an entry removed from [commands], when frob check
    runs, then it is reported
  evidence:
  - tests/unit/test_wrapper_drift.py::TestWrapperDriftGate::test_target_for_removed_commands_entry_is_wrap002
- text: Given scaffold apply run twice, when the second run completes, then the wrapper
    files are byte-identical to after the first
  evidence:
  - tests/unit/test_wrapper_drift.py::TestApplyGeneratesWrapperBlocks::test_second_apply_is_byte_identical
- text: Given a rendered project, when the generated Makefile and make.bat target
    sets are compared, then they are equal
  evidence:
  - tests/unit/test_wrapper_drift.py::TestApplyGeneratesWrapperBlocks::test_makefile_and_makebat_target_sets_are_equal
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Consequence of the [commands] leaf: wrappers become generated artefacts.

A planned scaffold apply regenerates Makefile and make.bat as managed
blocks, every target a one-line call to the run verb with an entry name.
Bootstrap (uv sync, cmake configure, npm ci) is the ONLY hand-written
target and stays outside the managed block. make.bat is new: today no type
ships a Windows wrapper at all, so a Windows consumer has no wrapper
surface.

Delete the authored make surface this replaces: shared/cpp/Makefile.j2 (76
lines, 12 targets including a 15-line publish target that re-implements the
version bump and the commit-message rule in shell), the pybind11 Makefile
(whose develop target runs a raw pip install, forbidden by refs/python.md,
and whose build target runs a pip subcommand that does not exist), the pyo3
Makefile (10 targets, including a back-to-back stamp-coverage then check
pair that is exactly the PRE001/SCOPE001 trap the scaffold docs warn
about), and the web-app Makefile (9 targets, taught to the user on page one
of its README).

Fix the two measured defects in the existing managed-block shim while here:
the Makefile core shim requires a STAMP variable that the cpp and web-app
Makefiles never define, so it expands to an empty prerequisite and invokes a
native build in a project that has no venv; and no template emits the
BEGIN/END markers, so the first apply on a fresh project APPENDS a second
copy of content already present (measured: 10 duplicated .gitignore entries
on a rendered cpp-library).

Add a drift gate: frob check fails when a wrapper target and the [commands]
table disagree -- a target that does not exist as an entry, an entry with no
target, or a target that expands steps inline instead of calling the run
verb by name.

Positive controls:
1. a rendered project whose Makefile target body is hand-edited to expand
   two steps inline is reported by the drift gate, with the target named;
2. a Makefile target for an entry that was removed from [commands] is
   reported;
3. applying twice is a no-op the second time (digest compare), asserted on
   file bytes, not on the report string;
4. the generated make.bat and Makefile expose the same target set, asserted
   as a set equality.

## Unblock log
- 2026-09-19: unblocked by T-4759 -- T-4759 READY and queued; wave-2 builds on branch t-4759; land order only
