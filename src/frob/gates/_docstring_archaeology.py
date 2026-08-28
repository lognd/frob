"""DOCARCH001 (T-2988): a docstring carrying change-NARRATIVE rather than
utility -- prose that reads as "what a prior attempt got wrong" or "which
policy superseded which" instead of "how and when to reuse this code".

T-2988's decision (see `docs/modules/docstrings.md`): tickets carry
narrative, code and docs carry utility. A docstring MAY carry a ticket
REFERENCE (`see T-0632 for the design rationale`); it must not carry the
ARGUMENT itself (`this used to walk the raw AST until T-0632 folded the
projection in, before which T-0370 had tried...`). The two shapes share a
surface -- both cite a `T-\\d+` id -- so citation alone cannot be the
signal (766+ legitimate provenance-shaped citations exist in this repo
today; see T-2988's measured baseline). This mirrors `frob.gates._waive`'s
WAIVE009/010 PROVENANCE-vs-DEFERRED-WORK discriminator exactly: key off
WORDING, not citation shape.

`_NARRATIVE_PHRASE_RES` is calibrated narrowly against phrasing that only
makes sense describing a CHANGE ("used to", "previously", "prior
attempt", "was originally", "before this", "folded into", "moved from/to",
"extracted from", "superseded", "replaced" ...) -- never a bare "why"
statement, which is legitimate utility prose (explaining a non-obvious
invariant) even when it happens to cite a ticket for provenance.

WARNING-tier, matching WAIVE010's own posture: this is a judgement call
over free text, not a mechanically-certain fact, so it nudges rather than
blocks. `frob:waive DOCARCH001 reason="..."` is the escape hatch for a
docstring the discriminator misreads.
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.lang import parse_file
from frob.logging import get_logger
from frob.xref import _collect_source_files

_log = get_logger(__name__)

_TICKET_ID_RE = re.compile(r"\bT-(?:draft-[0-9a-fA-F]+|\d+)\b")

# Calibrated against this repo's own real docstrings (T-2988 worked
# example: `frob.arch._python`'s tuple-returning function, whose ~17 of
# ~20 docstring lines narrate which prior ad-hoc walk T-0632 folded into
# which shared field and why T-0370's alternative stayed on the raw AST).
# Each pattern names a CHANGE happening to the code, never a property the
# code currently has -- "this used to X" and "this was replaced by Y" are
# narrative; "this is X because Y" is utility even when Y cites a ticket.
_NARRATIVE_PHRASE_RES = tuple(
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"\bused to\b",
        r"\bpreviously\b",
        r"\bprior (?:attempt|version|approach|walk|implementation)\b",
        r"\bwas (?:originally|previously)\b",
        r"\bbefore this (?:change|ticket|fix|commit)\b",
        r"\bfolded into\b",
        r"\bfolded .{0,40}? into\b",
        r"\bmoved (?:to|from|out of|into)\b",
        r"\bextracted (?:from|to|out of|into)\b",
        r"\bsuperseded\b",
        r"\breplaced by\b",
        r"\bthe old\b",
        r"\bthe prior\b",
        r"\bhistorically\b",
        r"\bnow lives (?:in|at)\b",
        r"\bwhich (?:ticket|policy) superseded\b",
        r"\bwhat a prior\b",
    )
)


def _doc_cites_ticket(doc_text: str) -> bool:
    """Whether `doc_text` mentions any `T-\\d+`/`T-draft-...` id anywhere."""
    return _TICKET_ID_RE.search(doc_text) is not None


def _doc_reads_as_narrative(doc_text: str) -> bool:
    """Whether `doc_text` uses phrasing that only makes sense describing a
    CHANGE to the code (`_NARRATIVE_PHRASE_RES`) -- the wording half of
    the discriminator, independent of ticket-citation shape (mirrors
    `frob.gates._waive._reason_reads_as_deferred_work`'s own posture:
    citation shape alone is the normal form of the legitimate provenance
    case too, so it cannot be the signal by itself)."""
    return any(pattern.search(doc_text) for pattern in _NARRATIVE_PHRASE_RES)


def _is_archaeology(doc_text: str) -> bool:
    """DOCARCH001's trigger condition: cites a ticket AND reads as
    change-narrative. Either alone is legitimate (a bare ticket reference
    for provenance; ordinary prose that happens to use a word like
    'replaced' with no ticket in sight) -- only the conjunction is the
    ticket-archaeology shape T-2988 measured."""
    return _doc_cites_ticket(doc_text) and _doc_reads_as_narrative(doc_text)


def _docarch001_violation(*, file: str, line: int, symref: str) -> Violation:
    """The single DOCARCH001 `Violation` for one symbol whose docstring
    reads as ticket archaeology rather than utility prose."""
    _log.warning(
        "DOCARCH001: %s docstring reads as change-narrative, not utility", symref
    )
    return Violation(
        rule="DOCARCH001",
        severity=Severity.WARN,
        file=file,
        line=line,
        message=(
            f"DOCARCH001: {symref}'s docstring cites a ticket and reads as "
            f"change-narrative (what a prior attempt got wrong, which "
            f"policy superseded which) rather than utility (how and when "
            f"to reuse this code) -- move the argument into the cited "
            f"ticket's body and leave a one-line reference here "
            f"('see T-#### for the design rationale'), per "
            f"docs/modules/docstrings.md's purpose test"
        ),
        symref=symref,
    )


# frob:enforces CHK-GATE-DOCARCH001
# frob:ticket T-2988
# frob:doc docs/modules/docstrings.md#docarch001
# frob:tests \
# tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_ticket_plus_narrative_wording_warns  # noqa: E501
# frob:tests \
# tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_bare_ticket_reference_stays_quiet  # noqa: E501
# frob:tests \
# tests/gates/test_docstring_archaeology.py::TestDocarch001Violations::test_long_utility_docstring_stays_quiet  # noqa: E501
# frob:tests \
# tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_fires_through_run_gates  # noqa: E501
# frob:tests \
# tests/gates/test_docstring_archaeology.py::TestDocarch001Wiring::test_utility_only_does_not_fire_through_run_gates  # noqa: E501
def docarch001_violations(root: Path) -> tuple[Violation, ...]:
    """DOCARCH001: a public or module-public symbol's docstring reads as
    ticket archaeology (`_is_archaeology`) instead of utility -- the
    detector half of T-2988's purpose test. Private symbols are exempt
    (T-2988's own measured baseline: 98% of private functions already
    carry a docstring at public-tier rates, and the tier-4 bar for
    private code is deliberately lower -- flagging private archaeology
    too would relitigate that same over-documentation on a tier the
    project explicitly wants LESS ceremony on, not more).

    Re-parses every `.py` file under `root` via `frob.lang.parse_file`
    (docstring text is not retained on `frob.graph`'s `SymbolRecord`, only
    its digest -- see `frob.graph.digest.doc_digest`), so this needs no
    `GraphSnapshot` at all -- same root-only self-check posture as
    `waive011_violations`. `_collect_source_files` restricts the walk to
    real source paths the same way every other whole-repo gate does.
    """
    violations: list[Violation] = []
    for path in _collect_source_files(root, "python"):
        parsed = parse_file(path, expect_heterogeneous=True)
        if parsed.is_err:
            continue
        # `ParsedFile.path` (`frob.lang._display_path`) is only
        # repo-relative when `root` happens to equal `Path.cwd()`; a gate
        # walking an arbitrary `root` (a test's `tmp_path`, a non-cwd
        # worktree) must derive the relative path itself instead.
        try:
            rel = path.relative_to(root).as_posix()
        except ValueError:
            rel = parsed.danger_ok.path
        for sym in parsed.danger_ok.symbols:
            if not sym.public or not sym.doc_text:
                continue
            if not _is_archaeology(sym.doc_text):
                continue
            line = sym.span[0]
            symref = f"{rel}::{sym.qualname}"
            _log.debug("DOCARCH001: candidate %s", symref)
            violations.append(_docarch001_violation(file=rel, line=line, symref=symref))
    return tuple(violations)
