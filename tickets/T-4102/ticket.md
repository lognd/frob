---
id: T-4102
title: two T-3947/T-3948 Windows fixtures assert a false premise (fnmatch normcases
  the glob too), and is_excluded's matching is platform-dependent
state: in-progress
kind: bug
origin: agent
created: '2026-09-06'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/excludes.py
- tests/unit/gates/test_ffi_boundary_path_shape.py
- tests/unit/gates/test_exhaustive_handling_path_shape.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a repo with [graph] exclude = vendor/**, when is_excluded is called
    with the POSIX rel vendor/sub/mod.py, then it returns True on every platform
  evidence: []
- text: given a glob and a path differing only in letter case, when is_excluded is
    called, then it returns False on every platform (no normcase dependence)
  evidence: []
- text: given the two test_windows_shaped_rel_path_mechanism fixtures, when the Windows
    CI leg runs, then neither fails
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
TWO FIXTURES ASSERT A PLATFORM BEHAVIOUR THAT WINDOWS DOES NOT HAVE, AND THEY
FAIL ON REAL WINDOWS. Measured in the third complete Windows CI run on
cc3dae236 (19 failures; these are two of them, and have failed in every
complete run so far):

    tests/unit/gates/test_ffi_boundary_path_shape.py
        ::test_windows_shaped_rel_path_mechanism
    tests/unit/gates/test_exhaustive_handling_path_shape.py
        ::test_windows_shaped_rel_path_mechanism

Both assert, of a backslash-joined relative path:

    assert is_excluded("vendor\\sub\\mod.py", ("vendor/**",)) is False

THE PREMISE IS FALSE. `frob.excludes.is_excluded` (excludes.py:83) matches with
`fnmatch.fnmatch`, and fnmatch runs BOTH the path AND the glob through
`os.path.normcase`. On Windows normcase turns the glob's forward slashes into
backslashes, so `vendor/**` becomes `vendor\**` and the backslash path MATCHES.
The function returns True. The fixtures assert False, so they fail -- on the one
platform they were written to describe.

THIS IS MY ERROR, NOT A NEW DEFECT, and the lesson is the reason to write it
down: T-3947 and T-3948 both proved their "Windows mechanism" with
`PureWindowsPath` on Linux. `PureWindowsPath` simulates Windows PATH SHAPES. It
does not simulate the Windows STDLIB -- `os.path.normcase` is still the posix
identity function under a Linux interpreter. SIMULATING A PLATFORM'S PATHS DOES
NOT SIMULATE ITS STDLIB, and any fixture that reasons about platform-conditional
library behaviour is unproven until it runs on that platform.

The PRODUCTION fixes on T-3947/T-3948 (`.as_posix()` at the producer) remain
correct and should NOT be reverted: emitting a POSIX rel is right regardless of
whether fnmatch would have accidentally matched. Only the third fixture in each
file is wrong. The first two in each file are platform-independent and pass.

THERE IS A REAL LATENT DEFECT UNDERNEATH, and it is the reason this is a bug
ticket rather than a test-only cleanup. `is_excluded`'s matching is PLATFORM
DEPENDENT: the same rel path and the same glob can produce different answers on
Windows and Linux, because fnmatch normcases both operands. Today that accident
happens to hide the path-shape bug; it can just as easily produce a
case-insensitive match on Windows that a Linux run rejects. `[graph].exclude` is
a repo's declaration of what is not its code -- it must mean the same thing
everywhere.

T-4013 ALREADY SOLVED THIS EXACT PROBLEM ONE MODULE OVER: it replaced
`fnmatch.fnmatch` in `src/frob/policy/__init__.py:40` with pathspec's
gitwildmatch, and promoted `pathspec>=0.12` to a direct runtime dependency. The
dependency is already there. Use the same mechanism here, so the two glob
surfaces cannot desync -- and check whether any OTHER module still calls
`fnmatch` against a path glob; a third copy is the same bug waiting.

WHAT TO DO
  1. Migrate `frob.excludes.is_excluded` to pathspec gitwildmatch, matching
     T-4013's approach exactly. Note excludes.py's docstring records that it is
     deliberately a near-leaf module whose only frob import is `frob.gitio` --
     pathspec is third-party, not a frob import, so that property survives.
     Preserve the documented `prefix/**` behaviour at excludes.py:126.
  2. REWRITE the two mechanism fixtures to assert what is actually true and what
     actually matters: that matching is IDENTICAL on both platforms for a
     POSIX-shaped rel, and that the producer emits a POSIX-shaped rel. Do not
     write a third fixture that predicts a Windows library's behaviour from
     Linux -- that is what produced this ticket. If a claim can only be settled
     on Windows, it belongs in an assertion that runs there, or not at all.
  3. Re-audit T-3941's `frob.xref.xref` fixture, which the docstrings name as
     the template both of these copied. If it carries the same
     `PureWindowsPath`-plus-fnmatch reasoning it has the same false premise,
     whether or not it currently fails.

MUST-FIRE FIXTURE:   a rel path under an excluded dir is excluded, given the
                     POSIX-shaped rel the producers now emit.
MUST-STAY-QUIET:     a path merely sharing a prefix with an exclude glob (the
                     `prefix/**` trailing-component rule at excludes.py:126) is
                     not excluded.
THIRD FIXTURE:       the same (rel, glob) pair returns the same answer with no
                     dependence on `os.path.normcase` -- i.e. a glob and a path
                     differing only in case do NOT match, on every platform.

ACCEPTANCE
- Both `test_windows_shaped_rel_path_mechanism` fixtures no longer assert a
  false premise; the Windows failure count drops by exactly 2.
- `is_excluded` matches via pathspec gitwildmatch, not fnmatch.
- Any remaining `fnmatch` call against a path glob is found and reported, fixed
  or ticketed.
- T-3941's sibling fixture audited, with the finding stated either way.
- All three fixtures committed.
