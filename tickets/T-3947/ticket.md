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
body_changes:
- mode: set
  reason: 'first real Windows run shows the fixtures fail: is_excluded returns True
    on Windows because fnmatch normcases the GLOB''s forward slashes to backslashes.
    The as_posix normalisation is still right, but the claimed exclude/test-file defect
    was overstated and the fixtures encode a false premise'
  actor: logan
  at: '2026-09-06'
  old_length: 1481
  new_length: 4989
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
## CORRECTION AFTER THE FIRST REAL WINDOWS RUN: THE PREMISE WAS WRONG FOR is_excluded

The two fixtures this work added FAIL ON REAL WINDOWS (run 34024645783 and the
following run, both legs):

    tests/unit/gates/test_ffi_boundary_path_shape.py::test_windows_shaped_rel_path_mechanism
    tests/unit/gates/test_exhaustive_handling_path_shape.py::test_windows_shaped_rel_path_mechanism

    assert is_excluded(pre_excl_rel, ("vendor/**",)) is False
    E  AssertionError: assert True is False
    E   +  where True = is_excluded('vendor\\sub\\mod.py', ('vendor/**',))

I VERIFIED THE MECHANISM RATHER THAN GUESSING. `is_excluded` is
`fnmatch.fnmatch`, and fnmatch applies `os.path.normcase` to BOTH the name and
the PATTERN:

    ntpath.normcase('vendor\\sub\\mod.py') -> 'vendor\\sub\\mod.py'
    ntpath.normcase('vendor/**')           -> 'vendor\\**'      => MATCHES  (True)
    posixpath.normcase('vendor/**')        -> 'vendor/**'       => no match (False)

So on Windows the FORWARD SLASHES IN THE GLOB are converted to backslashes, and a
backslash path matches a forward-slash glob correctly. The exclusion was NEVER
broken on Windows for this call, and the PureWindowsPath simulation on Linux
could not show that because it simulated the PATH while leaving fnmatch running
under posix normcase.

WHAT THIS MEANS, precisely -- and note it does NOT invalidate everything here:

  - THE `.as_posix()` NORMALISATION IS STILL CORRECT AND WORTH KEEPING. Emitting
    a platform-dependent string into a field consumers compare is a real hazard,
    and normalising at the producer removes it. Do not revert it.
  - BUT THE CLAIMED DEFECT WAS OVERSTATED FOR THESE TWO GATES. I reported that
    EXHAUST001 "fails to honour [graph].exclude and misclassifies test files as
    production on Windows". For the `is_excluded` path that is NOT TRUE --
    fnmatch's normcase compensated. Any part of the claim resting on
    `is_test_file`/`is_excluded` mis-matching needs re-checking the same way.
  - THE FIXTURES ENCODE A FALSE PREMISE and must be rewritten. They assert the
    pre-fix call returns False; on the platform they are written for it returns
    True. A fixture that only passes under simulation is worse than none.

T-3941 (PROFILE001) IS A DIFFERENT AND STILL-REAL DEFECT. That one compared with
`rel.startswith("src/frob/")` -- a plain string method with NO normcase -- so a
backslash path genuinely never matched. Do not let this correction cast doubt on
it; the mechanisms differ, and that is exactly why each needs its own real-platform
proof.

THE GENERAL LESSON, worth carrying beyond these tickets: SIMULATING A PLATFORM BY
CONSTRUCTING ITS PATH OBJECTS DOES NOT SIMULATE ITS STDLIB. PureWindowsPath gave
us Windows-shaped strings while fnmatch, os.path and every other platform-
dispatching call kept behaving as posix. Any future "verified via PureWindowsPath"
claim should be treated as a hypothesis until a real Windows run confirms it.

RELATED: T-4013 (policy globs use fnmatch, so `app/**/*.py` misses files directly
under app/) gains a second reason to move to pathspec/gitwildmatch -- fnmatch is
not merely wrong about `**`, it is PLATFORM-DEPENDENT, so the same config behaves
differently on Windows and Linux. Note that there.

ACCEPTANCE ADDITION
- The two fixtures rewritten to assert what actually happens on Windows, or
  deleted if they prove nothing.
- The exclude/test-file half of the original claim re-verified against real
  Windows behaviour rather than simulation.