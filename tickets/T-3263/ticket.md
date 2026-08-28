---
id: T-3263
title: render_lint_gate git-ls-files WARNING log line loses its level prefix under
  pytest
state: in-progress
kind: bug
origin: human
created: '2026-08-28'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/logging/**
- tests/system/test_cli_check.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
evidence:
- tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while root-causing T-3249's 11-failure cluster.
tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root
fails deterministically (reproduces in isolation, -p no:xdist, no
concurrency needed) on unmodified main.

Expected: capsys.readouterr().err contains
"WARNING: render_lint_gate: git ls-files exited". Actual: the same
message appears (3x, once per T-2719 pathspec) with NO "WARNING: "
level prefix at all:
  render_lint_gate: git ls-files exited 128
  render_lint_gate: git ls-files exited 128
  render_lint_gate: git ls-files exited 128

Evidence gathered, root cause NOT fully nailed down -- stating what I
found, not what I did not verify:

frob.logging.logger._init() (src/frob/logging/logger.py) checks
_under_pytest() ("pytest" in sys.modules) and, when true,
UNCONDITIONALLY sets cfg["root"]["handlers"] = [] before calling
logging.config.dictConfig(cfg) -- meaning frob's own _FrobFormatter
(which adds the "LEVELNAME: " prefix for WARNING+, src/frob/logging/
formatter.py) is never attached to the root logger's handler list
inside any pytest process, by design (T-1621, to avoid double-reporting
against pytest's own LogCaptureHandler).

The failing test's own docstring documents an EARLIER order-dependent
hazard (T-0818/T-0996) and works around it by resetting
_logger_module._initialized = False and calling get_logger(__name__)
again AFTER capsys swaps the streams. That workaround re-runs _init(),
but _under_pytest() is still True on the re-run, so root's handler list
is STILL forced empty -- frob's own formatter still never attaches, so
capsys observes only whatever Python's logging module does with a
root logger that has no handlers of its own (propagation to pytest's
LogCaptureHandler, or logging.lastResort, neither of which uses
_FrobFormatter's prefix convention).

Repro:
  uv run pytest -q -p no:xdist tests/system/test_cli_check.py::TestGitlessTargetGateSeverity::test_render_lint_gate_warns_not_errors_on_gitless_root

NOT a concurrency/host-load artifact -- confirmed via direct isolated
repro before any load was applied. Out of T-3249's scope (that ticket
owns the REF001/_STAGE_GROUPS/tickets.md-exemption subset of the
11-failure cluster; this is a separate, unrelated root cause in the
logging/pytest interaction).

Needs someone to decide the actual fix direction: either the test's
own capsys-based assertion is now testing something frob's pytest-mode
logging deliberately does not do (fix the test/its assumption), or
_under_pytest()'s handlers=[] should still preserve level-prefixing
somehow for a caller that explicitly wants it (fix the product). I have
not determined which is correct -- flagging both possibilities rather
than guessing.
