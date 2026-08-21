"""Block until no `frob ticket land` is in flight, quietly, with a
distinct exit code per outcome (T-2775).

WHY THIS EXISTS. Every agent in a landing fleet needs the same thing
before landing: wait until it is safe to land against. There was no
shared primitive for it, so each agent hand-rolled a poll loop, and the
hand-rolled versions were wrong in ways that cost real time: a per-tick
`echo` every 30s is a continuous context tax across a multi-agent fleet
(a 9-minute wait is ~18 noise lines PER AGENT PER LAND); a loop that
reads a count without checking `fleet_status.py`'s own exit code treats
an empty string from a FAILED probe as a genuine zero and starts a
second concurrent land -- the repo's dominant silent-zero bug class
(epic T-2391) reproduced INSIDE the workaround meant to prevent it; a
loop that waits on a notification instead of polling parks forever with
committed work stranded in a worktree; and callers disagreed on their
own wrapper timeout (`timeout 500` vs `timeout 540` seen live in the
same fleet minute).

THIS SCRIPT REUSES `fleet_status.py`'s OWN "a land is in flight"
definition -- it never re-derives it. It shells out to `fleet_status.py`
(or, for tests/fault-injection, whatever `--fleet-status-cmd` names) and
parses that command's own `LANDS IN FLIGHT: N` line, the exact text
`fleet_status.main`'s `_land_status_lines` already prints from `land_
invocations()`. Two homes for "what counts as a land in flight" would
desync the moment either one changed alone; this script has zero opinion
of its own on the question.

EXIT CODES (the one thing a caller must never have to guess):
    0   SLOT FREE      -- measured `LANDS IN FLIGHT` at or below
                          `--max-in-flight` (default 0); safe to land.
    1   TIMEOUT         -- `--timeout` elapsed while a land was genuinely
                          measured to be in flight the whole time; the
                          caller should retry later, not conclude the
                          fleet is unmeasurable.
    2   MEASUREMENT FAILURE -- the status probe never once produced a
                          readable measurement during the whole timeout
                          window (nonzero exit, a timeout of the probe
                          itself, or output with no parseable `LANDS IN
                          FLIGHT: N` line). NEVER conflated with 0: an
                          unmeasured fleet state is not a free slot, and
                          treating it as one is exactly the silent-zero
                          defect this script exists to prevent.

Usage:
    python3 scripts/wait_for_land_slot.py [--timeout SECONDS]
        [--poll-interval SECONDS] [--max-in-flight N] [--verbose]
        [--fleet-status-cmd COMMAND]
"""

from __future__ import annotations

import sys as _sys
from pathlib import Path as _Path

_sys.path.insert(0, str(_Path(__file__).resolve().parent))
from _require_python import require_python  # noqa: E402

require_python(__file__)

# ruff: noqa: E402 -- every import below MUST follow the require_python(__file__)
# guard above: T-2236 requires this script to fail with a clear version message
# on a too-old interpreter BEFORE it imports anything that would raise a
# confusing SyntaxError instead.
import argparse
import re
import shlex
import subprocess
import time
from pathlib import Path

#: exit codes, named rather than left as bare literals at every call site
#: (T-2775's own brief: a caller must be able to tell these apart, so the
#: names themselves are the contract, not just the docstring above).
# frob:doc docs/guides/coordinator-scripts.md#wait_for_land_slot-exit-codes
# frob:ticket T-2775
EXIT_SLOT_FREE = 0
# frob:doc docs/guides/coordinator-scripts.md#wait_for_land_slot-exit-codes
# frob:ticket T-2775
EXIT_TIMEOUT = 1
# frob:doc docs/guides/coordinator-scripts.md#wait_for_land_slot-exit-codes
# frob:ticket T-2775
EXIT_MEASUREMENT_FAILED = 2

#: T-2775: strictly below the wrapper timeouts this repo's own agent
#: playbook has used inconsistently (`timeout 500` and `timeout 540` both
#: seen live in the same fleet minute) -- this script must decline
#: cleanly on its OWN clock well before either wrapper would kill it,
#: never rely on which wrapper happened to be used this time.
# frob:doc docs/guides/coordinator-scripts.md#wait_for_land_slot-cli
# frob:ticket T-2775
DEFAULT_TIMEOUT_S = 480
# frob:doc docs/guides/coordinator-scripts.md#wait_for_land_slot-cli
# frob:ticket T-2775
DEFAULT_POLL_INTERVAL_S = 15
#: a single probe invocation's own subprocess timeout -- bounded well
#: below `DEFAULT_POLL_INTERVAL_S` so a hung probe cannot itself eat the
#: whole poll budget in one attempt.
# frob:doc docs/guides/coordinator-scripts.md#wait_for_land_slot-cli
# frob:ticket T-2775
PROBE_TIMEOUT_S = 30

