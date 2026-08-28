"""CPLACE001/CPLACE002: T-2994's placement doctrine as a gate (T-3218).

T-2994's rule: TICKETS carry narrative (why we did it, what was measured,
what was rejected, the history); CODE and DOCS carry utility (what an
operator or developer needs to run it, what the rules mean, what the
failure modes are). This module is the enforcement half -- T-2987
(waiver-reason bloat), T-2988 (docstring standard) and T-3022 (docs bulk
migration) already own the respective migrations under the epic; this
ticket ships only the gate, so it does not land a first-day WARN flood
with nowhere to drain to (T-2994's own MIGRATION IS NOT THIS TICKET'S JOB
constraint).

`frob.gates._narrative_blocks` (NARR001, T-2993) already covers one slice
of this doctrine -- a `# T-####:` LED comment block over a line threshold
-- and is not duplicated here. What NARR001 does not cover, and what
T-2987's own finding plus T-3189's docs measurement both flagged as a
live gap, is:

  CPLACE001 -- a `frob:waive` directive's reason prose is NOT exempt from
  the same length discipline as ordinary narrative prose, even though
  `frob:ticket`/`frob:tests`/`frob:doc` (86% of all directives, almost all
  already single-line, per T-2987) stay exempt at any length as pure
  binding syntax. T-2987 found the blanket "frob: directives are exempt"
  position (as T-3189 first drafted it) too broad: a 20-line
  `frob:waive reason="..."` essay IS the narrative bloat T-2994 is about,
  not enforcement surface. NARR001 does not fire on this shape at all --
  it only matches blocks LED by a `# T-####:` line, and a `frob:waive`
  directive is led by `# frob:waive`, not a ticket id.

  CPLACE002 -- a ticket-id-citing paragraph in `docs/modules/**` outside a
  provenance context (a markdown table row, or one of the doctrinally
  exempt paths: changelog.d/, CHANGELOG.md, docs/decisions/, tickets/**)
  is a narrative-migration candidate for `frob narrative move`. A bare
  `(T-1234)`-shaped citation used as evidence-of-behaviour in a table row
  stays -- T-2994's doctrine explicitly allows a reference, only the
  elaborated STORY moves.

Both rules ship at WARN, same TICK011/T-2372 burn-then-promote ladder
NARR001 already uses: T-2987/T-3022 (the migrations) have not landed yet
at the time this gate ships, so an immediate ERROR would be exactly the
"gate fires 96 times on day one, gets waived away" failure T-2994 warned
against. Both are candidate-flagging heuristics, same posture as NARR001
-- the split between narrative and utility prose is a judgement call per
T-2994's own doctrine, not something a detector resolves unattended.

Deliberately NOT a substring/lexical match over raw comment text: CPLACE001
reuses `frob.graph.dsl.fold_comment_runs`, the SAME physical-line-count
primitive `frob fmt` (T-0441) already uses to canonicalize directive runs,
so "how many physical lines does this frob:waive directive span" is
computed identically here and in the canonicalizer, not re-derived by a
regex over concatenated text. An earlier draft of a similar detector
(elsewhere in this drive) matched raw substrings and false-fired on its
own done-report narrative; this module's own regression tests
(`test_cplace001_does_not_fire_on_prose_mentioning_frobwaive_by_name`)
guard against repeating that.
"""

from __future__ import annotations

import re
from pathlib import Path

from frob.gates._models import Severity, Violation
from frob.graph import fold_comment_runs
from frob.logging import get_logger

_log = get_logger(__name__)

__all__ = [
    "CPLACE001_WAIVE_REASON_LIMIT_LINES",
    "CPLACE002_NARRATIVE_WORD_LIMIT",
    "comment_placement_gate",
    "scan_cplace001_waive_reason_length",
    "scan_cplace002_docs_narrative",
]

# T-2987's own proposed threshold, adopted verbatim by T-3218: 2 lines is
# already generous relative to a compliant one-line summary-plus-pointer
# waiver, and sits well below the measured long tail (the 5 longest
# directives in the repo are waivers, 18-20 lines each) so the must-fire/
# must-stay-quiet fixtures land clearly on either side of it.
# frob:doc docs/guides/agent-playbook.md#7b-comment-placement-t-3218
CPLACE001_WAIVE_REASON_LIMIT_LINES = 2

