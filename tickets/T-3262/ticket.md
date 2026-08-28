---
id: T-3262
title: 'python-tool scaffold does not pass frob check immediately: OPAQUE001 mismatch
  + REF001 on scaffolded root files'
state: queued
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/scaffold/**
- tests/system/test_scaffold_dx.py
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
Found while root-causing T-3249's 11-failure cluster.
tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately
fails deterministically (reproduces in isolation, -p no:xdist, no
concurrency needed) on unmodified main. This is the SAME node id
T-0089/T-0122 fixed once before (a swallowed-summary log race) -- but
this is a DIFFERENT defect, confirmed by direct repro: no swallowed
summary, a full normal report with real findings.

`frob scaffold python-tool` followed immediately by `frob check
--skip-tests --skip-exports` on the freshly scaffolded, freshly
committed project fails with:

1. ONE genuine OPAQUE001 finding:
   [gate:OPAQUE] src/demo/logging/filter.py:12 OPAQUE001 ... getattr is
   a runtime-resolved capability indirection ... a non-literal attribute
   name is resolved by runtime lookup; a literal name
   (`getattr(subprocess, "run")`) is equivalent to the plain attribute
   access the ordinary resolver already handles

   NOTE: the finding's own example text names `getattr(subprocess,
   "run")`, but the actual line at src/demo/logging/filter.py:12 (the
   scaffold's own template, src/frob/scaffold/data/shared/python/
   logging/filter.py.j2) is `getattr(logging, below.upper(),
   logging.WARNING)` -- unrelated to subprocess entirely. Either
   OPAQUE001's own violation-message template is wrong/stale for this
   call shape, or the detector is citing the wrong site. Not resolved
   here -- flagging the exact mismatch as evidence.

2. Many REF001 findings on the scaffold's own generated root files
   (.env.example, .github/workflows/*.yml, .gitignore, Makefile,
   frob-coverage.lock.json, frob.toml, invariants/.gitkeep,
   scripts/bump_version.py, tests/conftest.py, tickets.md) -- the same
   "clean/scaffolded project fails REF001" shape T-3019 fixed for
   src/frob/gates/_refs.py's _DEFAULT_ROOT_MANIFEST_EXEMPT list and
   T-3249 (tickets.md) extended, but the scaffold's OWN generated
   frob.toml does not declare REF001=warn as an adoption baseline the
   way tests/system/test_cli_check.py's `_make_project` fixture does,
   and several of these files (Makefile, .github/workflows/*, .gitkeep)
   are not root-manifest-shaped at all -- a real scaffold-DX gap: a repo
   `frob scaffold`-generates for a new user should pass `frob check`
   immediately, per this test's own name.

Repro:
  uv run pytest -q -p no:xdist tests/system/test_scaffold_dx.py::test_python_tool_scaffold_passes_check_immediately

NOT a concurrency/host-load artifact -- confirmed via direct isolated
repro before any load was applied. Out of T-3249's scope (that ticket
owns the REF001 EXEMPTION-LIST class of fix already applied to
_make_project/native-missing/perf fixtures; the scaffold template
itself is a different code path -- src/frob/scaffold/data/** -- and the
OPAQUE001 finding is unrelated to REF001 entirely).
