"""frob.gates._directive_stack -- DSTACK001: N+ consecutive `frob:`
directive lines stacked above one symbol (T-4713, leaf 4 of T-4703).

T-4703 measured 1,712 runs of 3+ consecutive directive lines in this
repo (the largest 73 lines) before leaf 1 (T-4710) removed the reverse
`frob:tests` copy that was most of the volume. This module is the LINT
half only: it groups `GraphSnapshot.edges` by `(file, src)` -- every
edge whose comment lives at the same enclosing symbol -- and counts
DISTINCT `origin` values (one per physical/logical directive line; a
T-4711 multi-target line collapses several edges onto ONE origin, so it
counts once here too, exactly as a human reading the file would count
physical lines, not edges). A group at or past the configured threshold
is a finding, reported at its first (lowest-line) origin. The Tier-A
MERGE fix that collapses a flagged stack into T-4711's multi-target
form lives in `frob.gates._fix_engine_text.fix_dstack001_merge`; this
module only detects and names the finding.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence

from frob.gates._models import Severity, Violation
from frob.graph import Edge, GraphSnapshot
from frob.logging import get_logger

_log = get_logger(__name__)

#: T-4713: the stack-lint threshold's default -- "N+ consecutive directive
#: lines above one symbol is a finding", N configurable. This leaf's own
#: declared scope does not include `frob.toml` (a lease collision with a
#: concurrently in-progress ticket, T-4663, refused adding it at write
#: time -- see this ticket's Done report); `stack_lint_violations`'s own
#: `threshold` parameter is the configurability surface until a follow-up
#: wires a `frob.toml` value through to it.
DEFAULT_STACK_THRESHOLD = 4

RULE_DSTACK001 = "DSTACK001"


def _directive_groups(edges: Sequence[Edge]) -> dict[tuple[str, str], list[Edge]]:
    """Every edge in `edges`, grouped by `(origin file, src)` -- one group
    per symbol's own directive stack, across every edge kind (a stack is
    typically a mix of `frob:doc`/`frob:tests`/`frob:ticket`/etc, not one
    kind). Split out of `stack_lint_violations` for ARCH001."""
    groups: dict[tuple[str, str], list[Edge]] = defaultdict(list)
    for edge in edges:
        file = edge.origin.rpartition(":")[0] or edge.origin
        groups[(file, edge.src)].append(edge)
    return groups


def _stack_finding(
    file: str, group_edges: Sequence[Edge], *, threshold: int
) -> Violation | None:
    """One `(file, src)` group's DSTACK001 finding, or `None` when the
    group's distinct origin count is below `threshold` -- split out of
    `stack_lint_violations` for ARCH001. Distinct origins (not raw edge
    count) is the stack SIZE: a T-4711 multi-target line is one physical
    directive line even though it produces several edges."""
    origins = sorted({edge.origin for edge in group_edges})
    if len(origins) < threshold:
        return None
    first_line_text = origins[0].rpartition(":")[2]
    first_line = int(first_line_text) if first_line_text.isdigit() else 0
    src = group_edges[0].src
    return Violation(
        rule=RULE_DSTACK001,
        severity=Severity.WARN,
        file=file,
        line=first_line,
        message=(
            f"DSTACK001: {file}:{first_line} {len(origins)} consecutive "
            f"frob: directive lines stacked above {src!r} (threshold="
            f"{threshold}) -- merge same-kind directives into T-4711's "
            "multi-target form (`frob fmt --fix` / the DSTACK001 Tier-A "
            "handler)"
        ),
    )


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:ticket T-4713
# tests/test_gates_directive_stack.py::TestDstack001MergeFix.test_interleaved_doc_tests_doc_collapses_to_one_doc_then_one_tests  # noqa: E501
def edges_for_stack(
    snapshot: GraphSnapshot, *, file: str, src: str
) -> tuple[Edge, ...]:
    """Every edge in `snapshot.edges` belonging to the one `(file, src)`
    directive stack a DSTACK001 `Violation` names -- the read accessor
    `frob.gates._fix_engine_text.fix_dstack001_merge` uses to re-derive
    the exact edge set a merge must preserve, without re-deriving
    `_directive_groups`' own grouping logic a second time."""
    return tuple(_directive_groups(snapshot.edges).get((file, src), ()))


# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:ticket T-4713
# tests/test_gates_directive_stack.py::TestStackThresholdOffByOne.test_n_is_exactly_one_finding  # noqa: E501
def stack_lint_violations(
    snapshot: GraphSnapshot, *, threshold: int = DEFAULT_STACK_THRESHOLD
) -> tuple[Violation, ...]:
    """DSTACK001: every symbol carrying `threshold` or more distinct
    `frob:` directive lines directly above it. `threshold` defaults to
    `DEFAULT_STACK_THRESHOLD` (4, this leaf's documented default); a
    caller wiring a per-repo override (a future `frob.toml` value, once
    this leaf's own scope reaches that file) passes it here rather than
    this module re-reading config itself, keeping this function a pure
    `GraphSnapshot -> Violation` transform like every other gate in this
    package."""
    out: list[Violation] = []
    for (file, _src), group_edges in _directive_groups(snapshot.edges).items():
        finding = _stack_finding(file, group_edges, threshold=threshold)
        if finding is not None:
            _log.debug(
                "DSTACK001: %s:%d %s", finding.file, finding.line, finding.message
            )
            out.append(finding)
    return tuple(out)


__all__ = [
    "DEFAULT_STACK_THRESHOLD",
    "RULE_DSTACK001",
    "edges_for_stack",
    "stack_lint_violations",
]
