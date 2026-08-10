"""Rule-level gate telemetry (T-1939).

AUDIT FINDING (full gate audit, 2026-08-09): `.frob/telemetry.jsonl`
(`frob.app.telemetry`, T-0178) records how long `frob check` TOOK and
whether it PASSED, but carries no rule dimension at all -- zero records
name a rule id. The question "which of our ~293 gate rules ever fire?"
could only be answered by proxy (grepping the ticket ledger for rule-id
mentions), which is biased toward rules that caused ARGUMENT, not rules
that caused WORK -- a rule that fires constantly and gets fixed without
comment looks identical to one that never fires at all.

This module closes that gap with the cheapest shape that answers the
question: one JSONL event per `frob check` gates-stage run, carrying a
`rule -> count` mapping over EVERY rule that fired at least once this
run (kept violation OR waived -- a waived rule still fired; only a rule
with zero total mentions across both never fired). No per-symbol/per-
file detail, no timing breakdown -- `GateStats.timing_s` already covers
per-FAMILY timing, and this module's own job is firing counts, not a
second profiler. Counting is a single pass over already-in-memory
`Violation` tuples (`GateReport.violations`/`.waived`, the exact shape
`run_gates` already returns at the end of every check) -- no new gate
walk, no new file I/O beyond one JSONL append, so this is cheap enough
to run on every `frob check` unconditionally rather than needing an
opt-in flag or a separate `frob gates stats` verb an operator has to
remember exists (this ticket's own explicit design directive: surface
automatically, where people already look, not behind a command name).

Reuses `frob.app.telemetry.append_event`'s existing best-effort,
`FROB_NO_TELEMETRY`-respecting JSONL writer rather than a second `.frob/`
file or a bespoke append path -- one write mechanism, one opt-out knob,
matching the "systematize friction" / "no duplication" engineering
principles this repo holds every module to.
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING

from frob.app.telemetry import append_event, iso_now
from frob.logging import get_logger

if TYPE_CHECKING:
    from frob.gates._models import GateReport

_log = get_logger(__name__)

# frob:doc docs/guides/agentic-time-profiling.md#rule-level-gate-firing-counts-t-1939
#: `frob.app.telemetry`'s existing `record["kind"]` discriminator value
#: for a rule-firing-counts event -- every OTHER telemetry record shape
#: uses `kind="cli"` or `kind="event"` (`frob.app.telemetry`'s own module
#: docstring), so this is a new, third `kind` sharing the same file/
#: append mechanism, not a parallel stream.
RULE_COUNTS_KIND = "gate_rule_counts"


# frob:doc docs/guides/agentic-time-profiling.md#rule-level-gate-firing-counts-t-1939
def rule_firing_counts(report: "GateReport") -> dict[str, int]:
    """`rule id -> total-fired count` over `report`, WAIVED findings
    included -- a waived rule still fired this run (the waiver is a
    policy decision about what to DO with the finding, not evidence the
    rule never ran). A rule id absent from the returned mapping fired
    zero times this run; the caller (or any downstream aggregator over
    the appended JSONL stream) is responsible for treating "never
    appeared in any record" as the true zero, this function has no
    all-293-rules roster to consult and does not attempt to synthesize
    one -- `frob.gates.__init__`'s own rule registry is the source of
    truth for "which rule ids exist at all", a question this counting
    pass over one run's OWN findings cannot and should not answer."""
    counts: Counter[str] = Counter()
    for violation in report.violations:
        counts[violation.rule] += 1
    for violation in report.waived:
        counts[violation.rule] += 1
    return dict(counts)


# frob:doc docs/guides/agentic-time-profiling.md#rule-level-gate-firing-counts-t-1939
# frob:tests tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts.test_appends_one_event_with_every_fired_rule  # noqa: E501
# frob:tests tests/unit/telemetry/test_rule_counts.py::TestRecordRuleFiringCounts.test_empty_report_appends_a_zero_rule_event  # noqa: E501
def record_rule_firing_counts(root: Path, report: "GateReport") -> None:
    """Append one `kind="gate_rule_counts"` telemetry event for this
    `frob check` gates-stage run's `rule_firing_counts(report)`.

    Best-effort by construction: `append_event` itself already never
    raises (an I/O failure logs at debug and is swallowed) and already
    respects `FROB_NO_TELEMETRY` -- this function adds no exception
    handling of its own because there is nothing left to guard beyond
    what `append_event` already guards. Always appends, even when
    `report` fired zero rules (an explicit `{}` counts mapping) --
    "this run examined the tree and found nothing" is itself a real,
    countable data point (a rule with a long streak of zero-count runs
    is a much stronger retirement signal than one that simply never
    appears in the stream, which is indistinguishable from "never ran
    at all")."""
    counts = rule_firing_counts(report)
    append_event(
        root,
        {
            "kind": RULE_COUNTS_KIND,
            "iso_ts": iso_now(),
            "rule_counts": counts,
            "distinct_rules_fired": len(counts),
        },
    )
    _log.debug(
        "record_rule_firing_counts: %d distinct rule(s) fired this run",
        len(counts),
    )


__all__ = [
    "RULE_COUNTS_KIND",
    "record_rule_firing_counts",
    "rule_firing_counts",
]
