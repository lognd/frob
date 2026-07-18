"""Run a target under cProfile while preserving its real exit code (T-0027).

cProfile's own CLI (`python -m cProfile -o out script.py`) swallows the
workload's SystemExit and always exits 0, so a failed profiled run is
invisible. This harness runs the target programmatically, captures its exit
code, dumps the pstats, and re-raises the code -- so the subprocess's return
status reflects the workload, not cProfile.

Usage: ``python _harness.py <pstats-out> (<script.py>|-m <module>) [args...]``
"""

# frob:waive TEST005 reason="module line coverage 0.0%, debt T-0160"

from __future__ import annotations

import cProfile
import runpy
import sys


# frob:doc docs/modules/perf.md#integration-points
# frob:waive TEST005 reason="main 0.0% branch cover, debt T-0160"
def main() -> int:
    """Profile the target argv, dump stats, and return the workload's code."""
    if len(sys.argv) < 3:
        return 2
    out = sys.argv[1]
    target = sys.argv[2:]

    profiler = cProfile.Profile()
    code = 0
    is_module = target[0] == "-m"
    if is_module:
        modname = target[1]
        sys.argv = [modname, *target[2:]]
    else:
        modname = ""
        sys.argv = list(target)

    try:
        profiler.enable()
        if is_module:
            runpy.run_module(modname, run_name="__main__", alter_sys=True)
        else:
            runpy.run_path(target[0], run_name="__main__")
    except SystemExit as exc:
        raw = exc.code
        code = raw if isinstance(raw, int) else (0 if raw is None else 1)
    finally:
        profiler.disable()
        profiler.dump_stats(out)
    return code


if __name__ == "__main__":
    sys.exit(main())
