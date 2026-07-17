"""Verdict report rendering for the strata kernel (docs/strata/kernel.md).

Turns the flat `tuple[ClaimResult, ...]` `evaluate_claims` returns into the
human-facing report `frob sys check` prints (later phases) and a
machine-facing count summary. Pure and total: no I/O, no `Result` wrapping
-- there is no fallible step here (charter law 4, "never a vibe" applies to
what the checker asserts, not to formatting it).
"""

from __future__ import annotations

from frob.logging import get_logger
from frob.logging.color import CYAN, GREEN, RED, YELLOW, paint

from ._models import ClaimResult, Verdict

_log = get_logger(__name__)

# Verdict -> (display tag, right-padded width, color code).
_TAG_WIDTH = 8  # len("REFUTED") + pad; ASSUMED/EVIDENCED are shorter
_TAGS: dict[Verdict, tuple[str, str]] = {
    Verdict.PROVED: ("PROVED", GREEN),
    Verdict.REFUTED: ("REFUTED", RED),
    Verdict.ASSUMED: ("ASSUMED", YELLOW),
    Verdict.EVIDENCED: ("EVIDENCED", CYAN),
}

# Listing order: most severe first (law 3 -- a refutation must never hide
# behind a page of proofs).
_ORDER: dict[Verdict, int] = {
    Verdict.REFUTED: 0,
    Verdict.ASSUMED: 1,
    Verdict.EVIDENCED: 2,
    Verdict.PROVED: 3,
}


def _sorted(results: tuple[ClaimResult, ...]) -> list[ClaimResult]:
    """Refuted first, then assumed, then evidenced, then proved; stable by claim_id."""
    return sorted(results, key=lambda r: (_ORDER[r.verdict], r.claim_id))


def _tag(result: ClaimResult, *, color: bool) -> str:
    """The right-padded, optionally colored verdict tag for one result."""
    text, code = _TAGS[result.verdict]
    padded = text.ljust(_TAG_WIDTH)
    return paint(padded, code, color)


# frob:doc docs/strata/kernel.md#verdict-report
def render_report(results: tuple[ClaimResult, ...], *, color: bool = False) -> str:
    """The deterministic plain-text verdict report for one evaluation run.

    One line per claim (verdict tag, id, quantifier, detail), a witness
    path line under any refutation, a summary count line, and -- only when
    an assume closed the run -- an assumption ledger section. `color`
    defaults False so JSON/log-piped output is never polluted with ANSI
    (`frob.logging.color`); a caller opts in only for a TTY.
    """
    ordered = _sorted(results)
    lines: list[str] = []
    for result in ordered:
        tag = _tag(result, color=color)
        lines.append(
            f"{tag} {result.claim_id} [{result.quantifier.value}] -- {result.detail}"
        )
        if result.verdict is Verdict.REFUTED and result.counterexample:
            lines.append(f"  path: {' -> '.join(result.counterexample)}")

    counts = summarize(results)
    lines.append("")
    lines.append(
        f"{len(results)} claim(s): {counts[Verdict.PROVED.value]} proved, "
        f"{counts[Verdict.REFUTED.value]} refuted, "
        f"{counts[Verdict.ASSUMED.value]} assumed, "
        f"{counts[Verdict.EVIDENCED.value]} evidenced"
    )

    assumed = [r for r in ordered if r.verdict is Verdict.ASSUMED]
    if assumed:
        lines.append("")
        lines.append("## Assumption ledger")
        for result in assumed:
            lines.append(f"  {result.claim_id}: {result.detail}")

    report = "\n".join(lines)
    _log.debug(
        "rendered verdict report: %d claim(s), %d byte(s)", len(results), len(report)
    )
    return report


# frob:doc docs/strata/kernel.md#verdict-report
def summarize(results: tuple[ClaimResult, ...]) -> dict[str, int]:
    """Per-verdict counts over `results`; all four `Verdict` keys always present."""
    counts = {v.value: 0 for v in Verdict}
    for result in results:
        counts[result.verdict.value] += 1
    return counts


__all__ = ["render_report", "summarize"]
