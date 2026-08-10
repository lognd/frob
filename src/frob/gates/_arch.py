"""ARCH001: complexity-aware long-function findings, channeled through the
gate/waiver path (docs/modules/gates.md#rule-catalog, T-0289).

T-0101's original decision kept `frob.arch`'s whole suggestion surface
outside the `Violation`/`frob:waive` pipeline (`frob.gates._unwaivable_channel_rules`'s
docstring) -- reasonable at the time, since `ArchSuggestion`s carried no
symbol identity a waiver could bind to precisely. T-0289 revisits exactly
one category, long-function, now that `frob.arch._python`/`_cpp` set
`symref`/`metric` on every long-function finding: a long-AND-complex
function residue is real technical debt that deserves the same reasoned,
auditable, at-the-code waiver every other rule gets (`frob:waive ARCH001
reason="..." [ceiling=N]`), not a silent "the tool doesn't listen here"
carve-out. Every OTHER arch category not listed below stays exactly as
T-0101 left it -- unwaivable-channel WARN-only suggestions, not gate
violations. Do not widen this module further without a fresh design
decision.

T-0728 is that fresh design decision for exactly three more categories:
`low-cohesion-class` (ARCH101), `god-module` (ARCH102), and
`mixed-concern-function` (ARCH103) -- T-0616's ARCH1xx SRP/cohesion family
(`frob.arch._srp`), each already carrying `symref` a waiver can bind to,
same shape as `long-function`. T-0616 built the checks but left them
un-dispatched by `analyze_project` and un-registered here (its Done
report's disclosed follow-up); this closes that catalogued-is-not-enforced
gap. All three channel at `Severity.WARN`, matching ARCH001 -- none of the
three has been observed to fire against this repo's own current source at
their calibrated `frob.app.config.load_arch_config` defaults (T-0728 Done
report), so WARN-not-ERROR is a plain precedent match, not a softening
made just to land quietly.

T-1034 is the next such fresh design decision, for exactly one more
category: `cpp-noexcept-throws` (CPPTHROW001, T-0687's C++ may-throw
analysis, `frob.arch._cpp_mayraise`). Unlike every category above, this
one channels at `Severity.ERROR`, not `Severity.WARN` -- an escaping
exception from a C++ `noexcept` function is `std::terminate` at runtime,
not a style preference a team can defer; `ArchSuggestion.severity` is
already `"error"` for this category (T-0687 added that `ArchSeverity`
value specifically for it, see `frob.arch._models`'s own module-level
comment), so this gate reads that severity through rather than
hardcoding `Severity.WARN` the way every prior category here does. A real
run against this repo's own source at landing time surfaced zero
findings (no `noexcept` function in this repo's own C++ test fixtures
reaches a may-throw call) -- there is no pre-existing debt corpus an
ERROR severity would instantly red, so ERROR ships directly, not deferred
behind a WARN-first promotion the way EXHAUST001/002 (T-0688) needed for
their own 176-finding first run.

T-1102 wires one more pre-existing category into this same map:
`large-file` (LARGE001, `frob.arch._check_large_file`, language-agnostic,
already computed by `analyze_project` for every walk but previously
advisory-only -- never channeled into a `Violation` a gate run or a
waiver could see). This is a WARN-first-turn-on, not an ERROR: this
repo's own source tree already carries known over-large production files
at filing time (see `frob.arch.__init__`'s `_check_large_file` docstring
and this ticket's Refile note in `tickets.md` for the disclosed count),
same debt-corpus posture as ARCH101-103 and EXHAUST001/002 above, not the
CPPTHROW001 zero-findings case just above it.
"""

from __future__ import annotations

