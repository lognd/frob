"""frob.perf -- profiling, heat-maps, and PERF linear-scan/recursion rules
(docs/modules/perf.md).

# frob:ticket T-0021
# frob:ticket T-0290

Three interlocking pieces, per the doc: `profile_command` runs a workload
under cProfile and stores a content-addressed artifact; `heat` joins the
artifact's pstats rows onto the obligation graph's symbol spans, ranked by
cumulative time; `perf_rules` runs PERF001..PERF008 over `frob.lang`'s token
stream -- PERF001-004 are lexical linear-scan smells, PERF005/PERF006
(T-0290) are the prove-terminating-or-error / tail-call depth-bound
recursion checks (`frob.perf._recursion.recursion_rules`), PERF007
(T-0413, the PERF META-GAP) is the cross-call-site redundant-recomputation
check (`frob.perf._redundancy.redundant_computation_violations`) -- a
`frob.toml`-configured expensive call invoked from 2+ distinct top-level
symbols with no shared cache -- and PERF008 (T-0775) is the loop-invariant
effectful-call detector (`frob.perf._loop_effects.
loop_invariant_effect_violations`): a loop whose body calls (directly, or
transitively through a local call-graph BFS) a process-spawn/directory-
walk effect with arguments that never vary across iterations. `frob perf heat
--smells` intersects the smell/hot-path signals: hot AND quadratic, the
malmberg-incident fix generator the doc names as the point of this package.

`frob.perf._hotgraph`/`frob.perf._sampler` (T-0710, EPIC T-0709) add a
sampling-profiler alternative: a language-neutral `SampledStack` hit-stream
contract, a resolver mapping `(file, line)` samples onto normalized-model
sections (function/loop/branch bodies), and a python `StackSampler` --
the first of what T-0748 makes a multi-language family of producers into
the same contract. See docs/modules/perf.md#hot-graph-collector.

`frob.perf._advisories`/`frob.perf._ratchet` (T-0712) add the consumer
side: `frob perf hot` queries T-0711's persisted sketch store; the three
advisory functions (external-call-dominates-loop, nested-loop fan-in,
heavy-tail variance) flag slow-operation shapes straight off a resolved
`HitStream`; PERF009 (`ratchet_violations`, wired into `frob check` via
`frob.gates.__init__.perf_gate`) fires when a section's current-run
sketch regresses beyond `[perf.sketch].ratchet_tolerance` relative to its
stored prior. See docs/modules/perf.md#hot-graph-query-surface-t-0712.

PERF010/011/013/014 (T-1225, `frob.perf._hotpath_smells.
hotpath_smell_violations`) are four lexical detectors mined from the
2026-07-29 hot-graph report's EPIC A root causes: a `yaml.safe_load`/
`yaml.load` call missing the C-accelerated loader, a repo-scan API
(`xref`/`exports_consumers`/`iter_files`) called inside a loop, more than
one `ast.walk(tree)` pass over the same tree in one function, and a
`re.finditer` call nested inside a pattern-list loop nested inside a
per-line loop.
"""

from __future__ import annotations

from frob.perf._advisories import (
    external_call_advisories,
    heavy_tail_advisories,
    nested_loop_fanin_advisories,
)
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
from frob.perf._dup_spawn import duplicate_spawn_violations
from frob.perf._effect_summaries import EffectGraph, Unknown
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
from frob.perf._hotpath_smells import hotpath_smell_violations
from frob.perf._loop_effects import loop_invariant_effect_violations
from frob.perf._models import HeatEntry, HeatReport, PerfError, ProfileArtifact
from frob.perf._profile import load_artifact, profile_command
from frob.perf._ratchet import (
    RatchetFinding,
    check_ratchet,
    load_ratchet_findings,
    ratchet_violations,
    save_ratchet_findings,
)
from frob.perf._recursion import recursion_rules
from frob.perf._redundancy import redundant_computation_violations
from frob.perf._rules import perf_rules
from frob.perf._sampler import SamplerConfig, StackSampler, run_sampled
from frob.perf._serial_pools import (
    SERIAL_POOLS_ENV_VAR,
    SerialExecutor,
    install_serial_pools,
)
from frob.perf._sketch_store import (
    SketchStoreConfig,
    StoredSketch,
    get_sketch,
    list_sketches,
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
    "SERIAL_POOLS_ENV_VAR",
    "UNATTRIBUTED_SECTION_ID",
    "CollectorError",
    "EdgeHit",
    "EffectGraph",
    "HeatEntry",
    "HeatReport",
    "HitStream",
    "LanguageDecileRow",
    "PerfError",
    "ProfileArtifact",
    "RatchetFinding",
    "SampledFrame",
    "SampledStack",
    "SamplerConfig",
    "Section",
    "SectionHit",
    "SectionIndex",
    "SerialExecutor",
    "SketchStoreConfig",
    "StackSampler",
    "StoredSketch",
    "Unknown",
    "build_class_to_file",
    "build_index_for_files",
    "build_section_index",
    "check_ratchet",
    "detect_collector_format",
    "duplicate_spawn_violations",
    "external_call_advisories",
    "get_sketch",
    "heat",
    "heavy_tail_advisories",
    "hotpath_smell_violations",
    "install_serial_pools",
    "join_smells",
    "language_deciles",
    "list_sketches",
    "load_artifact",
    "load_ratchet_findings",
    "load_sketch_config",
    "loop_invariant_effect_violations",
    "nested_loop_fanin_advisories",
    "new_run_sketch",
    "parse_collector_format",
    "parse_jfr_print",
    "parse_perf_script",
    "parse_v8_cpuprofile",
    "perf_rules",
    "profile_command",
    "put_sketch",
    "ratchet_violations",
    "recursion_rules",
    "redundant_computation_violations",
    "render_bar",
    "resolve_stream",
    "run_sampled",
    "save_ratchet_findings",
    "stable_section_key",
    "store_size_bytes",
]
