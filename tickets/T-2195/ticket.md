---
id: T-2195
title: resolve_local_import (frob.lang._nodes) does not resolve src-layout absolute
  python imports, silently degrading every consumer of _local_imports_by_path to zero
  cross-file imports
state: done
kind: bug
origin: human
created: '2026-08-16'
priority: critical
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
evidence:
- tests/unit/test_lang_primitives.py::test_resolve_local_import_src_layout_absolute
- tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_sibling
- tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_bare_dot_is_package_init
- tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_parent
- tests/unit/test_lang_primitives.py::test_resolve_local_import_third_party_still_none
- tests/unit/test_lang_primitives.py::test_resolve_local_import_scripts_fleet_status_still_resolves
- tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_top_level_layout
- tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_src_layout_too
- tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_resolves_a_nonempty_target_set
- tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_detects_a_real_violation
designated_repro_test: tests/unit/test_lang_primitives.py::test_resolve_local_import_src_layout_absolute
attachments:
- path: T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md
  caption: 'widened to CRITICAL: relative imports fail too, zero cross-file resolution
    repo-wide, T-2156 re-verification needed'
  sha256: 52c8a76d9827cda441c2e95fe3f97685dca9e7dd5405bda6ca19cdb510165dc6
- path: T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md
  caption: independently confirmed frob cycle vacuous on src-layout; widened acceptance
    criteria and fix-guidance (no src/ lexical special-case)
  sha256: cb8f524a05591cd2b69401bdf42a00cafa2a5a6be873b0678ea2d05da318c51a
- path: T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md
  caption: three confirmed vacuous consumers (attribution, cycle, arch layering);
    per-consumer must-still-pass acceptance criteria
  sha256: e1de499843567281d791d0c15f96ef5ce65d56dd2f2db7679543675311449bc4
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
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

## Done report

Changed:
- src/frob/lang/_nodes.py::resolve_local_import
- src/frob/lang/_nodes.py::_declared_python_source_roots (new)
- src/frob/lang/_nodes.py::_resolve_under (new)
- src/frob/lang/_nodes.py::_resolve_absolute_python_import (new)
- src/frob/lang/_nodes.py::_resolve_relative_python_import (new)
- docs/modules/graph.md (T-2188/BLOCKER section updated: cleared, not open)
- tests/unit/test_lang_primitives.py (6 new unit tests)
- tests/test_lang.py::TestResolveLocalImportConsumers (4 new consumer-control tests)
- tests/test_lang.py::_write (mkdir parents=True so nested fixture paths work)

Root cause (confirmed, matches ticket premise exactly): `resolve_local_
import`'s python branch only ever checked `root` itself for an absolute
specifier (`root / specifier.replace(".",  "/") + suffix`), and had no
branch at all for a leading-dot relative specifier -- it fell through to
the same absolute-style join, which can never exist under `root` for a
specifier starting with `.`. Absolute src-layout imports (`frob.tickets.
_land`) and every relative import (`._land`, `..lang._nodes`) returned
`None`.

Fix, per the ticket's explicit no-lexical-`src/`-special-case directive:
`_declared_python_source_roots` reads `root`'s own `pyproject.toml`
(`[tool.setuptools] packages.find.where` / `package-dir`, or the hatch
wheel-packages equivalent) to discover every additional source root an
absolute specifier might resolve under, falling back to bare `root` only
-- a differently-declared layout (`lib/`, a namespace package) is picked
up the same way, no code change needed. Relative specifiers resolve via
`_resolve_relative_python_import`, walking up one directory per leading
dot from the importing file's own directory (`file_dir`), matching
python's own relative-import semantics -- no pyproject.toml lookup
needed for this branch, since a relative import is always anchored at
the importer's own package position.

Evidence (pytest, `tests/test_lang.py tests/unit/test_lang_primitives.py
-o addopts="" -q`): `88 passed` (SUITE-RESULT: exitstatus=0
collected=88 failed=0), run after merging main and rebuilding natives.
10 node ids bound via `frob ticket evidence T-2195`:

- tests/unit/test_lang_primitives.py::test_resolve_local_import_src_layout_absolute
- tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_sibling
- tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_bare_dot_is_package_init
- tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_parent
- tests/unit/test_lang_primitives.py::test_resolve_local_import_third_party_still_none
- tests/unit/test_lang_primitives.py::test_resolve_local_import_scripts_fleet_status_still_resolves
- tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_top_level_layout
- tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_src_layout_too
- tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_resolves_a_nonempty_target_set
- tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_detects_a_real_violation

Repro discipline (playbook 7b): the 6 unit-level tests were committed
ALONE first (f827c996d), 4 of them observed FAILING against the
pre-fix code (`4 failed, 4 passed` -- the 4 failures are exactly the
new-capability cases; the 2 that already passed are the pre-existing
third-party/toplevel regression guards), then the fix committed
separately (b621e7752). `frob ticket evidence T-2195 --check-repro
... --base-ref f827c996d` confirms `FAILED_AT_PARENT`, designated as
the ticket's repro test.

Must-still-pass controls, all verified directly (per the ticket's own
"newly-resolving alone is not proof" requirement):
- `scripts.fleet_status` (the one absolute form that already worked)
  still resolves unchanged.
- `pytest`/`tomllib` (genuine third-party) still resolve to `None`.
- Attribution positive cross-file case: `tests/test_graph.py::
  TestBuildCallGraphVerifyImports::test_cross_file_candidate_resolves_
  when_caller_imports_it` still passes (pre-existing test, unaffected --
  it used a same-directory absolute import that already worked before
  this fix; disclosed honestly in docs/modules/graph.md rather than
  claimed as new evidence this fix produced).