# A bare provenance citation ("(T-1234)" inline, or a short attribution
# like "see T-1234 for why") is a handful of words; a paragraph doing
# real narrative work (T-2994's "why we arrived here, what a prior
# attempt got wrong") reads as ordinary prose sentences. 15 words is
# comfortably above a bare citation's word count and comfortably below a
# genuine narrative paragraph's, matching the shape of the must-fire/
# must-stay-quiet fixtures below.
# frob:doc docs/guides/agent-playbook.md#7b-comment-placement-t-3218
CPLACE002_NARRATIVE_WORD_LIMIT = 15

_TICKET_ID_RE = re.compile(r"\bT-\d{2,6}\b")
_WAIVE_LEAD_RE = re.compile(r"^frob:waive\b")
_TABLE_ROW_RE = re.compile(r"^\s*\|")
_HEADING_RE = re.compile(r"^\s*#")
_CODE_FENCE_RE = re.compile(r"^\s*```")

# T-2994's own doctrine: provenance is the point in these locations, so a
# ticket-id-citing paragraph there is never flagged by either rule.
_EXEMPT_PREFIXES = ("changelog.d/", "docs/decisions/", "tickets/")
_EXEMPT_FILES = ("CHANGELOG.md",)


def _is_provenance_exempt(rel: str) -> bool:
    """`True` when `rel` is one of T-2994's doctrinally-exempt provenance
    locations (changelog, decision records, the ticket queue itself) --
    neither CPLACE001 nor CPLACE002 ever fires there."""
    if rel in _EXEMPT_FILES:
        return True
    return any(rel.startswith(prefix) for prefix in _EXEMPT_PREFIXES)


# frob:doc docs/guides/agent-playbook.md#7b-comment-placement-t-3218
# frob:tests \
# tests/gates/test_comment_placement.py::TestCplace001::test_must_fire_long_waive_reason
# frob:tests \
# tests/gates/test_comment_placement.py::TestCplace001::test_must_stay_quiet_ordinary_o\
# ne_line_waive
# frob:tests \
# tests/gates/test_comment_placement.py::TestCplace001::test_must_stay_quiet_frob_ticke\
# t_directive_any_length
# frob:tests \
# tests/gates/test_comment_placement.py::TestCplace001::test_does_not_fire_on_prose_men\
# tioning_frobwaive_by_name
def scan_cplace001_waive_reason_length(
    path: Path, text: str, *, limit: int = CPLACE001_WAIVE_REASON_LIMIT_LINES
) -> tuple[Violation, ...]:
    """Every `frob:waive` directive in `text` (a `src/**/*.py` file) whose
    logical comment run spans more than `limit` physical lines, as
    `CPLACE001` violations. Pure function of file content, matching
    `scan_narrative_blocks`'s own no-filesystem-access shape so fixtures
    can call it directly. Uses `fold_comment_runs`'s physical-line-count
    return -- the same primitive `frob fmt` (T-0441) canonicalizes
    directive runs with -- rather than a raw-text length guess, so a
    `frob:waive` directive is identified by matching the DSL's own
    `frob:waive` directive-start syntax on the FOLDED logical line, never
    by a substring search over unfolded comment text."""
    rel = str(path)
    if _is_provenance_exempt(rel):
        return ()
    lines = text.splitlines()
    entries: list[tuple[int, str, str, int]] = []
    for i, raw in enumerate(lines):
        stripped = raw.lstrip(" \t")
        if not stripped.startswith("#"):
            continue
        content = stripped[1:]
        if content.startswith(" "):
            content = content[1:]
        entries.append((i, content, "", 0))
    violations: list[Violation] = []
    for logical_text, lineno, _src, count in fold_comment_runs(entries):
        if not _WAIVE_LEAD_RE.match(logical_text.strip()):
            continue
        if count <= limit:
            continue
        violations.append(
            Violation(
                rule="CPLACE001",
                severity=Severity.WARN,
                file=rel,
                line=lineno + 1,
                message=(
                    f"CPLACE001: {count}-line frob:waive directive (over "
                    f"the {limit}-line cap) -- move the justification into "
                    "the referenced ticket, leaving a one-line summary "
                    "plus ticket pointer in the directive (T-2987/T-2994)"
                ),
            )
        )
    return tuple(violations)