from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: The `frob.arch` categories this gate channels into `Violation`s: the
#: original T-0289 long-function category plus (T-0728) T-0616's ARCH1xx
#: SRP/cohesion family, each mapped to its rule id.
_ARCH_LONG_FUNCTION_CATEGORY = "long-function"
_ARCH_CATEGORY_TO_RULE = {
    _ARCH_LONG_FUNCTION_CATEGORY: "ARCH001",
    "low-cohesion-class": "ARCH101",
    "god-module": "ARCH102",
    "mixed-concern-function": "ARCH103",
    # T-1034: cpp-noexcept-throws (frob.arch._cpp_mayraise, T-0687) --
    # see this module's own docstring for why this one category channels
    # at Severity.ERROR, not Severity.WARN like every category above.
    "cpp-noexcept-throws": "CPPTHROW001",
    # T-1102: large-file (frob.arch._check_large_file) -- language-
    # agnostic file-size check, already computed by `analyze_project` for
    # every walk but previously advisory-only. WARN first-turn-on (see
    # this module's own docstring for the disclosed turn-on count).
    "large-file": "LARGE001",
}

#: Categories (T-1034) whose `Violation` uses `Severity.ERROR` instead of
#: the `Severity.WARN` every prior `_ARCH_CATEGORY_TO_RULE` entry hardcodes
#: -- a `noexcept` hard-boundary violation is std::terminate at runtime,
#: not deferrable debt. Read as an allowlist (not the reverse) so a future
#: category added to `_ARCH_CATEGORY_TO_RULE` defaults to the existing
#: WARN precedent unless explicitly opted into ERROR here.
_ERROR_SEVERITY_CATEGORIES = frozenset({"cpp-noexcept-throws"})


# frob:doc docs/modules/gates.md#rule-catalog
# frob:enforces ACC-2-1-LONG-FUNCTION
# frob:enforces CHK-GATE-ARCH001
# T-1020-followup: T-0728 disclosed CHK-GATE-ARCH101/102/103 as a land
# obligation left for a later pass -- this closes it, same
# `_ARCH_CATEGORY_TO_RULE` sites ARCH001 already binds to.
# frob:enforces CHK-GATE-ARCH101
# frob:enforces CHK-GATE-ARCH102
# T-0339-close pass: CPPTHROW001 channels through this same
# category-to-rule map (T-1034 wired it above), so its enforces edge
# binds here with its ARCH siblings.
# frob:enforces CHK-GATE-CPPTHROW001
# frob:enforces CHK-GATE-ARCH103
# T-1102: large-file channels through this same category-to-rule map.
# frob:enforces CHK-GATE-LARGE001
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_two_cluster_class_fires_arch101  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_cohesive_class_does_not_fire_arch101  # noqa: E501
# frob:tests \
# tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_god_module_fires_arch102
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_mixed_concern_function_fires_arch103  # noqa: E501
# frob:tests tests/unit/test_arch_srp.py::TestArchGateSrpWiring.test_arch101_respects_explicit_frob_toml_override  # noqa: E501
# frob:tests tests/test_arch_gate.py::TestArchGateCppThrow.test_noexcept_may_throw_fires_cppthrow001_error  # noqa: E501
# frob:tests tests/test_arch_gate.py::TestArchGateCppThrow.test_noexcept_with_catch_all_does_not_fire_cppthrow001  # noqa: E501
# frob:tests \
# tests/test_arch_gate.py::TestArchGateLargeFile.test_large_file_fires_large001_warn
# frob:tests \
# tests/test_arch_gate.py::TestArchGateLargeFile.test_test_file_exempt_from_large001
# frob:tests tests/test_arch_gate.py::TestArchGateLargeFile.test_single_file_mode_matches_directory_walk  # noqa: E501
def arch_gate(root: Path) -> tuple[Violation, ...]:
    """ARCH001: one `Violation` per long-AND-complex python/C++ function
    `frob.arch.analyze_project` still flags after its complexity filter
    (`frob.arch._python._py_is_complex` / `_cpp._cpp_is_complex`).
    T-0728 adds ARCH101 (`low-cohesion-class`), ARCH102 (`god-module`), and
    ARCH103 (`mixed-concern-function`) -- T-0616's ARCH1xx SRP/cohesion
    family, now dispatched by `analyze_project` itself
    (`frob.arch._run_srp_checks_python`). T-1034 adds CPPTHROW001
    (`cpp-noexcept-throws`, T-0687's C++ may-throw analysis,
    `frob.arch._cpp_mayraise`) -- see this module's own docstring for why
    THIS rule channels at `Severity.ERROR`, every other rule here at
    `Severity.WARN`. T-1102 adds LARGE001 (`large-file`,
    `frob.arch._check_large_file`) at `Severity.WARN`, same posture as
    ARCH001/ARCH1xx -- a file-level finding has no function/class symbol
    to bind a `symref` to, so its `Violation.symref` stays `None` and a
    `frob:waive LARGE001 reason="..."` binds by file/line like any other
    unsymref'd rule. Every rule's `symref`/`metric` carried through so
    `frob.gates._match_waiver` can bind a `frob:waive ARCHxxx
    reason="..." [ceiling=N]` to the exact symbol.

    T-0373: thresholds come from `frob.app.config.load_arch_config` (the
    repo's `[arch]` `frob.toml` table, calibrated-default fallback) instead
    of `analyze_project`'s own conservative keyword defaults -- the gate
    used to silently ignore the user's disclosed 60/800 calibration. T-0728
    extends the same threading to its own five ARCH1xx knobs."""
    from frob.app.config import load_arch_config
    from frob.arch import analyze_project

    result = analyze_project(root, **load_arch_config(root))
    violations: list[Violation] = []
    for s in result.suggestions:
        rule = _ARCH_CATEGORY_TO_RULE.get(s.category)
        if rule is None:
            continue
        severity = (
            Severity.ERROR
            if s.category in _ERROR_SEVERITY_CATEGORIES
            else Severity.WARN
        )
        violations.append(
            Violation(
                rule=rule,
                severity=severity,
                file=s.file,
                line=s.line or 0,
                message=f"{rule}: {s.message}",
                symref=s.symref,
                metric=s.metric,
            )
        )
    _log.info("arch_gate: %d arch-family violation(s)", len(violations))
    return tuple(violations)