- Cycle detection, BOTH layouts: `TestResolveLocalImportConsumers::
  test_cycle_detected_in_top_level_layout` and
  `test_cycle_detected_in_src_layout_too` both report the SAME planted
  2-node cycle; measured directly with the real `frob check --only
  cycle` CLI path too (not just the unit-level graph construction):
  reverting to the pre-fix `_nodes.py` and running `frob check --only
  cycle` against this repo's OWN `src/frob` tree reports "no cycles"
  (0 errors); with the fix, it reports 3 errors + 1 warning of
  genuinely real, previously-invisible cyclic-import clusters.
- Layering: `test_layering_resolves_a_nonempty_target_set` (a src-layout
  fixture's `_resolve_import_targets` returns a non-empty set) and
  `test_layering_detects_a_real_violation` (`check_layering_violations`
  flags a real disallowed cross-layer import on a src-layout fixture)
  both pass.

Addendum question answered: `_layering.py` does NOT narrow further on
top of `resolve_local_import` -- `_resolve_import_targets` and
`_resolve_reexports` both call it directly with no additional filtering,
so fixing the primitive alone was sufficient; no scope widening to
`frob.arch._layering` was needed.

**Disclosed, out-of-scope finding (filed, not silently fixed):** fixing
this primitive makes `frob check --only cycle` genuinely fail on frob's
OWN repo -- 3 errors, 1 warning, real previously-hidden cyclic-import
clusters spanning src/frob/gates, src/frob/dup, src/frob/tickets/
src/frob/app/ticket_runner/src/frob/serve/src/frob/verify, src/frob/arch,
src/frob/app, plus two smaller 2-node info-severity cycles in
src/frob/deploy and src/frob/vet. Confirmed via direct before/after
`frob check --only cycle` comparison against the identical tree (only
`_nodes.py` swapped). This is real debt this fix correctly surfaces, not
a defect in the fix -- untangling it is a separate, large body of work
well outside `src/frob/lang/_nodes.py` + tests/docs scope. Filed as
T-2202 (renumbers at land).

Filed: T-2202 (renumbers at land) -- "frob check --only cycle
now genuinely fails on frob's own repo once resolve_local_import
(T-2195) resolves src-layout imports -- real cyclic-import clusters, not
a fix defect".

Gates: `frob check --ticket T-2195` shows the repo's own already
broadly-red baseline (gate:ARCH/COV/DOC/DRIFT/PERF/PRE/SELFAUDIT/TEST/
TICK all pre-existing FAILs unrelated to this ticket's touched files,
confirmed via section 6c's scope-note: --ticket only narrows SCOPE/
PREWORK/COV002/TODO001/FMT/AFFECT, everything else reported is
repo-wide). `frob check --land-parity` could not evaluate cleanly in
this heavily-loaded multi-agent session (budget-deferred lint/static
groups, T-1703) -- reported honestly rather than treated as a pass;
land's own pre-commit/post-land sweep is the authoritative gate.
`git diff main --diff-filter=D --stat` empty after merging main (no
unintended deletions). Natives rebuilt after the main merge; scoped
tests re-run and still green (88 passed) post-merge.

### Changed
```
 docs/modules/graph.md              |  65 +++++++++++------
 src/frob/lang/_nodes.py            | 144 ++++++++++++++++++++++++++++++++++---
 tests/test_lang.py                 | 103 ++++++++++++++++++++++++++
 tests/unit/test_lang_primitives.py |  86 ++++++++++++++++++++++
 tickets/T-2195/ticket.md           |  15 +++-
 tickets/T-2202/ticket.md |  55 ++++++++++++++
 6 files changed, 434 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/unit/test_lang_primitives.py::test_resolve_local_import_src_layout_absolute` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_sibling` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_bare_dot_is_package_init` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_primitives.py::test_resolve_local_import_relative_parent` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_primitives.py::test_resolve_local_import_third_party_still_none` (pytest node id, verified passing when recorded)
- `tests/unit/test_lang_primitives.py::test_resolve_local_import_scripts_fleet_status_still_resolves` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_top_level_layout` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestResolveLocalImportConsumers::test_cycle_detected_in_src_layout_too` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_resolves_a_nonempty_target_set` (pytest node id, verified passing when recorded)
- `tests/test_lang.py::TestResolveLocalImportConsumers::test_layering_detects_a_real_violation` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 10 passed (from 10 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: @, ARCH001@src/frob/app/telemetry.py, ARCH001@src/frob/app/ticket_runner/_land_cmd.py, ARCH001@src/frob/app/ticket_runner/_new.py, ARCH103@src/frob/app/ticket_runner/_land_cmd.py, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-draft-0bd874ac/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-draft-0bd874ac/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, DOC011@docs/design/gate-semantics-classification.md, DOC011@docs/guides/coordinator-scripts.md, DRIFT001@src/frob/app/ticket_runner/_land_cmd.py, DRIFT001@src/frob/lang/_nodes.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2195/src/frob/app/ticket_runner/_land_cmd.py, E501@/home/logan/projects/frob/.claude/worktrees/t-2195/src/frob/lang/_nodes.py, PERF004@src/frob/app/ticket_runner/_land_cmd.py, PRE001@tickets/T-2195, SELFAUDIT001@design, TEST010@tests/test_lang.py, TEST010@tests/test_ticket_work_and_land_finish.py, TICK004@tickets.md