def _iter_paragraphs(lines: list[str]) -> list[tuple[int, int]]:
    """Contiguous `(start, end)` 0-indexed line ranges (inclusive) of
    plain prose paragraphs in `lines` -- non-blank lines that are not a
    markdown table row, a heading, or inside a fenced code block. A table
    row is provenance by construction (T-2994) so it is never grouped
    into a scanned paragraph."""
    paras: list[tuple[int, int]] = []
    i = 0
    n = len(lines)
    in_fence = False
    while i < n:
        if _CODE_FENCE_RE.match(lines[i]):
            in_fence = not in_fence
            i += 1
            continue
        if (
            in_fence
            or not lines[i].strip()
            or _TABLE_ROW_RE.match(lines[i])
            or _HEADING_RE.match(lines[i])
        ):
            i += 1
            continue
        start = i
        j = i
        while (
            j < n
            and lines[j].strip()
            and not _TABLE_ROW_RE.match(lines[j])
            and not _HEADING_RE.match(lines[j])
            and not _CODE_FENCE_RE.match(lines[j])
        ):
            j += 1
        paras.append((start, j - 1))
        i = j
    return paras


# frob:doc docs/guides/agent-playbook.md#7b-comment-placement-t-3218
# frob:tests \
# tests/gates/test_comment_placement.py::TestCplace002::test_must_fire_long_narrative_p\
# aragraph
# frob:tests \
# tests/gates/test_comment_placement.py::TestCplace002::test_must_stay_quiet_table_row_\
# citation
# frob:tests \
# tests/gates/test_comment_placement.py::TestCplace002::test_must_stay_quiet_short_attr\
# ibution
# frob:tests \
# tests/gates/test_comment_placement.py::TestCplace002::test_must_stay_quiet_exempt_path
def scan_cplace002_docs_narrative(
    path: Path, text: str, *, word_limit: int = CPLACE002_NARRATIVE_WORD_LIMIT
) -> tuple[Violation, ...]:
    """Every ticket-id-citing prose paragraph in `text` (a
    `docs/modules/**/*.md` file) outside a provenance table row, longer
    than `word_limit` words, as `CPLACE002` violations. A bare citation
    like `(T-1234)` or a short `see T-1234` attribution stays quiet by
    construction (too few words to cross `word_limit`); the flag is a
    migration CANDIDATE for `frob narrative move`, not a verdict -- same
    judgement-call posture NARR001 already documents for T-2994's split."""
    rel = str(path)
    if _is_provenance_exempt(rel):
        return ()
    lines = text.splitlines()
    violations: list[Violation] = []
    for start, end in _iter_paragraphs(lines):
        para_text = " ".join(lines[start : end + 1])
        if not _TICKET_ID_RE.search(para_text):
            continue
        words = para_text.split()
        if len(words) <= word_limit:
            continue
        violations.append(
            Violation(
                rule="CPLACE002",
                severity=Severity.WARN,
                file=rel,
                line=start + 1,
                message=(
                    f"CPLACE002: {len(words)}-word ticket-citing paragraph "
                    "outside a provenance table/section -- if this is "
                    "narrative (why/history) rather than current-behavior "
                    "utility, move it into the ticket with "
                    "`frob narrative move` (T-2994/T-3022)"
                ),
            )
        )
    return tuple(violations)


# frob:doc docs/guides/agent-playbook.md#7b-comment-placement-t-3218
# frob:tests \
# tests/gates/test_comment_placement.py::TestCommentPlacementGate::test_fires_across_bo\
# th_surfaces
def comment_placement_gate(root: Path) -> tuple[Violation, ...]:
    """CPLACE001 (src `frob:waive` reason length) and CPLACE002 (docs
    ticket-narrative placement) over every tracked file under `root`
    (T-3218). Reads files directly, same lightweight repo-wide-scan
    posture `narrative_blocks_gate` and `_exclude_hazard.py` already use."""
    from frob.gates._tracked_files import tracked_files as _shared_tracked_files

    tracked = _shared_tracked_files(root, caller="comment_placement_gate")
    violations: list[Violation] = []
    for rel in tracked:
        full = root / rel
        if rel.startswith("src/") and rel.endswith(".py"):
            try:
                text = full.read_text(encoding="utf-8")
            except OSError:
                continue
            violations.extend(scan_cplace001_waive_reason_length(Path(rel), text))
        elif rel.startswith("docs/modules/") and rel.endswith(".md"):
            try:
                text = full.read_text(encoding="utf-8")
            except OSError:
                continue
            violations.extend(scan_cplace002_docs_narrative(Path(rel), text))
    _log.debug(
        "comment_placement: %d CPLACE001/CPLACE002 violation(s) under %s",
        len(violations),
        root,
    )
    return tuple(violations)