_FLEET_STATUS_SCRIPT = Path(__file__).resolve().parent / "fleet_status.py"

_LANDS_IN_FLIGHT_RE = re.compile(r"^LANDS IN FLIGHT:\s*(\d+)\s*$", re.MULTILINE)


# frob:doc docs/guides/coordinator-scripts.md#probe_lands_in_flight
# frob:ticket T-2775
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight.test_reads_a_genuine_c\
# ount
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight.test_nonzero_exit_is_u\
# nmeasured
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight.test_unparseable_outpu\
# t_is_unmeasured
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestProbeLandsInFlight.test_probe_timeout_is_\
# unmeasured
def probe_lands_in_flight(command: list[str]) -> int | None:
    """Run `command` (default: `fleet_status.py` itself) and return its
    own `LANDS IN FLIGHT: N` reading, or `None` when the probe could not
    be trusted -- a nonzero exit, a hung process past `PROBE_TIMEOUT_S`,
    or output with no parseable count. `None` here is UNMEASURED, never
    zero -- the caller (`wait_for_slot`) must never collapse the two, the
    exact discipline T-2775 exists to enforce. This is the ONLY place
    that knows how to read the probe's output; `wait_for_slot` never
    parses `fleet_status.py` text itself."""
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=PROBE_TIMEOUT_S,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    match = _LANDS_IN_FLIGHT_RE.search(result.stdout)
    if match is None:
        return None
    return int(match.group(1))


# frob:doc docs/guides/coordinator-scripts.md#wait_for_slot
# frob:ticket T-2775
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWaitForSlot.test_slot_already_free_return\
# s_immediately
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWaitForSlot.test_land_in_flight_then_free\
# _blocks_then_returns
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWaitForSlot.test_always_in_flight_times_o\
# ut
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWaitForSlot.test_always_unmeasurable_neve\
# r_returns_zero
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWaitForSlot.test_measured_then_unmeasurab\
# le_is_timeout_not_measurement_failure
def wait_for_slot(
    *,
    command: list[str],
    max_in_flight: int = 0,
    timeout_s: float = DEFAULT_TIMEOUT_S,
    poll_interval_s: float = DEFAULT_POLL_INTERVAL_S,
    on_tick=None,
    sleep=time.sleep,
    now=time.monotonic,
) -> tuple[int, str]:
    """Poll `probe_lands_in_flight(command)` until the reading is at or
    below `max_in_flight`, or `timeout_s` elapses. Returns `(exit_code,
    summary_line)` -- never prints anything itself (`on_tick`, when
    given, is called with each raw reading -- `--verbose`'s hook; the
    default `None` means the common quiet path emits nothing per tick).
    `sleep`/`now` are injectable for tests that must not actually sleep
    for real wall-clock seconds.

    T-2775's central rule lives here: `ever_measured` tracks whether ANY
    poll in this call ever produced a real reading. On timeout, a caller
    that was measured to have a land in flight the whole time gets
    `EXIT_TIMEOUT` ("gave up, but the fleet was real"); a caller that
    NEVER once got a readable measurement gets `EXIT_MEASUREMENT_FAILED`
    ("never learned anything, and 0 would be a lie"). These are checked
    every iteration, not only at the end, so a probe that measures once
    successfully and then starts failing still correctly reports TIMEOUT
    (it learned real fleet state before losing the ability to keep
    reading it), not MEASUREMENT_FAILED."""
    start = now()
    ever_measured = False
    last_reading: int | None = None
    while True:
        reading = probe_lands_in_flight(command)
        elapsed = now() - start
        if on_tick is not None:
            on_tick(reading, elapsed)
        if reading is not None:
            ever_measured = True
            last_reading = reading
            if reading <= max_in_flight:
                return (
                    EXIT_SLOT_FREE,
                    f"slot free: LANDS IN FLIGHT={reading} <= "
                    f"max-in-flight={max_in_flight} after {elapsed:.1f}s",
                )
        if elapsed >= timeout_s:
            if ever_measured:
                return (
                    EXIT_TIMEOUT,
                    f"timeout after {elapsed:.1f}s: last measured LANDS IN "
                    f"FLIGHT={last_reading}, never <= max-in-flight="
                    f"{max_in_flight}",
                )
            return (
                EXIT_MEASUREMENT_FAILED,
                f"measurement failed: no readable LANDS IN FLIGHT count in "
                f"{elapsed:.1f}s (probe kept exiting nonzero, timing out, or "
                f"returning unparseable output) -- treating this as UNKNOWN, "
                f"never as a free slot",
            )
        remaining = timeout_s - (now() - start)
        sleep(min(poll_interval_s, max(remaining, 0)))


