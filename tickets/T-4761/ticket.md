---
id: T-4761
title: 'Green on day one: refs regression, doc anchors, tickets/ and integration dirs,
  39 bare TODOs, and a readable rendered frob.toml'
state: queued
kind: feature
origin: human
created: '2026-09-19'
priority: high
blocked_by:
- T-4760
parent: T-4757
tier: ticket
sprint: v0.537.0
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/data/shared/python/frob.toml.j2
- src/frob/scaffold/data/shared/cpp/frob.toml.j2
- src/frob/scaffold/data/types/web-app/frob.toml.j2
- src/frob/scaffold/data/types/pyo3-library/frob.toml.j2
- src/frob/scaffold/data/types/pybind11-library/frob.toml.j2
- src/frob/scaffold/data/shared/python/docs/**
- src/frob/scaffold/data/shared/python/tests/**
- src/frob/scaffold/project.py
- docs/guides/frob-toml.md
- tests/unit/test_scaffold_frob_toml.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: sprint
  old_value: null
  new_value: v0.537.0
  reason: sprint set via `frob ticket sprint assign`
  actor: logan
  at: '2026-09-19'
designated_repro_test: null
acceptance:
- text: Given a rendered frob.toml, when its top-level tables are read in order, then
    they are project, profile, commands, testing, gates, and every table header line
    is preceded by a comment line
  evidence: []
- text: Given python-tool is rendered, when its frob.toml is measured, then it is
    under 30 lines and contains no ticket id and no refs.entrypoint row
  evidence: []
- text: Given every registered type is rendered, when the output is searched for bare
    TODO markers, then the count is zero (it is 39 today)
  evidence: []
- text: Given every frob:doc anchor a template emits, when the rendered docs are read,
    then each anchor resolves to a heading the same manifest renders
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Green on day one is now a requirement. Today every one of the 7 renderable
types is RED on a fresh frob check: 17/5/17/17/?/19/18 errors respectively
(audit section 3, each measured by git init plus commit plus frob check in
the rendered tree).

Fix, in the templates:

1. The [[refs.entrypoint]] regression. Only shared/python/frob.toml.j2
   carries the block; shared/cpp, types/web-app, types/pyo3-library and
   types/pybind11-library each forked the python file and silently dropped
   it, which alone accounts for 11-12 REF001 per non-python type. With
   T-draft-538a0625 landing conventional-file defaults in the refs gate, the
   right fix is that the rendered frob.toml needs ZERO refs rows, not four
   more copies of the block.
2. docs/index.md has no Public API heading, so the frob:doc anchors the
   logging templates emit do not resolve (5 DOC002 on python-library). Emit
   the heading the directive points at.
3. No type renders a tickets/ directory, although every type renders a
   frob.toml. Render it.
4. TEST003 fires everywhere: only tests/unit and tests/system render, so the
   integration floor of 1 is never met. Render tests/integration with a real
   test, not a placeholder.
5. 39 bare TODO markers ship into every new project, which is TODO001 in a
   frob-enabled repo on day one. Each becomes either a frob:todo pointing at
   a ticket the scaffold itself creates in the rendered tickets/ directory,
   or is deleted. The worst are in generated source, not prose: the cpp test
   is literally named after TODO.
6. The frob-exports findings (symbols defined in the logging templates and
   not exported from the package __init__).

Readability, same bar as the wrappers leaf: the rendered frob.toml is
ordered project, profile, commands, testing, gates (refs only for genuine
exceptions), every table header preceded by one plain-English comment
stating what it controls and when you would edit it, no ticket ids or change
history in comments, defaults omitted, and under 30 lines for python-tool.
No schema tables and no per-rule severities in a rendered file; severities
come from the profile.

Add docs/guides/frob-toml.md walking the rendered file top to bottom.

Also correct the scaffold docs' claim that nothing in a rendered template
needs hand-fixing to pass its own rules: that is true only of ruff, ty and
pytest, and false of frob check, which is the actual gate.

Positive controls:
1. a test asserts the rendered frob.toml's exact top-level table order and
   that every table header line is preceded by a comment line;
2. a test asserts the rendered python-tool frob.toml is under 30 lines;
3. a test asserts zero bare TODO markers across all rendered types (the
   current count is 39, so the test fails loudly before the fix);
4. a test asserts every frob:doc anchor emitted by a template resolves to a
   heading that the same manifest renders.

## Unblock log
- 2026-09-19: unblocked by T-4989 -- T-4989's own scope (src/frob/gates/_refs.py, tests/test_refs_gate.py) is leased by T-4770/T-4624, so it cannot be implemented right now either; narrowing T-4761 instead of waiting on it -- restoring refs.entrypoint parity across the 4 forked templates (matching shared/python's existing block) rather than the zero-rows ideal T-4989 would enable, and noting that gap explicitly rather than silently dropping it
