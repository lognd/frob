---
id: T-3587
title: frob refactor verbs cannot address any module outside src/ -- module_to_path
  hardcodes src/ as sole root
state: in-progress
kind: feature
origin: agent
created: '2026-08-31'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/refactor/**
- tests/test_refactor.py
- docs/commands/refactor.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_refactor.py
  reason: closure requires the new frob:doc anchors and frob:tests targets landed
    in this same diff
  actor: logan
  at: '2026-08-31'
- op: add
  glob: docs/commands/refactor.md
  reason: closure requires the new frob:doc anchors and frob:tests targets landed
    in this same diff
  actor: logan
  at: '2026-08-31'
evidence:
- tests/test_refactor.py::TestModuleToPath::test_maps_module_under_src
- tests/test_refactor.py::TestModuleToPath::test_maps_module_under_root
- tests/test_refactor.py::TestImportRoots::test_src_first_then_repo_root
- tests/test_refactor.py::TestImportRoots::test_repo_root_only_when_no_src
- tests/test_refactor.py::TestRootForPath::test_finds_owning_root
- tests/test_refactor.py::TestRootForPath::test_none_when_outside_every_root
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-3586 (split tests/test_gates.py via frob refactor
verbs).

`frob refactor split`/`move`/`rename`/`move-module` cannot address any
module outside `src/`: `module_to_path` (src/frob/refactor/_resolve.py:27-33)
unconditionally does:

    src_root = repo_root / "src"
    base = src_root if src_root.is_dir() else repo_root
    return base.joinpath(*module.split(".")).with_suffix(".py")

Since this repo has an `src/` layout, `base` is ALWAYS `src/` whenever
`src/` exists, with no override. A dotted module like `tests.test_gates`
maps to `src/tests/test_gates.py`, which does not exist, so
`resolve_symbol` returns `Err(TargetNotFound)` and every split/move/
rename/move-module call against a `tests/**` module fails immediately:

    WARNING: refactor.resolve: module file missing: <repo>/src/tests/test_gates.py
    error: the move/rename target does not resolve to exactly one symbol

The same src-hardcoding is duplicated in
src/frob/refactor/_module_resolve.py:77-90 (resolve_module),
src/frob/refactor/_module_scan_python.py:90-91 (reference-scan root),
src/frob/refactor/_operands.py:173-174 (module-destination validation),
and src/frob/refactor/_verify.py:127-128,156-157 (pytest --collect-only
import root) -- five independent copies of the same "base = src if
src.is_dir() else repo_root" rule, all of which need to agree on
whatever the fix is (NO DUPLICATION applies to this decision itself:
one home for "how does a dotted module map to a path", not five).

This blocks any refactor-verb-driven split of a monofile test suite
under `tests/` in a repo that also has `src/` -- which is exactly the
shape T-3586, and its five named follow-ups (test_ticket_land.py,
tests/unit/test_arch.py, tests/test_vet.py,
tests/unit/test_coordinator_scripts.py, tests/unit/test_rapid_sweep.py)
need.

SUGGESTION: give the four resolve/scan/verify/operand-validation call
sites a shared root-selection rule that tries multiple package roots
(at minimum `src/` and the repo root itself, in that priority order) by
checking which one actually contains the FILE `module_to_path` would
produce, instead of a single always-src decision keyed only on whether
`src/` exists as a directory. Land it as one function other call sites
delegate to, not five parallel patches.

ACCEPTANCE: `frob refactor split tests.test_gates --symbols ... --into
tests.gates_suite.test_x` succeeds against this repo's actual `tests/`
tree (not a synthetic fixture repo) with `src/` present alongside it,
producing correct chunk-committed moves and a working re-export shim,
verified by a real `--collect-only` pass.