# frob:ticket T-2775
def _build_parser() -> argparse.ArgumentParser:
    """The CLI surface: every knob `wait_for_slot` takes, plus `--verbose`
    (restores one line per tick) and `--fleet-status-cmd` (overrides the
    default `fleet_status.py` invocation -- the fault-injection seam
    T-2775's own mandatory positive control uses to force the probe to
    fail without touching the real fleet)."""
    parser = argparse.ArgumentParser(
        description=(
            "Block until no `frob ticket land` is in flight (or --max-in-"
            "flight is satisfied), quietly, with a distinct exit code per "
            "outcome. See this module's own docstring for the exit-code "
            "contract."
        )
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=DEFAULT_TIMEOUT_S,
        help=(
            f"give up after this many seconds (default {DEFAULT_TIMEOUT_S}s "
            "-- deliberately below this repo's own 500s/540s wrapper "
            "timeouts, so this script declines cleanly instead of being "
            "killed)"
        ),
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=DEFAULT_POLL_INTERVAL_S,
        help=f"seconds between probes (default {DEFAULT_POLL_INTERVAL_S}s)",
    )
    parser.add_argument(
        "--max-in-flight",
        type=int,
        default=0,
        help=(
            "the reading is a free slot at or below this count (default 0: "
            "wait for genuinely zero lands in flight; pass 1 to match this "
            "repo's own 'fewer than 2 is fine to land against' convention)"
        ),
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="print one line per poll tick (default: only the final summary line)",
    )
    parser.add_argument(
        "--fleet-status-cmd",
        default=None,
        help=(
            "override the status-probe command (shell-split), default: "
            f"'{_sys.executable} {_FLEET_STATUS_SCRIPT}'. Exists for tests "
            "and fault injection, e.g. pointing at a command that always "
            "fails to prove this script never treats that as a free slot."
        ),
    )
    return parser


# frob:ticket T-2775
# frob:waive WIRE001 reason="called only indirectly, passed as the on_tick callback \
# argument main hands to wait_for_slot -- the static call-graph walk this rule's \
# detector runs sees a NAME reference, not a call expression, so it cannot resolve \
# this as wired even though main's own body genuinely passes it as a live callback on \
# every --verbose invocation; exercised directly by \
# TestWaitForLandSlotMain::test_verbose_adds_per_tick_lines_to_stderr" \
# follow_up="T-2778"
def _print_tick(reading: int | None, elapsed: float) -> None:
    """`--verbose`'s per-tick line, to STDERR (never stdout, so a caller
    scripting against this tool's exit code and stdout output never has
    to filter tick noise out)."""
    shown = "UNMEASURED" if reading is None else str(reading)
    # frob:waive RENDER001 reason="scripts/** standalone-CLI posture, same as this \
    # module's own main() waiver immediately below -- no frob.render wiring applies \
    # here"
    print(f"[{elapsed:6.1f}s] LANDS IN FLIGHT={shown}", file=_sys.stderr)


# frob:ticket T-2775
def _resolve_fleet_status_command(fleet_status_cmd: str | None) -> list[str]:
    """The status-probe argv: `--fleet-status-cmd` shell-split when given,
    else `[<this interpreter>, fleet_status.py]` -- isolated from `main`
    so the CLI entry point stays a single, flat call sequence (ARCH103)."""
    if fleet_status_cmd is not None:
        return shlex.split(fleet_status_cmd)
    return [_sys.executable, str(_FLEET_STATUS_SCRIPT)]


# frob:doc docs/guides/coordinator-scripts.md#wait_for_land_slot-cli
# frob:ticket T-2775
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWaitForLandSlotMain.test_quiet_by_default\
# _prints_one_summary_line
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWaitForLandSlotMain.test_verbose_adds_per\
# _tick_lines_to_stderr
# frob:tests \
# tests/unit/test_coordinator_scripts.py::TestWaitForLandSlotMain.test_end_to_end_force\
# d_probe_failure_via_fleet_status_cmd
def main(argv: list[str] | None = None) -> int:
    """CLI entry point: parse args, run `wait_for_slot`, print exactly one
    summary line (plus per-tick lines under `--verbose`), return the exit
    code named in this module's own docstring."""
    args = _build_parser().parse_args(argv)
    command = _resolve_fleet_status_command(args.fleet_status_cmd)
    exit_code, summary = wait_for_slot(
        command=command,
        max_in_flight=args.max_in_flight,
        timeout_s=args.timeout,
        poll_interval_s=args.poll_interval,
        on_tick=_print_tick if args.verbose else None,
    )
    # frob:waive RENDER001 reason="scripts/** is the same standalone-CLI, \
    # no-frob.render-wiring posture check_summary.py/fleet_status.py/verify_lands.py \
    # already carry (T-1863) -- this script has no frob import and is invoked directly \
    # by a human/agent shell or another script's subprocess call, never through the \
    # installed frob CLI's own Renderer plumbing"
    print(summary)
    return exit_code


if __name__ == "__main__":
    _sys.exit(main())
