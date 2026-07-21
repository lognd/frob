"""frob.perf -- profiling, heat-maps, and PERF linear-scan/recursion rules
(docs/modules/perf.md).

# frob:ticket T-0021
# frob:ticket T-0290

Three interlocking pieces, per the doc: `profile_command` runs a workload
under cProfile and stores a content-addressed artifact; `heat` joins the
artifact's pstats rows onto the obligation graph's symbol spans, ranked by
cumulative time; `perf_rules` runs PERF001..PERF007 over `frob.lang`'s token
stream -- PERF001-004 are lexical linear-scan smells, PERF005/PERF006
(T-0290) are the prove-terminating-or-error / tail-call depth-bound
recursion checks (`frob.perf._recursion.recursion_rules`), and PERF007
(T-0413, the PERF META-GAP) is the cross-call-site redundant-recomputation
check (`frob.perf._redundancy.redundant_computation_violations`) -- a
`frob.toml`-configured expensive call invoked from 2+ distinct top-level
symbols with no shared cache. `frob perf heat
--smells` intersects the smell/hot-path signals: hot AND quadratic, the
malmberg-incident fix generator the doc names as the point of this package.
"""

from __future__ import annotations

from frob.perf._heat import heat, join_smells, render_bar
from frob.perf._models import HeatEntry, HeatReport, PerfError, ProfileArtifact
from frob.perf._profile import load_artifact, profile_command
from frob.perf._recursion import recursion_rules
from frob.perf._redundancy import redundant_computation_violations
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
    "recursion_rules",
    "redundant_computation_violations",
    "render_bar",
]
