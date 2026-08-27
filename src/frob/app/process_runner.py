"""CLI wiring for `frob ops process reap` (T-3106): a first-class, on-
demand CLI verb for `frob.process.reap_orphaned_forkservers` (T-3072/
T-2443), which until now only ever ran as a best-effort side effect of
`frob check` startup. The documented remediation for a leaked forkserver
was "SIGTERM it by hand" -- exactly the improvised-shell friction this
repo has a standing directive to systematize instead of leaving to
per-agent judgment."""

from __future__ import annotations

import sys

from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


# frob:doc docs/modules/app.md#runners
# frob:ticket T-3106
# frob:tests tests/unit/test_app_runners_process.py::TestProcessRunnerReap.test_reap_reports_reaped_pids  # noqa: E501
# frob:tests tests/unit/test_app_runners_process.py::TestProcessRunnerReap.test_reap_reports_nothing_reaped  # noqa: E501
# frob:tests tests/unit/test_app_runners_process.py::TestProcessRunnerReap.test_reap_json_mode_emits_json  # noqa: E501
# frob:tests tests/unit/test_app_runners_process.py::TestProcessRunnerReap.test_unknown_process_subcommand_exits_1  # noqa: E501
def run(cfg: AppConfig) -> None:
    """`frob ops process <reap>`: currently the single `reap` subcommand,
    dispatched by `cfg.process_command` the same way every other T-1569
    verb-group member dispatches by its own `*_command` field (matching
    `ops_runner.run`'s existing per-member pattern this module joins)."""
    if cfg.process_command == "reap":
        _reap(cfg)
    else:
        _log.error(
            "frob ops process: unknown subcommand %r (expected: reap)",
            cfg.process_command,
        )
        sys.exit(1)


# frob:ticket T-3106
def _reap(cfg: AppConfig) -> None:
    """`frob ops process reap`: calls `reap_orphaned_forkservers` on
    demand and reports which pids (if any) were SIGTERM'd. SAFE UNDER
    CONCURRENCY BY CONSTRUCTION -- it reuses T-3072's own ancestry
    helpers (`_forkserver_root_is_live_check`'s multi-hop walk through
    `frob.process._reap`) rather than a second liveness rule, the exact
    class of bug T-3106's own investigation found THREE duplicate,
    broken copies of in this codebase already; a forkserver whose
    ancestry reaches ANY live `frob check` process, at any depth, is
    never touched, which is what makes running this command freely
    under a live multi-agent fleet -- where such chains always exist --
    safe rather than merely fast.

    Windows/macOS: `reap_orphaned_forkservers` itself is a structural
    no-op there (no `/proc`, and Windows never uses the `forkserver`
    multiprocessing start method at all) -- this command runs, reports
    zero pids reaped, and exits 0 rather than erroring; it does not
    (and cannot) reap anything on those platforms."""
    from frob.process import reap_orphaned_forkservers

    reaped = reap_orphaned_forkservers()

    renderer = Renderer.for_stream(sys.stdout)

    if cfg.process_reap_json:
        import json

        renderer.line(json.dumps({"reaped_pids": reaped}))
        return

    if not reaped:
        renderer.line(
            "frob ops process reap: nothing to reap (no orphaned forkserver "
            "found, or not on Linux -- see `frob ops process reap --help`)"
        )
        return
    renderer.line(
        f"frob ops process reap: SIGTERM'd {len(reaped)} orphaned "
        f"forkserver(s): {', '.join(str(pid) for pid in reaped)}"
    )
