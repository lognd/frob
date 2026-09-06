---
id: T-4011
title: The Windows path-shape audit covered only relative_to() sites; gates deriving
  paths another way are unexamined
state: queued
kind: bug
origin: human
created: '2026-09-06'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/__init__.py
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
UNEXAMINED GAP, flagged honestly by the implementer that fixed the known instances rather than left implied.

THREE CONFIRMED INSTANCES of a gate silently mis-scoping on Windows have now landed: PROFILE001 (T-3941), FFI002 (T-3947) and EXHAUST001/2/3 (T-3948). All three had the same mechanism -- a relative path built with str(path.relative_to(root)), which yields BACKSLASHES on Windows, then compared against forward-slash literals or passed to helpers (frob.excludes.is_excluded / is_test_file) that require POSIX input by contract. All three are fixed by normalising at the producer with .as_posix().

THE AUDIT THAT FOUND THEM WAS BOUNDED, and the agent said so plainly:

  'the audit that found these two tickets covered only relative_to()-based path-building call sites; a gate deriving a path string some other way (e.g. via string concatenation, os.path.relpath, or a different traversal helper) reaching a forward-slash comparison was outside that audit scope and outside what I re-verified here. I did not go looking for that shape -- flagging it as unexamined, not fixing it.'

That is the correct thing to have done and the correct thing to record. The remaining question is a real one: the gate catalogue is roughly 96 gates, the audit swept 7 files and 9 sites, and it swept them by ONE syntactic pattern.

WHY THIS MATTERS MORE THAN A TIDY-UP. Every instance of this class is a SILENT ZERO -- the gate reports a clean tree while examining nothing (PROFILE001) or, worse, examines the WRONG SET (EXHAUST001/2/3 failed to honour [graph].exclude and misclassified test files as production). On Windows CI those gates were green and meaningless. Until this class is bounded, a green Windows GATE run is not evidence those gates ran, which is a live input to the owner's undecided question of whether 'fully green' must include Windows.

DO NOT SWEEP BY SYNTAX AGAIN -- that is the flaw being fixed. Two better approaches, and the second is strongly preferred:
  1. Enumerate every gate that compares a path string at all, by whatever means it obtained it, and check each for platform dependence.
  2. MAKE THE CLASS UNREPRESENTABLE. Give the codebase one helper that produces a repo-relative path, guarantee it returns posix form, and have gates take paths only from it. Then the bug cannot be reintroduced by a new gate written next month, which a one-off audit cannot promise.

STRONG CROSS-REFERENCE: T-3985 (the subject-count primitive) would have surfaced all three landed instances WITHOUT any path-shape audit at all -- a gate reporting 0 findings over 0 subjects on Windows while reporting thousands on Linux is exactly what that primitive makes visible. If T-3985 lands first, this ticket becomes a much smaller confirmation exercise. SEQUENCE THIS AFTER T-3985 unless there is a reason not to, and say so if you start it earlier.

MUST-FIRE FIXTURE: a gate deriving a path by a non-relative_to route and comparing it forward-slash is detected by whatever method this ticket adopts.
MUST-STAY-QUIET: the three already-fixed gates stay fixed.

ACCEPTANCE
- The enumeration method stated and justified (not another single-pattern grep).
- A count of gates that compare path strings, with each classified.
- A statement on whether the class is now bounded or merely sampled.