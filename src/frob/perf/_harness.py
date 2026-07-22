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
"""

# frob:waive TEST005 reason="module line coverage 0.0%, debt T-0160"

from __future__ import annotations

import cProfile
import os
import runpy
import sys
from collections import Counter
from pathlib import Path

from frob.logging import get_logger
from frob.perf._hotgraph import SectionIndex, build_section_index, resolve_stream
from frob.perf._sampler import SampledStack, StackSampler

_log = get_logger(__name__)

#: Environment variable gating the `StackSampler` wiring below -- opt-in
#: (never on by default) since resolving samples parses every distinct
#: file a sample landed in (T-0710 review round 2's harness-wiring
#: requirement; the persisted store is T-0711's job, this only logs).
_SAMPLE_ENV_VAR = "FROB_PERF_SAMPLE"


def _sampled_section_index(stacks: list[SampledStack]) -> SectionIndex:
    """Best-effort `SectionIndex` covering only the distinct python files
    referenced by `stacks`' frames -- parsing the whole repo at harness
    runtime would defeat the point of a low-overhead sampler. A file that
    fails to parse (not python, not on disk, a syntax error) is simply
    absent from the index -- `resolve_stream` already treats a frame that
    matches no section as `UNATTRIBUTED_SECTION_ID`, never an error, so
    this degrades the same NO-FAIL-SILENT way."""
    from frob.arch._python import PythonAdapter
    from frob.lang import raw_tree

    files = {frame.file for stack in stacks for frame in stack.frames}
    modules = []
    for file in sorted(files):
        path = Path(file)
        if not path.is_file():
            continue
        parsed = raw_tree(path)
        if parsed.is_err:
            continue
        tree, source, language = parsed.danger_ok
        if language != "python":
            continue
        modules.append(PythonAdapter().adapt(tree, source, file))
    return build_section_index(modules)


def _log_hotgraph_summary(stacks: list[SampledStack]) -> None:
    """Resolve `stacks` against a best-effort section index and log the
    top sections by weight plus the unattributed total -- the harness's
    "collect and log" wiring ahead of T-0711's persisted sketch store.
    Never raises: an empty/unresolvable stream just logs zeros."""
    if not stacks:
        _log.info("hotgraph: FROB_PERF_SAMPLE set but 0 samples collected")
        return
    index = _sampled_section_index(stacks)
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
# frob:waive TEST005 reason="main 0.0% branch cover, debt T-0160"
def main() -> int:
    """Profile the target argv, dump stats, and return the workload's code.

    When `FROB_PERF_SAMPLE=1` is set, also runs a `StackSampler` alongside
    cProfile and logs a resolved hot-graph section-hit summary (T-0710
    review round 2's harness wiring)."""
    if len(sys.argv) < 3:
        return 2
    out = sys.argv[1]
    target = sys.argv[2:]

    profiler = cProfile.Profile()
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
