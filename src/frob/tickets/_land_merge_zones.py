"""`frob ticket land` -- union-zone conflict-block resolution (T-1189).

Split out of `frob.tickets._land_merge` (T-1189, following the T-1186/
T-1188 verbatim-move pattern this drive established: `_sys.py`/`_inv.py`
in `frob.gates`): the registered append-only merge-zone machinery
(`_UnionZone`, the `_UNION_ZONES` registry, `_zone_for_path`, the
keyed-lines/append-only chunk unioners, and `_resolve_union_zone_conflicts`
itself) that resolves the three chronic conflict hotspots named in
docs/audits/coordination-churn.md item 3 without a manual merge step.
Zero caller-visible behavior change -- every moved function keeps its
original body, docstring, and `frob:ticket`/`frob:tests` directives
verbatim; `frob.tickets._land_merge` imports `_resolve_union_zone_conflicts`
back for its own use, and re-exports nothing else -- every other symbol
here (`_UnionZone`, `_zone_for_path`, `_union_keyed_chunks`, and friends)
is reached directly off this module by `tests/test_ticket_land.py`, same
module-attribute access pattern those tests already used before the move.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

import fnmatch
import re
from pathlib import Path

from typani.result import Ok, Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._models import LandError

_log = get_logger(__name__)


# frob:ticket T-1002
class _UnionZone:
    """One registered append-only merge zone (T-1002): a file glob plus how
    to union two sides' concurrent appends inside it instead of leaving a
    real git conflict. `kind="keyed_lines"` unions per-key chunks (each
    chunk is zero or more leading comment/blank lines followed by exactly
    one line matching `key_regex`) between `marker_start`/`marker_end`
    (docs/audits/coordination-churn.md item 3's `[gates.severity]` and
    `_KNOWN_GATE_RULES` hotspots); `kind="append_only"` treats the whole
    conflicted region as two blocks of pure appended text with no per-line
    key at all (the `docs/audits/*.md` remediation-log hotspot). Both kinds
    refuse (return `None`) rather than guess whenever the two sides
    genuinely disagree about the same key's value -- a true contradiction,
    not a concurrent append, and left for manual resolution same as before
    this ticket."""

    __slots__ = ("glob", "kind", "key_regex", "marker_start", "marker_end")

    def __init__(
        self,
        glob: str,
        kind: str,
        *,
        key_regex: re.Pattern[str] | None = None,
        marker_start: str | None = None,
        marker_end: str | None = None,
    ) -> None:
        """Register one union zone; see the class docstring for the field
        semantics."""
        self.glob = glob
        self.kind = kind
        self.key_regex = key_regex
        self.marker_start = marker_start
        self.marker_end = marker_end


# frob:ticket T-1002
# The three chronic conflict hotspots from docs/audits/coordination-churn.md
# item 3 (~8 occurrences, always resolved keep-both-chronological by hand
# before this ticket). Each source file carries `# frob-zone-start
# <name> T-1002` / `# frob-zone-end <name> T-1002` marker comments
# delimiting the exact region this registry is allowed to touch.
_UNION_ZONES: tuple[_UnionZone, ...] = (
    _UnionZone(
        "frob.toml",
        "keyed_lines",
        key_regex=re.compile(r"^(?P<key>[A-Za-z][A-Za-z0-9_-]*)\s*="),
        marker_start="# frob-zone-start gates.severity T-1002",
        marker_end="# frob-zone-end gates.severity T-1002",
    ),
    _UnionZone(
        "src/frob/gates/__init__.py",
        "keyed_lines",
        key_regex=re.compile(r'^\s*"(?P<key>[A-Za-z0-9_-]+)",\s*$'),
        marker_start="# frob-zone-start known-gate-rules T-1002",
        marker_end="# frob-zone-end known-gate-rules T-1002",
    ),
    _UnionZone("docs/audits/*.md", "append_only"),
)


def _zone_for_path(path: str) -> _UnionZone | None:
    """The registered `_UnionZone` matching `path`, or `None` if `path` is
    not a union zone at all (T-1002)."""
    for zone in _UNION_ZONES:
        if fnmatch.fnmatch(path, zone.glob):
            return zone
    return None


_CONFLICT_BLOCK_RE = re.compile(
    r"<<<<<<< [^\n]*\n"
    r"(?P<ours>.*?)"
    r"(?:\|\|\|\|\|\|\| [^\n]*\n.*?)?"
    r"=======\n"
    r"(?P<theirs>.*?)"
    r">>>>>>> [^\n]*\n",
    re.DOTALL,
)


def _chunk_by_key(
    text: str, key_regex: re.Pattern[str]
) -> list[tuple[str | None, str]]:
    """Split `text` into `(key, chunk_text)` pairs for `_union_keyed_chunks`
    (T-1002): each chunk is the run of lines up to and including the next
    line matching `key_regex` (so leading comments stay attached to the
    entry they annotate); any trailing lines with no further key match form
    one final `(None, ...)` chunk."""
    lines = text.splitlines(keepends=True)
    chunks: list[tuple[str | None, str]] = []
    buf: list[str] = []
    for line in lines:
        buf.append(line)
        m = key_regex.match(line)
        if m:
            chunks.append((m.group("key"), "".join(buf)))
            buf = []
    if buf:
        chunks.append((None, "".join(buf)))
    return chunks


# frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_keyed_lines_union_composes  # noqa: E501
# frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_keyed_lines_union_refuses  # noqa: E501
def _union_keyed_chunks(
    ours_text: str, theirs_text: str, key_regex: re.Pattern[str]
) -> str | None:
    """Union-merge two sides of a keyed-lines conflict block (T-1002):
    every key present on either side survives, in ours'-then-theirs'-new-
    only order; a key present on BOTH sides with differing chunk text is a
    true contradiction, not a concurrent append, and this returns `None`
    (refuse) rather than pick a side silently."""
    ours_chunks = _chunk_by_key(ours_text, key_regex)
    theirs_chunks = _chunk_by_key(theirs_text, key_regex)
    ours_by_key = {k: text for k, text in ours_chunks if k is not None}
    seen = set(ours_by_key)
    merged = [text for _, text in ours_chunks]
    theirs_only: list[str] = []
    for key, text in theirs_chunks:
        if key is None:
            continue
        if key in seen:
            if text.strip() != ours_by_key[key].strip():
                return None
            continue
        theirs_only.append(text)
        seen.add(key)
    return "".join(merged) + "".join(theirs_only)


def _union_append_only(ours_text: str, theirs_text: str) -> str:
    """Union-merge two sides of an append-only conflict block (T-1002): pure
    concatenation (ours' new content, then theirs') since there is no
    per-line key to reconcile by -- both sides only ever append whole
    sections (e.g. a `## Remediation log (...)` block). Identical sides
    (a no-op re-append) collapse to one copy."""
    if ours_text.strip() == theirs_text.strip():
        return ours_text
    return ours_text.rstrip("\n") + "\n\n" + theirs_text.lstrip("\n")


def _resolve_conflict_blocks(raw_text: str, zone: _UnionZone) -> str | None:
    """Resolve every `<<<<<<<`/`=======`/`>>>>>>>` conflict block in
    `raw_text` via `zone`'s union strategy, or `None` if any block is a true
    contradiction (`_union_keyed_chunks` refused) or (for a marker-delimited
    zone) any block falls outside the `marker_start`/`marker_end` region --
    a conflict there is not this zone's business to silently resolve, and
    the caller leaves the file conflicted exactly as before T-1002."""
    if zone.marker_start is not None:
        start = raw_text.find(zone.marker_start)
        end = raw_text.find(zone.marker_end or "")
        if start == -1 or end == -1 or end < start:
            return None
        zone_end = end + len(zone.marker_end or "")
        for m in _CONFLICT_BLOCK_RE.finditer(raw_text):
            if not (start <= m.start() and m.end() <= zone_end):
                return None

    def _resolve_one(m: re.Match[str]) -> str | None:
        ours, theirs = m.group("ours"), m.group("theirs")
        if zone.kind == "keyed_lines":
            assert zone.key_regex is not None
            return _union_keyed_chunks(ours, theirs, zone.key_regex)
        return _union_append_only(ours, theirs)

    out: list[str] = []
    cursor = 0
    for m in _CONFLICT_BLOCK_RE.finditer(raw_text):
        resolved = _resolve_one(m)
        if resolved is None:
            return None
        out.append(raw_text[cursor : m.start()])
        out.append(resolved)
        cursor = m.end()
    out.append(raw_text[cursor:])
    return "".join(out)


# frob:tests tests/test_ticket_land.py::TestUnionZoneMerge.test_resolve_stages  # noqa: E501
def _resolve_union_zone_conflicts(
    cwd: Path, conflicted: set[str]
) -> Result[frozenset[str], LandError]:
    """After a merge/squash leaves `conflicted` paths unmerged in `cwd`,
    resolve every one that matches a registered `_UNION_ZONE` via its union
    strategy and `git add` the result; returns whatever is STILL conflicted
    (union zones that refused a true contradiction, or were left alone
    because they are not a registered zone at all) for the caller to treat
    exactly as before T-1002 (fall through to the existing out-of-scope
    auto-resolve / hard-abort path)."""
    still_conflicted: set[str] = set()
    for path in sorted(conflicted):
        zone = _zone_for_path(path)
        if zone is None:
            still_conflicted.add(path)
            continue
        full_path = cwd / path
        if not full_path.exists():
            still_conflicted.add(path)
            continue
        raw_text = full_path.read_text(encoding="utf-8")
        resolved = _resolve_conflict_blocks(raw_text, zone)
        if resolved is None:
            _log.warning(
                "land: union-zone merge for %s left a true contradiction "
                "(or a conflict outside its registered marker region) -- "
                "leaving it conflicted for manual resolution",
                path,
            )
            still_conflicted.add(path)
            continue
        full_path.write_text(resolved, encoding="utf-8")
        add = run_argv(["git", "-C", str(cwd), "add", "--", path])
        if add.is_err or add.danger_ok.returncode != 0:
            still_conflicted.add(path)
            continue
        _log.info(
            "land: union-zone merge composed concurrent appends in %s "
            "(zone=%s) with no manual resolution",
            path,
            zone.glob,
        )
    return Ok(frozenset(still_conflicted))
