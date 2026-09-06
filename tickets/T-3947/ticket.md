---
id: T-3947
title: FFI002 gate mis-scopes test/excluded files on Windows (backslash rel path,
  same class as PROFILE001)
state: done
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
- src/frob/gates/_ffi_boundary.py
- tests/unit/gates/test_ffi_boundary_path_shape.py
scope_breadth_ack: true
scope_breadth_ack_reason: docs/modules/gates.md is a single shared reference doc describing
  ~40 gates; this ticket's edit is a narrow, additive scope note under the FFI001/FFI002
  section only (T-3947's own path-shape fix) and does not touch or invalidate any
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
  glob: src/frob/gates/_exhaustive_handling.py
  reason: T-3947/T-3948 worked as one series in one worktree (identical bug class,
    sibling gate files) -- shared test file (test_compliance.py) and doc (gates.md)
    touched by both, plus the sibling gate source, need scope on each ticket
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: docs/modules/gates.md
  reason: reverted the gates.md doc edit -- editing that shared multi-gate reference
    file dragged in a full scope-closure requirement over ~40 unrelated gate source
    files (SCOPE002); resolving AFFECT001 via frob:waive at the two changed sites
    instead, since this is a comment-only internal fix with no documented-behavior
    change
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: tests/gates_suite/test_compliance.py
  reason: moved new fixtures to a standalone test module to avoid tests/gates_suite/test_compliance.py's
    shared-file scope-closure explosion (SCOPE002 over dozens of unrelated gates whose
    own frob:tests directives live in that same shared file)
  actor: logan
  at: '2026-09-06'
- op: add
  glob: tests/unit/gates/test_ffi_boundary_path_shape.py
  reason: moved new fixtures to a standalone test module to avoid tests/gates_suite/test_compliance.py's
    shared-file scope-closure explosion (SCOPE002 over dozens of unrelated gates whose
    own frob:tests directives live in that same shared file)
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: src/frob/gates/_exhaustive_handling.py
  reason: T-3948 owns _exhaustive_handling.py in its own scope; T-3947 only needs
    its own gate file plus its own new standalone test module now that the shared
    test_compliance.py/gates.md touches were reverted
  actor: logan
  at: '2026-09-06'
- op: add
  glob: design/frob.strata
  reason: 'SELFAUDIT001: declare the new standalone test file''s fs.write capability
    at the testsuite node''s may clause, per existing per-ticket via-list precedent
    (T-3516/T-3531/etc in the same block)'
  actor: logan
  at: '2026-09-06'
- op: remove
  glob: design/frob.strata
  reason: reverted the frob.strata edit -- switched the new test module to import
    the already-declared tests.conftest._write helper instead of defining a local
    write, so no new fs.write via-site needs declaring (avoids a second scope-closure
    explosion, this time over the design registry's own doc/test cross-references)
  actor: logan
  at: '2026-09-06'
evidence:
- tests/unit/gates/test_ffi_boundary_path_shape.py::test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production
- tests/unit/gates/test_ffi_boundary_path_shape.py::test_rel_path_fed_to_exclude_and_test_checks_is_posix_style
- tests/unit/gates/test_ffi_boundary_path_shape.py::test_windows_shaped_rel_path_mechanism
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

Found during T-3941's audit (same bug class as PROFILE001, and the
same pattern as the sibling ticket filed for
src/frob/gates/_exhaustive_handling.py -- both were duplicated from
each other per that gate's own docstring: "test files excluded (mirrors
_exhaustive_handling's own test-file carve-out)").

_ffi002_violations (src/frob/gates/_ffi_boundary.py, FFI002) does:

    for path in iter_files(root, suffix=".py"):
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            continue
        if is_excluded(rel, exclude_globs) or is_test_file(rel):
            continue

Identical mechanism to the _exhaustive_handling.py finding: on Windows,
str(path.relative_to(root)) is backslash-separated, is_excluded expects
a forward-slash "POSIX" path to fnmatch against [graph].exclude globs,
and is_test_file builds a PurePosixPath(path) whose "tests" directory-
component check cannot see a backslash-joined path's components at
all. [graph].exclude is never honored by FFI002 on Windows, and test
files are misclassified as production files there.

Not verified against a real Windows run -- confirmed by code reading
plus reproducing the string-shape difference with PureWindowsPath
locally (no Windows machine available).

## Suggested fix

rel = path.relative_to(root).as_posix() -- same fix T-3941 applied at
frob.xref.xref()'s equivalent site, and the sibling ticket filed for
_exhaustive_handling.py's identical pattern.