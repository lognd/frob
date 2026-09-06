---
id: T-3947
title: FFI002 gate mis-scopes test/excluded files on Windows (backslash rel path,
  same class as PROFILE001)
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
- src/frob/gates/_ffi_boundary.py
- tests/gates_suite/test_compliance.py
- src/frob/gates/_exhaustive_handling.py
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