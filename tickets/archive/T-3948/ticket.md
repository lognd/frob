---
id: T-3948
title: EXHAUST001/2/3 gate mis-scopes test/excluded files on Windows (backslash rel
  path, same class as PROFILE001)
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
body_changes:
- mode: set
  reason: 'first real Windows run shows the fixtures fail: is_excluded returns True
    on Windows because fnmatch normcases the GLOB''s forward slashes to backslashes.
    The as_posix normalisation is still right, but the claimed exclude/test-file defect
    was overstated and the fixtures encode a false premise'
  actor: logan
  at: '2026-09-06'
  old_length: 2271
  new_length: 5779
evidence:
- tests/unit/gates/test_exhaustive_handling_path_shape.py::test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production
- tests/unit/gates/test_exhaustive_handling_path_shape.py::test_rel_path_fed_to_exclude_and_test_checks_is_posix_style
- tests/unit/gates/test_exhaustive_handling_path_shape.py::test_windows_shaped_rel_path_mechanism
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