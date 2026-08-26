---
id: T-2951
title: 'PLATFORM001 gap: does not catch platform-restricted attributes evaluated at
  import/def time (default args, module/class constants, decorator kwargs)'
state: done
kind: bug
origin: human
created: '2026-08-26'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_walk_lint.py
- tests/test_walk_lint_gate.py
- docs/modules/gates.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: docs/modules/gates.md
  reason: T-2951 documents the new PLATFORM001 shape 4 in the gate catalog
  actor: logan
  at: '2026-08-26'
evidence:
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_default_arg_fires
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_module_constant_fires
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_class_attribute_fires
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_decorator_kwarg_fires
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_guarded_default_arg_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_ternary_guarded_constant_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_if_guarded_def_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_body_reference_is_quiet
- tests/test_walk_lint_gate.py::TestPlatform001ImportTimeEval::test_gate_fires_end_to_end
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
T-2936 fixed a real crash-on-Windows-import bug: `src/frob/process/
_reap.py`'s `arm_parent_death_signal(sig: int = signal.SIGKILL)` bound
a POSIX-only attribute as a default argument, evaluated unconditionally
at MODULE LOAD (a `def` statement's default values are computed once,
when the `def` itself executes) -- crashing the import of the whole
module (and everything that imports it) on Windows with an
AttributeError, before the function's own platform guard ever ran.

PLATFORM001 (T-2919, frob.gates._walk_lint._scan_platform_guards) does
NOT catch this shape. Its detector looks for `if <name> is None:`
guards on a name bound via the try/except-ImportError probe idiom --
this bug had no guard of any kind; the absence of a guard at
`def`-evaluation time WAS the bug. This is a structurally different
population from what PLATFORM001 currently covers:

  - module-level constant: `X = signal.SIGKILL` (unguarded)
  - default argument: `def f(x=signal.SIGKILL):` (unguarded)
  - class attribute: `class C: X = signal.SIGKILL` (unguarded)
  - decorator argument: `@deco(sig=signal.SIGKILL)` (unguarded)

all share the same defect shape: a platform-restricted attribute
(fcntl.*, signal.SIGKILL/SIGSTOP/etc, msvcrt.*, termios.*, pwd.*,
grp.*, resource.*, ...) referenced somewhere that Python evaluates
UNCONDITIONALLY at import/class-body time, with no platform guard
anywhere in reach, rather than lazily inside a function body a caller
might never invoke on the wrong platform.

Build a second PLATFORM00x rule (or extend PLATFORM001's own scan, if
that turns out cleaner) detecting this shape: an `ast.FunctionDef`
default value, an `ast.Assign` at module/class top level, or a
decorator-call keyword argument, whose value is (or contains) an
`ast.Attribute` access on one of the same `_PLATFORM_RESTRICTED_
MODULES` names PLATFORM001 already tracks, with NO enclosing
`if <module> is not None:`-shaped guard anywhere in its lexical scope.

Must-fire fixture: T-2936's own pre-fix `def arm_parent_death_signal(
sig: int = signal.SIGKILL)`. Must-stay-quiet fixture: its post-fix
`sig: int | None = None` form, and a genuinely-guarded module-level
constant (e.g. `_SIG = signal.SIGKILL if sys.platform != "win32" else
None`, evaluated inside an `if`/ternary that itself never raises on
import).

Re-run the sweep this ticket already did by hand (grep for `def
...=signal\.`, module-level `NAME = os/signal/fcntl\.ATTR`) once the
new rule exists, to confirm it reproduces the same "nothing else
repo-wide" finding as a STATIC fact, not a one-off manual grep.