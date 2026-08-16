---
id: T-draft-0bd874ac
title: resolve_local_import (frob.lang._nodes) does not resolve src-layout absolute
  python imports, silently degrading every consumer of _local_imports_by_path to zero
  cross-file imports
state: queued
kind: bug
origin: human
created: '2026-08-16'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/lang/_nodes.py
- tests/test_lang.py
- docs/modules/graph.md
- tests/unit/test_lang_primitives.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
scope_changes:
- op: add
  glob: docs/modules/graph.md
  reason: close scope-closure warnings for the docstring/test targets the flagged
    symbols already declare
  actor: logan
  at: '2026-08-16'
- op: add
  glob: tests/unit/test_lang_primitives.py
  reason: close scope-closure warnings for the docstring/test targets the flagged
    symbols already declare
  actor: logan
  at: '2026-08-16'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
---
T-2188 finding. `resolve_local_import` (src/frob/lang/_nodes.py:59) resolves
a python absolute-import specifier (`frob.gates._dead_symbols`) purely as
`root / specifier.replace(".", "/") + ".py"` -- i.e. it assumes `root` IS
the importable package root. This repo (and any other src-layout repo)
has its importable root at `root/src`, not `root` -- `frob.gates._dead_
symbols` really lives at `root/src/frob/gates/_dead_symbols.py`, which
`resolve_local_import` never checks, so it returns `None` for every
absolute intra-package import in this entire repo.

Confirmed directly:

    from frob.lang import extract_imports, resolve_local_import
    specs = extract_imports(root / "src/frob/gates/_dead_symbols.py")
    resolve_local_import("frob.gates._models", "python", file_dir=..., root=root)
    # -> None (should resolve to src/frob/gates/_models.py)

Impact: `frob.graph.callgraph._local_imports_by_path` (T-2156's own
substrate, `build_reference_graph_module_scoped`'s cross-file check, and
T-2188's newly-shared `verify_imports=True` path in `build_call_graph`/
`build_reference_graph`/`build_ordered_call_graph`) silently degrades to
an EMPTY import set for every python file in a src-layout repo whose
imports are absolute (`from frob.x import y`, the dominant style in this
codebase) rather than relative. T-2156's own attribution consumer never
surfaced this because it is scoped to small commit diffs where an empty
cross-file import set rarely changes the attributed outcome; T-2188
surfaced it at package scale: DEAD001 30->622 findings-worth of blast
radius when `verify_imports=True` became the default for `build_call_
graph`/`build_reference_graph` (see T-2188's own Done report for the
full before/after).

WANTED: `resolve_local_import`'s python branch needs to try candidate
"source roots" beyond bare `root` -- at minimum `root` and `root/src`
(the two-root convention `pyproject.toml`'s own `[tool.setuptools]`/
`[tool.hatch.build]` package-dir declares, or infer from where `__init__
.py`/the top package directory is actually found under `root`), not just
`root` itself. Consider whether `frob.lang.extract_imports`'s own
callers already have a "project root(s)" concept to reuse rather than
hardcoding `src/` as a second guess.

Blocks T-2188: `verify_imports=True` cannot safely become build_call_
graph/build_reference_graph's default behavior on this repo (or any
other src-layout repo) until this resolves -- every python cross-file
edge silently vanishes, which is a MUCH larger false-positive/false-
negative blast radius than the bare-short-name-collision defect T-2188
set out to fix.
