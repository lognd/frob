---
id: T-2962
title: Split PLATFORM001 out of _walk_lint.py (LARGE001, T-2944 follow-up)
state: queued
kind: feature
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
`src/frob/gates/_walk_lint.py` crossed LARGE001's 800-line threshold
after T-2944 added two more PLATFORM001 detection shapes (a silent
platform-string guard scan and a bare-restricted-import scan) alongside
the existing WALK001 traversal scan and the original PLATFORM001
`X is None` scan. Unlike several other LARGE001-waived files in this
repo (`app/check_runner.py`, `app/config.py`), this module DOES have a
natural seam: WALK001 (raw traversal detection) and PLATFORM001 (the
whole platform-degrade population, now three shapes) are two
independently-testable AST scans that happen to share the file only for
"one pass over the tree" convenience (module docstring's own words),
not because they are the same concern.

Split PLATFORM001's scan functions/violation builders (_PLATFORM_
RESTRICTED_MODULES, _restricted_import_names, _handles_import_error,
_none_bound_names, _platform_guard_names, _is_none_names, the T-2934
typed-result-exit helpers, _guard_is_loud, _guard_logs, _PlatformSite,
_scan_platform_guards, _is_platform_string_read,
_is_platform_string_guard_test, _is_degrade_body,
_scan_platform_string_guards, _scan_bare_restricted_imports, and the
three _platform001_*_violation builders) into their own module
(e.g. `src/frob/gates/_platform_guards.py`), imported by
`_walk_lint.py::walk_lint_gate` the same way `walk_lint_gate` is
imported by `frob/gates/__init__.py` today. Re-home the corresponding
tests out of `tests/test_walk_lint_gate.py` into a new
`tests/test_platform_guards_gate.py`. Update every `frob:doc`/
`frob:tests` directive that currently points at `_walk_lint.py` for a
PLATFORM001 symbol.

Filed per T-2944's own Done report: `_walk_lint.py` needed a
`frob:waive LARGE001` to land T-2944's two new shapes because a real
file split was outside T-2944's declared scope
(`src/frob/gates/_walk_lint.py`, `src/frob/process/_reap.py`,
`src/frob/tickets/_leases.py`, two test files) -- not attempted there.
