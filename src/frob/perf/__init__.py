"""frob.perf -- profiling, heat-maps, and PERF linear-scan rules (docs/modules/perf.md).

# frob:ticket T-0021

Three interlocking pieces, per the doc: `profile_command` runs a workload
under cProfile and stores a content-addressed artifact; `heat` joins the
artifact's pstats rows onto the obligation graph's symbol spans, ranked by
cumulative time; `perf_rules` runs PERF001..PERF004, lexical linear-scan
smells, over `frob.lang`'s token stream. `frob perf heat --smells`
intersects the two: hot AND quadratic, the malmberg-incident fix generator
the doc names as the point of this package.
"""

from __future__ import annotations

from frob.perf._heat import heat, join_smells, render_bar
from frob.perf._models import HeatEntry, HeatReport, PerfError, ProfileArtifact
from frob.perf._profile import load_artifact, profile_command
from frob.perf._rules import perf_rules

# `frob.perf._harness.main` (T-0362) is deliberately NOT re-exported here: it
# is a standalone subprocess entrypoint invoked as `python _harness.py
# <pstats-out> ...` via `runpy` (see `_profile.py`'s `_harness_argv`), never
# imported by any package -- re-exporting a `main()` from a package
# `__init__.py` that nothing ever imports would be dead surface, not a real
# fix.

__all__ = [
    "HeatEntry",
    "HeatReport",
    "PerfError",
    "ProfileArtifact",
    "heat",
    "join_smells",
    "load_artifact",
    "perf_rules",
    "profile_command",
    "render_bar",
]
