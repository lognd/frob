---
id: T-3948
title: EXHAUST001/2/3 gate mis-scopes test/excluded files on Windows (backslash rel
  path, same class as PROFILE001)
state: queued
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