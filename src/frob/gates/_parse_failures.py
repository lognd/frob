"""PARSE001: a source file `frob.lang` could not parse/read at all
(docs/modules/gates.md#rule-catalog, T-0558).

Motivating case (T-0404 finding 2): `frob.graph._parse_source_file_fresh`
used to swallow any `frob.lang.parse_file` error (other than the expected
`NativeParserUnavailable` degrade for a standalone install with no
strata-core native) and return `(True, (), (), ())` -- indistinguishable
from an empty file. The file's ENTIRE obligation set (every public
symbol, every `frob:doc`/`frob:invariant`/`frob:describes`/`frob:tests`
edge) silently vanished for that build, and every gate that would have
reasoned about its real content -- COV001, DRIFT, INV -- instead saw
nothing and passed vacuously. `frob.graph.GraphSnapshot.parse_failures`
(T-0558) now records every such failure; this module is the ERROR-tier
gate that turns a recorded failure into an actual `frob check` violation
instead of a warning only visible in logs.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/gates/_parse_failures.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

from frob.gates._models import Severity, Violation
from frob.graph import GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)


# frob:doc docs/modules/gates.md#rule-catalog
# frob:ticket T-0558
# frob:ticket T-0561
# frob:tests tests/test_gates.py::TestParseFailureGate.test_parse_failure_is_an_error_violation  # noqa: E501
# frob:tests tests/test_gates.py::TestParseFailureGate.test_no_parse_failures_is_clean
def parse_failure_gate(snapshot: GraphSnapshot) -> tuple[Violation, ...]:
    """PARSE001: one ERROR violation per `snapshot.parse_failures` entry.

    ERROR, not WARN, per the ticket's RIGHT-WAY direction: a swallowed
    parse/IO failure hides real obligations from every downstream gate,
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
    _log.info("parse_failure_gate: %d violation(s)", len(violations))
    return violations
