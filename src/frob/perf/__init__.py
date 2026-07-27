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

`frob.perf._hotgraph`/`frob.perf._sampler` (T-0710, EPIC T-0709) add a
sampling-profiler alternative: a language-neutral `SampledStack` hit-stream
contract, a resolver mapping `(file, line)` samples onto normalized-model
sections (function/loop/branch bodies), and a python `StackSampler` --
the first of what T-0748 makes a multi-language family of producers into
the same contract. See docs/modules/perf.md#hot-graph-collector.
"""

from __future__ import annotations

from frob.perf._collectors import (
    CollectorError,
    build_class_to_file,
    build_index_for_files,
    detect_collector_format,
    parse_collector_format,
    parse_jfr_print,
    parse_perf_script,
    parse_v8_cpuprofile,
)
from frob.perf._heat import heat, join_smells, render_bar
from frob.perf._hotgraph import (
    UNATTRIBUTED_SECTION_ID,
    EdgeHit,
    HitStream,
    LanguageDecileRow,
    SampledFrame,
    SampledStack,
    Section,
    SectionHit,
    SectionIndex,
    build_section_index,
    language_deciles,
    resolve_stream,
)
from frob.perf._models import HeatEntry, HeatReport, PerfError, ProfileArtifact
from frob.perf._profile import load_artifact, profile_command
from frob.perf._recursion import recursion_rules
from frob.perf._redundancy import redundant_computation_violations
from frob.perf._rules import perf_rules
from frob.perf._sampler import SamplerConfig, StackSampler, run_sampled
from frob.perf._sketch_store import (
    SketchStoreConfig,
    get_sketch,
    load_sketch_config,
    new_run_sketch,
    put_sketch,
    stable_section_key,
    store_size_bytes,
)

# `frob.perf._harness.main` (T-0362) is deliberately NOT re-exported here: it
# is a standalone subprocess entrypoint invoked as `python _harness.py
# <pstats-out> ...` via `runpy` (see `_profile.py`'s `_harness_argv`), never
# imported by any package -- re-exporting a `main()` from a package
# `__init__.py` that nothing ever imports would be dead surface, not a real
# fix.

__all__ = [
    "UNATTRIBUTED_SECTION_ID",
    "CollectorError",
    "EdgeHit",
    "HeatEntry",
    "HeatReport",
    "HitStream",
    "LanguageDecileRow",
    "PerfError",
    "ProfileArtifact",
    "SampledFrame",
    "SampledStack",
    "SamplerConfig",
    "Section",
    "SectionHit",
    "SectionIndex",
    "SketchStoreConfig",
    "StackSampler",
    "build_class_to_file",
    "build_index_for_files",
    "build_section_index",
    "detect_collector_format",
    "get_sketch",
    "heat",
    "join_smells",
    "language_deciles",
    "load_artifact",
    "load_sketch_config",
    "new_run_sketch",
    "parse_collector_format",
    "parse_jfr_print",
    "parse_perf_script",
    "parse_v8_cpuprofile",
    "perf_rules",
    "profile_command",
    "put_sketch",
    "recursion_rules",
    "redundant_computation_violations",
    "render_bar",
    "resolve_stream",
    "run_sampled",
    "stable_section_key",
    "store_size_bytes",
]
