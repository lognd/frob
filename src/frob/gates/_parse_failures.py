"""PARSE001/PARSE002: a source file `frob.lang` could not parse at all, or
could only be partially (salvaged) parsed (docs/modules/gates.md#rule-
catalog, T-0558/T-0905).

Motivating case (T-0404 finding 2): `frob.graph._parse_source_file_fresh`
used to swallow any `frob.lang.parse_file` error (other than the expected
`NativeParserUnavailable` degrade for a standalone install with no
strata-core native) and return `(True, (), (), ())` -- indistinguishable
from an empty file. The file's ENTIRE obligation set (every public
symbol, every `frob:doc`/`frob:invariant`/`frob:describes`/`frob:tests`
edge) silently vanished for that build, and every gate that would have
reasoned about its real content -- COV001, DRIFT, INV -- instead saw
nothing and passed vacuously. `frob.graph.GraphSnapshot.parse_failures`
(T-0558) now records every such failure; PARSE001 is the ERROR-tier gate
that turns a recorded failure into an actual `frob check` violation
instead of a warning only visible in logs.

PARSE002 (T-0905) closes the sibling, PARTIAL-parse half of the same
finding: `frob.lang._parse` can salvage a tree-sitter tree around a syntax
error (`has_error=True` but usable top-level structure) rather than
failing outright -- every symbol after the error region is silently
absent from that salvaged tree, with only a WARNING log line
(`frob.lang._warn_if_partial_tree`) and the queryable
`frob.lang.partial_parse_files()` accessor as evidence. Before T-0905,
nothing in `frob check` ever called that accessor -- a syntax error
partway through a file could silently drop every downstream obligation
(COV001, DRIFT, INV, TEST001-*) for everything after it. PARSE002 makes
that loud the same way PARSE001 does for a hard failure, reusing this
module's single `parse_failures` job entry (`frob.gates._ALL_GATES`) so
no gate-dispatch wiring changes -- `frob.lang.partial_parse_files()` is
read directly rather than threaded through `GraphSnapshot`, since it is
already the purpose-built, process-lifetime-scoped accessor for exactly
this signal (its own docstring: "Callers wanting to turn this into a
blocking `frob check` violation can wire a gate against this list").
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pathlib import Path

from frob.excludes import is_excluded, load_exclude_globs
from frob.gates._models import Severity, Violation
from frob.graph import GraphSnapshot
from frob.lang import partial_parse_files
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:ticket T-0942
def _partial_parse_violations(root: Path) -> tuple[Violation, ...]:
    """PARSE002: one ERROR violation per `frob.lang.partial_parse_files()` entry.

    Read directly off `frob.lang`'s process-lifetime accessor (T-0905) --
    NOT threaded through `GraphSnapshot` -- since `partial_parse_files()`
    is already reset once per `frob check` run (`frob.lang.
    reset_parse_cache`, called from `frob.check._run_check_with_skips`
    before any gate/snapshot work starts) and populated as a side effect
    of the very `frob.lang.parse_file`/`_parse` calls `st.snapshot`'s
    `build_graph` makes; forcing `snapshot` access below (via the
    `parse_failure_gate` caller) guarantees that population has already
    happened by the time this reads it.
    """
    # T-0942: graph-excluded paths (frob.toml [graph].exclude, e.g.
    # tests/fixtures/**'s deliberately-broken parser fixtures) contribute
    # no symbols to the obligation graph, so "symbols silently missing" is
    # vacuous there -- and in-file waivers cannot bind on excluded paths
    # (waivers attach through graph-ingested edges; same class T-0897
    # fixed for PII010/RENDER001/SEC-CVE). Skip them instead of firing an
    # unwaivable ERROR.
    exclude_globs = load_exclude_globs(root)
    violations: list[Violation] = []
    for path in partial_parse_files():
        if is_excluded(path, exclude_globs):
            _log.debug(
                "_partial_parse_violations: %s is graph-excluded, skipping",
                path,
            )
            continue
        violations.append(
            Violation(
                rule="PARSE002",
                severity=Severity.ERROR,
                file=path,
                line=0,
                message=(
                    f"PARSE002: {path} was only PARTIALLY parsed (tree-sitter "
                    "salvaged a tree around a syntax error) -- every symbol "
                    "after the error region is silently missing from this "
                    "build's obligation graph; fix the syntax error or "
                    'frob:waive PARSE002 reason="..." if this is a known, '
                    "intentionally-malformed fixture"
                ),
            )
        )
    _log.info("_partial_parse_violations: %d violation(s)", len(violations))
    return tuple(violations)


# frob:doc docs/modules/gates.md#rule-catalog
# frob:ticket T-0558
# frob:ticket T-0561
# frob:ticket T-0905
# frob:ticket T-0902
# frob:tests tests/test_gates.py::TestParseFailureGate.test_parse_failure_is_an_error_violation  # noqa: E501
# frob:tests tests/test_gates.py::TestParseFailureGate.test_no_parse_failures_is_clean
# frob:tests tests/test_gates.py::TestParseFailureGate.test_partial_parse_is_an_error_violation  # noqa: E501
# frob:tests tests/test_gates.py::TestParseFailureGate.test_no_partial_parses_is_clean
# frob:enforces CHK-GATE-PARSE001
# frob:enforces CHK-GATE-PARSE002
def parse_failure_gate(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PARSE001 + PARSE002: one ERROR per hard parse failure or partial parse.

    ERROR, not WARN, per the ticket's RIGHT-WAY direction: a swallowed
    parse/IO failure (PARSE001) or a silently symbol-dropping partial
    parse (PARSE002) hides real obligations from every downstream gate,
    which is a stronger silent-failure class than an advisory-tier
    finding (REF/PERF/FUZZ) -- it deserves to block a build, or be waived
    with an honest reason, not sit quietly in a log line.
    """
    violations = tuple(
        Violation(
            rule="PARSE001",
            severity=Severity.ERROR,
            file=failure.file,
            line=0,
            message=(
                f"PARSE001: {failure.file} could not be parsed/read -- its "
                "entire symbol/edge set is missing from this build "
                f"(reason: {failure.reason}); fix the file or "
                'frob:waive PARSE001 reason="..." if this is a known, '
                "intentionally-unparseable fixture"
            ),
        )
        for failure in snapshot.parse_failures
    )
    violations = violations + _partial_parse_violations(Path(snapshot.root))
    _log.info("parse_failure_gate: %d violation(s)", len(violations))
    return violations


