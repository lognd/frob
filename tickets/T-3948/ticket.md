---
id: T-3948
title: EXHAUST001/2/3 gate mis-scopes test/excluded files on Windows (backslash rel
  path, same class as PROFILE001)
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_exhaustive_handling.py
- tests/unit/gates/test_exhaustive_handling_path_shape.py
scope_breadth_ack: true
scope_breadth_ack_reason: docs/modules/gates.md is a single shared reference doc describing
  ~40 gates; this ticket's edit is a narrow, additive scope note under the EXHAUST001/002/003
  section only (T-3948's own path-shape fix) and does not touch or invalidate any
  other gate's described section, so full scope closure over every other gate file
  that doc happens to also describe is not warranted
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/gates_suite/test_compliance.py
  reason: T-3947/T-3948 worked as one series in one worktree (identical bug class,
    sibling gate files) -- shared test file (test_compliance.py) and doc (gates.md)
    touched by both, plus the sibling gate source, need scope on each ticket
  actor: logan
  at: '2026-09-06'
- op: add
  glob: docs/modules/gates.md
  reason: T-3947/T-3948 worked as one series in one worktree (identical bug class,
    sibling gate files) -- shared test file (test_compliance.py) and doc (gates.md)
    touched by both, plus the sibling gate source, need scope on each ticket
  actor: logan
  at: '2026-09-06'
- op: add
  glob: src/frob/gates/_ffi_boundary.py
  reason: T-3947/T-3948 worked as one series in one worktree (identical bug class,
    sibling gate files) -- shared test file (test_compliance.py) and doc (gates.md)
    touched by both, plus the sibling gate source, need scope on each ticket
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/gates_suite/test_compliance.py
  reason: moved new fixtures to a standalone test module to avoid tests/gates_suite/test_compliance.py's
    shared-file scope-closure explosion; T-3947 owns _ffi_boundary.py in its own scope
    now that the shared gates.md/test_compliance.py touches were reverted
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: src/frob/gates/_ffi_boundary.py
  reason: moved new fixtures to a standalone test module to avoid tests/gates_suite/test_compliance.py's
    shared-file scope-closure explosion; T-3947 owns _ffi_boundary.py in its own scope
    now that the shared gates.md/test_compliance.py touches were reverted
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/gates/test_exhaustive_handling_path_shape.py
  reason: moved new fixtures to a standalone test module to avoid tests/gates_suite/test_compliance.py's
    shared-file scope-closure explosion; T-3947 owns _ffi_boundary.py in its own scope
    now that the shared gates.md/test_compliance.py touches were reverted
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: docs/modules/gates.md
  reason: reverted the gates.md doc edit -- editing that shared multi-gate reference
    file dragged in a full scope-closure requirement over hundreds of unrelated gate
    symbols (SCOPE002); the new standalone test module plus AFFECT001 waivers at the
    two changed sites cover this instead
  actor: logan
  at: '2026-09-06'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Found during T-3941's audit (same bug class as PROFILE001's Windows
silent-zero: T-3941 fixed frob.xref.xref() itself, but this site does
not use xref at all -- it has its own independent instance of the
identical mistake).

exhaustive_handling_gate (src/frob/gates/_exhaustive_handling.py, the
EXHAUST001/EXHAUST002/EXHAUST003 gate) does:

    for path in iter_files(root, suffix=".py"):
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            continue
        if is_excluded(rel, exclude_globs) or is_test_file(rel):
            continue

frob.excludes.is_excluded's own docstring: "True if rel_path
(root-relative, POSIX) matches any glob" -- it fnmatches rel against
each [graph].exclude glob, which are always written forward-slash
style. frob.excludes.is_test_file explicitly builds a PurePosixPath(path)
and checks "tests" in pure.parts[:-1] -- PurePosixPath does not treat
backslash as a separator, so a backslash-joined path collapses to ONE
part and this check can never see a "tests" directory component at all.

On Windows, str(path.relative_to(root)) is backslash-separated
(confirmed directly: PureWindowsPath('C:/repo/tests/test_x.py')
.relative_to('C:/repo') stringifies to 'tests\\test_x.py'). Consequence:

  - [graph].exclude globs are never honored by this gate on Windows
    (fnmatch never matches a backslash string against a forward-slash
    pattern).
  - Test files are misclassified as production files on Windows (the
    "tests" dir-component check silently fails), so this gate scans
    tests/** it should skip, and -- more importantly -- EXHAUST001/002/003
    could fire spuriously against test code the gate's own documented
    scope disclaims, OR (if is_excluded is relied on to skip a whole
    excluded subtree) fail to skip something it should have.

Not verified against a real Windows run. Confirmed by direct code
reading plus reproducing the string-shape difference with
PureWindowsPath locally (no Windows machine available).

## Suggested fix

`rel = path.relative_to(root).as_posix()` -- same fix T-3941 applied at
frob.xref.xref()'s equivalent site. `src/frob/gates/_ffi_boundary.py`'s
`_ffi002_violations` has the identical pattern (filed separately,
T-3941 audit).