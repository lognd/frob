---
id: T-1945
title: Bulk-reformat the 77 ruff-format + 265 frob-fmt drifted files (deferred from
  T-1928)
state: queued
kind: feature
origin: human
created: '2026-08-09'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- '**/*.py'
- tests/unit/strata/litmus/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-1928 measured, on a clean main tree (2026-08-10), three genuinely
different things all named "fmt" that answer different questions:

- `frob check --only fmt` (gate:FMT / FMT001): diff-scoped by
  construction (`fmt_gate`, src/frob/gates/_todo_fmt.py, only inspects
  `frob:` directive-comment lines the CURRENT DIFF touches). On a clean
  tree this is correctly 0 errors in ~0s -- it did no work because there
  was no diff to examine, not because the repo is formatted.
- `ruff format --check .` (the "ruff-format" tool inside `frob check`'s
  unscoped lint stage, src/frob/check/_python.py::_ruff_format_result):
  77 .py files with real ruff code-style drift, repo-wide.
- `frob fmt --check` (standalone CLI, src/frob/app/fmt_runner.py): 265
  files (215 .py + 49 .strata) needing `frob:` directive-comment
  line-wrap canonicalization, repo-wide -- a DIFFERENT concern from ruff
  code style. Overlap between the two .py lists is only 7 files out of
  215/77 -- these are almost entirely disjoint drift populations, not
  the same drift measured two ways.

T-1928's explicit non-goal was "do not open with a mass reformat" (a
265+77-file reformat commit is unreviewable and collides with every live
worktree). Per T-1928's acceptance [4], recording that decision here
explicitly rather than leaving it implicit in a passing gate:

DECISION (2026-08-10): the 77-file ruff-format drift and the 265-file
frob-fmt drift are ACCEPTED, KNOWN, UNACTIONED debt for now. Neither is
silently "fixed" by T-1928 (which only adds disclosure, per its own
non-goal). This ticket tracks the actual bulk-reformat work, to be
sequenced separately, deliberately, when the live `.claude/worktrees/*`
count is low enough that a large mechanical diff will not collide with
concurrent agents' in-flight work. Suggested shape when picked up: two
separate commits (ruff-format's 77 files; frob-fmt's 265 files), not one
combined diff, since they are different tools fixing different concerns
and either could regress independently.