# frob:doc docs/modules/gates.md#data-models
# frob:ticket T-1921
# frob:tests tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites.test_archgate_examined_sites_include_a_real_python_file  # noqa: E501
# frob:tests tests/unit/gates/test_examined_sites.py::TestAttachExaminedSites.test_archgate_examined_sites_exclude_an_unparseable_file  # noqa: E501
# frob:waive WIRE001 reason="already called at runtime from \
# frob.gates._coverage_sites._load_family_reporters, which stores it as a dict value \
# and invokes it indirectly (reporters[family](root)) -- the exact shape static \
# call-graph analysis cannot trace through; genuinely wired, not dead" \
# follow_up="T-1965"
def arch_examined_sites(root: Path) -> frozenset[str]:
    """T-1921: the per-site analysis-coverage substrate's ARCH-family
    reporter -- the repo-relative file paths `arch_gate`'s own
    `analyze_project(root, ...)` call actually parsed and checked this
    run (`ArchResult.files_examined`, itself built from `_analyze_one_
    file`'s real success/failure outcome, never merely "was in the
    walk's candidate list" -- see that function's own docstring).

    Calls `analyze_project` a SECOND time rather than threading the
    first call's result through `arch_gate`'s own return value, so
    `arch_gate`'s public `(root) -> tuple[Violation, ...]` contract stays
    exactly what every other Tier-A/dispatch consumer already expects --
    `analyze_project` is memoized per `frob check` run (T-0423,
    `frob.check._memo.memoize_per_run`, see its own docstring), so this
    second call is a cache hit, not a second tree walk, PROVIDED it is
    called with the identical `**load_arch_config(root)` kwargs
    `arch_gate` used; a caller invoking this standalone (outside the
    same `frob check` run `arch_gate` ran in) pays one real walk, same
    cost as any other on-demand `frob.gates._coverage_sites.attach_
    examined_sites` call."""
    from frob.app.config import load_arch_config
    from frob.arch import analyze_project

    result = analyze_project(root, **load_arch_config(root))
    return frozenset(result.files_examined)


__all__ = ["arch_examined_sites", "arch_gate"]
