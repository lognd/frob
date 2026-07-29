"""Run a target under cProfile while preserving its real exit code (T-0027).

cProfile's own CLI (`python -m cProfile -o out script.py`) swallows the
workload's SystemExit and always exits 0, so a failed profiled run is
invisible. This harness runs the target programmatically, captures its exit
code, dumps the pstats, and re-raises the code -- so the subprocess's return
status reflects the workload, not cProfile.

Usage: ``python _harness.py <pstats-out> (<script.py>|-m <module>) [args...]``

T-0710's hot-graph collector wiring (review round 2 -- "wire it, do not
defer"): set `FROB_PERF_SAMPLE=1` in the environment to additionally run a
`frob.perf._sampler.StackSampler` alongside cProfile and log a resolved
section-hit summary at the end of the run. T-0711's sketch store does not
exist yet, so this is deliberately a LOGGED summary, not a persisted
artifact -- the first real caller of `frob.perf._hotgraph.resolve_stream`
outside its own test suite, proving the contract composes with a real
workload before T-0711 gives it a place to land.

T-0948: unless `FROB_PERF_SERIAL_POOLS=0` is explicitly set, this harness
also calls `frob.perf._serial_pools.install_serial_pools()` before running
the target, so that any `ThreadPoolExecutor`/`ProcessPoolExecutor` the
target dispatches onto (frob's own gate dispatch, most notably) executes
inline on the already-instrumented thread instead of on invisible worker
threads/processes -- see that module's docstring for why cProfile/
StackSampler cannot see pool-dispatched work otherwise.
"""

# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import cProfile
import os
import runpy
import sys
from collections import Counter

from frob.logging import get_logger
from frob.perf._collectors import build_index_for_files
from frob.perf._hotgraph import resolve_stream
from frob.perf._sampler import SampledStack, StackSampler
from frob.perf._serial_pools import SERIAL_POOLS_ENV_VAR, install_serial_pools

_log = get_logger(__name__)

#: Environment variable gating the `StackSampler` wiring below -- opt-in
#: (never on by default) since resolving samples parses every distinct
#: file a sample landed in (T-0710 review round 2's harness-wiring
#: requirement; the persisted store is T-0711's job, this only logs).
_SAMPLE_ENV_VAR = "FROB_PERF_SAMPLE"


def _log_hotgraph_summary(stacks: list[SampledStack]) -> None:
    """Resolve `stacks` against a best-effort section index and log the
    top sections by weight plus the unattributed total -- the harness's
    "collect and log" wiring ahead of T-0711's persisted sketch store.
    Never raises: an empty/unresolvable stream just logs zeros."""
    if not stacks:
        _log.info("hotgraph: FROB_PERF_SAMPLE set but 0 samples collected")
        return
    files = {frame.file for stack in stacks for frame in stack.frames}
    index = build_index_for_files(files)
    stream = resolve_stream(index, stacks)
    totals: Counter[str] = Counter()
    for hit in stream.section_hits:
        totals[hit.section_id] += hit.weight
    top = totals.most_common(5)
    _log.info(
        "hotgraph: %d sample(s), %d section(s) hit, top=%s, "
        "unattributed_weight=%.1f, edge_hits=%d",
        len(stacks),
        len(totals),
        top,
        stream.unattributed_weight,
        len(stream.edge_hits),
    )


# frob:doc docs/modules/perf.md#integration-points
# frob:tests tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision.test_env_unset_installs_serial_pools  # noqa: E501
# frob:tests tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision.test_env_one_installs_serial_pools  # noqa: E501
# frob:tests tests/unit/perf/test_harness_sampling.py::TestHarnessSerialPoolsDecision.test_env_zero_skips_serial_pools  # noqa: E501
def main() -> int:
    """Profile the target argv, dump stats, and return the workload's code.

    When `FROB_PERF_SAMPLE=1` is set, also runs a `StackSampler` alongside
    cProfile and logs a resolved hot-graph section-hit summary (T-0710
    review round 2's harness wiring).

    Unless `FROB_PERF_SERIAL_POOLS=0` is set, also calls `install_serial_
    pools()` (T-0948) before running the target so pool-dispatched work
    (`ThreadPoolExecutor`/`ProcessPoolExecutor`, frob's own gate dispatch
    most notably) executes inline where cProfile/StackSampler can see it,
    rather than on invisible worker threads/processes -- see the
    TestHarnessSerialPoolsDecision tests bound above for the TEST016
    mutant (T-0948) this exact `!= "0"` comparison used to survive."""
    if len(sys.argv) < 3:
        return 2
    out = sys.argv[1]
    target = sys.argv[2:]

    # frob:waive SEC110 reason="pool-serialization behavior toggle, not a secret"
    if os.environ.get(SERIAL_POOLS_ENV_VAR, "1") != "0":
        install_serial_pools()

    profiler = cProfile.Profile()
    # frob:waive SEC110 reason="stack-sampling opt-in flag, not a secret"
    sampled = os.environ.get(_SAMPLE_ENV_VAR) == "1"
    sampler = StackSampler() if sampled else None
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
        if sampler is not None:
            sampler.start()
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
        if sampler is not None:
            stacks = sampler.stop()
            _log_hotgraph_summary(stacks)
    return code


if __name__ == "__main__":
    sys.exit(main())
