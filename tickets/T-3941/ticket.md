---
id: T-3941
title: 'PROFILE001 silently returns zero findings on Windows: xref emits backslash
  paths, gate compares forward-slash prefixes'
state: in-progress
kind: bug
origin: human
created: '2026-09-05'
priority: critical
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/xref/__init__.py
- src/frob/gates/_profile_boundary.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: 'ticket was filed with an empty body: the heredoc writing the body file
    was blocked by a hook before it ran, so the cat substitution produced nothing'
  actor: logan
  at: '2026-09-05'
  old_length: 0
  new_length: 4085
evidence:
- tests/unit/test_xref.py::test_definition_and_usage_file_fields_are_posix_style
- tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_positive_control_reintroduced_branch_is_flagged
- tests/unit/gates/test_profile_boundary.py::TestProfileBoundaryGate::test_pre_t2361_shape_is_flagged
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
PROFILE001 CANNOT FIRE AT ALL ON WINDOWS. It returns the empty tuple
unconditionally, so on Windows CI it has been reporting "no findings" while
performing no detection whatsoever. Found by Series FP while working T-3936;
traced through the real code path, not inferred.

THE MECHANISM, end to end:

1. frob.xref.xref() at src/frob/xref/__init__.py:129 builds each usage's file
   field with:
       rel = str(path.relative_to(root))
   On Windows, Path.relative_to returns a WindowsPath, and str() of that uses
   BACKSLASHES: src\frob\app\ticket_runner\_land_cmd.py

2. profile_boundary_gate at src/frob/gates/_profile_boundary.py:139-143 then does:
       if not rel.startswith(_SRC_PREFIX):        # _SRC_PREFIX = "src/frob/"
           continue
       if rel in _PROFILE_BOUNDARY_ALLOWED_FILES: # also forward-slash literals
           continue

   On Windows rel never starts with "src/frob/", so EVERY usage is discarded
   before the allowlist check is even reached, and the gate returns () no matter
   what the tree contains.

WHY THIS IS SEVERE BEYOND THE ONE RULE. PROFILE001 is the closing regression
gate for the T-1696/T-2360/T-2361 profile-collapse epic. Its entire job is to
stop that shape coming back. On Windows it has been dead, and a dead gate is
indistinguishable in CI output from a clean tree -- the silent-zero class, in
its most expensive form: a rule whose whole purpose is regression prevention,
reporting success while measuring nothing.

THE POSITIVE CONTROLS DID THEIR JOB. test_positive_control_reintroduced_branch_is_flagged
and test_pre_t2361_shape_is_flagged were the ONLY reason this surfaced. They
were initially triaged as two more Windows test failures; they were in fact the
detector correctly reporting its own death. This is the strongest vindication
yet of the standing rule that a detector without a positive control proves
nothing -- record it as such.

THE FIX, AND THE ARGUMENT FOR WHICH ONE. Two candidates:
  (a) normalise at the xref() boundary, e.g. path.relative_to(root).as_posix();
  (b) normalise the two comparison literals in _profile_boundary.py.
PREFER (a). The defect is that xref() emits a platform-dependent string into a
field every consumer then compares against forward-slash literals; fixing the
one consumer that noticed leaves the trap armed for the next. Fixing it at the
producer makes the field contract "always posix-style" and makes that checkable.
If you choose (b) instead, you must state why (a) is unsafe.

THE AUDIT IS THE REAL DELIVERABLE, NOT THE ONE-LINE FIX. FP checked xref()'s
direct consumers under src/frob/gates/ and found only _prework.py besides
_profile_boundary.py, and did NOT exhaustively audit every gate -- their words,
correctly flagged as incomplete. So:
  - Enumerate EVERY consumer of xref() and of any other API that emits a
    str()-of-Path, and check each for forward-slash comparison.
  - Then ask the wider question this finding forces: HOW MANY OTHER GATES
    SILENTLY RETURN ZERO ON WINDOWS? Any gate comparing path strings is
    suspect. Until that is answered, a green Windows gate run cannot be read as
    evidence that those gates ran. That bears directly on the open decision of
    whether "fully green" includes Windows, so report the count even if the fix
    for each is separate.

MUST-FIRE FIXTURE: the two existing positive controls pass on Windows -- i.e.
PROFILE001 flags a reintroduced branch there. They already exist and already
fail correctly; do NOT rewrite them to accommodate the bug.
MUST-STAY-QUIET: a clean tree still reports nothing on both platforms.
THIRD FIXTURE: a path-shape test asserting xref()'s file field is posix-style
regardless of platform -- the contract, made checkable, so this cannot silently
regress.

ACCEPTANCE
- PROFILE001 fires on Windows, proven by the existing positive controls.
- The fix is at the producer unless a stated reason rules it out.
- Every xref() consumer audited for the same comparison, result stated per site.
- A count (with method) of how many other gates are at risk of the same
  silent-zero on Windows.
