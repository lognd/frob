"""SIGUSR1 stack-dump handler (T-1433, extended beyond pytest by T-1466):
a live, reusable diagnostic ANY frob process can opt into -- install it and
a `SIGUSR1` sent to that process dumps every live thread's stack to
`.frob/stackdumps/pid-<pid>.txt`, self-diagnosing a wedge instead of
leaving only a bare `wchan=futex_wait_queue` with no indication of which
lock, in which function.

T-1433 wired this ONLY into `tests/conftest.py`'s `pytest_configure` (the
`make coverage` xdist/serial-rerun phases that motivated it), which left
`WIRE001` flagging both helpers as unreached outside their own tests --
`tests/conftest.py` is itself a test-path the gate's text scan skips, so a
test-only definition looked structurally dead from any non-test caller's
point of view. Moving the reusable core here (T-1466) closes that: any
process -- `frob serve`'s daemon, `frob check`'s own subprocess pool, or
`tests/conftest.py` itself -- can call `install_stackdump_handler` and get
the same opt-in, near-zero-cost-until-triggered diagnostic.

`tests/conftest.py` is left as a thin wrapper (still owns its own
`pytest_configure` wiring and its own `_STACKDUMP_ENV` re-export for
source-compat with existing tests) rather than moved wholesale, since
`tests/conftest.py`'s own env-var name and its pytest-specific install
timing are still real, correct docs for the ONE caller T-1433 actually
built this for; T-1466 only had to make the underlying mechanism
independently reachable, not relocate every caller."""

from __future__ import annotations

import faulthandler
import os
import signal
from pathlib import Path

# frob:doc docs/modules/testing.md#sigusr1-stack-dump-handler-t-1433-t-1466
#: Opt-in env var (T-1433): when set to a nonempty, non-`0`/`false` value,
#: `install_stackdump_handler` installs a `SIGUSR1` handler that dumps
#: every live thread's stack (via `faulthandler.dump_traceback`) of the
#: process that receives it. Off by default: the handler itself is
#: near-zero-cost once installed, but installing a signal handler
#: unconditionally in every ordinary process invocation that never wedges
#: is unnecessary surface area.
STACKDUMP_ENV = "FROB_COVERAGE_STACKDUMP"


# frob:ticket T-1433
# frob:ticket T-1466
# frob:ticket T-1823
# frob:doc docs/modules/testing.md#sigusr1-stack-dump-handler-t-1433-t-1466
# frob:tests tests/unit/test_stackdump.py::TestStackdumpHandler.test_sigusr1_writes_all_thread_stacks_when_enabled  # noqa: E501
def dump_all_thread_stacks(_signum: int, _frame: object) -> None:
    """`SIGUSR1` handler (T-1433, moved here T-1466): write every live
    thread's stack in THIS process to a per-pid file under
    `.frob/stackdumps/` so a wedge self-diagnoses instead of leaving only
    a bare `wchan=futex_wait_queue` with no indication of which lock, in
    which function, on which process. Appends (`"a"`) rather than
    truncates -- a wedge investigated by sending `SIGUSR1` more than once
    (e.g. once per suspect-narrowing probe) keeps every dump, timestamped
    by the surrounding `faulthandler.dump_traceback` call's own
    thread-id/frame text, not just the last one."""
    dump_dir = Path(".frob") / "stackdumps"
    dump_dir.mkdir(parents=True, exist_ok=True)
    dump_path = dump_dir / f"pid-{os.getpid()}.txt"
    with dump_path.open("a", encoding="utf-8") as fh:
        fh.write(f"\n--- SIGUSR1 stack dump, pid={os.getpid()} ---\n")
        faulthandler.dump_traceback(file=fh, all_threads=True)


# frob:ticket T-1433
# frob:ticket T-1466
# frob:ticket T-1823
# frob:doc docs/modules/testing.md#sigusr1-stack-dump-handler-t-1433-t-1466
# frob:tests tests/unit/test_stackdump.py::TestStackdumpHandler.test_handler_not_installed_when_env_unset  # noqa: E501
def install_stackdump_handler() -> None:
    """Install `dump_all_thread_stacks` as the `SIGUSR1` handler for THIS
    process, gated on `STACKDUMP_ENV` (T-1433, generalized beyond pytest
    by T-1466). Safe to call from ANY frob process -- pytest's
    controller/worker, `frob serve`'s daemon, a `frob check` subprocess
    pool member -- the wedge this exists to diagnose can live in any of
    them, and only sending the signal to the actually-stuck process
    produces a useful dump. `SIGUSR1` is POSIX-only (absent on Windows,
    where `signal.SIGUSR1` does not exist); silently a no-op there."""
    # frob:waive SEC110 reason="FROB_COVERAGE_STACKDUMP is a boolean opt-in feature \
    # flag (same shape as the existing FROB_AGENT/FROB_NO_TELEMETRY precedent), gating \
    # whether a SIGUSR1 stack-dump handler is installed; it carries no \
    # secret/confidential value"
    value = os.environ.get(STACKDUMP_ENV, "")
    if value.strip().lower() in ("", "0", "false"):
        return
    sigusr1 = getattr(signal, "SIGUSR1", None)
    if sigusr1 is None:  # pragma: no cover - POSIX-only, not exercised on Windows CI
        return
    signal.signal(sigusr1, dump_all_thread_stacks)