# frob:doc docs/modules/gates.md#rule-catalog
# frob:tests tests/test_gates.py::TestRenderLintGate.test_unparseable_file_fires_parse001  # noqa: E501
def local_parse001_violation(
    rel_path: str,
    reason: str,
    cannot_clause: str,
    unparseable_word: str = "unparseable",
) -> Violation:
    """PARSE001 `Violation` for a per-gate LOCAL read/parse failure (T-0897,
    extracted T-0861): the shared shape three independent gates
    (`_pii_structural`, `_render_lint`, `_cve_fingerprint_scan`) each need
    when their own file read/`ast.parse` fails mid-scan -- one home so the
    rule id, severity, and PARSE001 message convention can never drift
    between the three call sites. `cannot_clause` is the gate-specific
    capability the caller lost (e.g. "PII010/SEC110 cannot inspect it for
    PII-shaped fields"); `unparseable_word` lets a caller say
    "unreadable" instead of "unparseable" where that reads better."""
    _log.warning("PARSE001: %s could not be parsed/read (%s)", rel_path, reason)
    return Violation(
        rule="PARSE001",
        severity=Severity.ERROR,
        file=rel_path,
        line=0,
        message=(
            f"PARSE001: {rel_path} could not be parsed/read -- {cannot_clause} "
            f"(reason: {reason}); fix the file or "
            'frob:waive PARSE001 reason="..." if this is a known, '
            f"intentionally-{unparseable_word} fixture"
        ),
    )
