"""T-1134: INV006 split-assist -- when a module split moves exclusivity-
claim prose VERBATIM out of a file that already carries an INV006 waiver
or a bound `frob:invariant` edge, the destination file's own INV006
finding should name that source and offer its waiver/binding as a
fix-it, instead of making "remember the carried waiver" a human step
every split has had to redo by hand (T-1103/T-1107/T-1072/T-1077/T-1081/
T-1082 each paid this cost this drive; 3 more waivers hand-carried by the
coordinator on 2026-07-28 after the gates splits redded main).

Detection is a plain VERBATIM (whitespace-normalized) substring match on
the offending claim sentence -- a lighter-weight sibling of `frob.dup`'s
full clone pipeline (which is function/symbol-scoped and does not target
bare prose blocks/docstrings), same "exact match first" posture as
`frob.dup`'s own Type-1 rung. Deliberately narrow, disclosed (v1): only
an exact sentence match counts as "moved" -- a reworded paraphrase is not
detected. T-1135's refactor epic is expected to fold this in as a child
ticket at design time; `find_carried_waiver` is written to be reusable
outside INV006 specifically for that reason (its own T-1076 PII012
precedent has the identical (file, token)-keyed-allowlist-needs-a-new-
entry-on-move failure mode)."""
# frob:waive INV006 reason="module-docstring exclusivity-vocabulary hit is \
# source-level design-rationale prose describing this module's own already-implemented \
# detection behavior, verifiable by reading the code it annotates -- not a separate \
# cross-module contract needing its own tracked invariant, same calibration posture as \
# frob.tickets._new_gate_rule_acceptance's own T-0756 INV006 waiver"

from __future__ import annotations

from pathlib import Path

from frob.excludes import iter_files
from frob.gates.invariants import find_exclusivity_claim_sentences
from frob.graph import EdgeKind, GraphSnapshot


def _normalize_prose(text: str) -> str:
    """Collapse all whitespace/newlines in `text` to single spaces -- the
    shared comparison key both a claim sentence and a whole candidate
    file's text are folded through, so line-wrap reflow across a move
    (a docstring re-wrapped to a new file's column width) does not defeat
    verbatim detection."""
    return " ".join(text.split())


def _covering_waiver_directive_attrs(
    rel: str, snapshot: GraphSnapshot
) -> tuple[str, str | None] | None:
    """The `(reason, preset)` pair of a `frob:waive INV006` edge covering
    `rel`, or `None` if none exists -- mirrors `frob.gates._inv006_waived`'s
    own file-or-symbol-under-it matching rule without importing from
    `frob.gates` (would be circular; `_inv006_src_violations` imports THIS
    module, not the reverse). `preset` is `None` when the covering edge was
    written with a plain inline `reason=` (T-1176: a `preset=`-written
    edge's resolved reason still lands in `attrs["reason"]` at parse time,
    so `reason` is always present when this returns non-`None`; `preset`
    is only set when the site can be carried as a preset REFERENCE rather
    than a copy of its resolved text)."""
    for edge in snapshot.edges:
        if edge.kind != EdgeKind.WAIVE or edge.target != "INV006":
            continue
        if (
            edge.origin.rpartition(":")[0] == rel
            or edge.src == rel
            or edge.src.startswith(f"{rel}::")
        ):
            reason = edge.attrs.get("reason")
            if reason:
                return (reason, edge.attrs.get("preset"))
    return None


def _covering_invariant_id(rel: str, snapshot: GraphSnapshot) -> str | None:
    """The `INV-###` id of a `frob:invariant` edge anchored anywhere in
    `rel`, or `None` -- the OTHER way a file can already discharge INV006,
    mirrored from `frob.gates._inv006_src_violations`'s own check."""
    for edge in snapshot.edges:
        if edge.kind == EdgeKind.INVARIANT and edge.origin.rpartition(":")[0] == rel:
            return edge.target
    return None


# frob:doc docs/modules/gates.md#inv006-t-0408
# frob:ticket T-1134
# frob:tests tests/test_gates.py::TestInv006SplitAssist.test_finds_carried_waiver_for_verbatim_moved_claim  # noqa: E501
# frob:tests tests/test_gates.py::TestInv006SplitAssist.test_no_match_when_no_other_file_shares_the_claim  # noqa: E501
# frob:tests tests/test_gates.py::TestInv006SplitAssist.test_reworded_claim_is_not_detected_v1_disclosed  # noqa: E501
# frob:waive AFFECT001 reason="T-1371 only widens internal exception handling so one bad candidate file cannot abort the whole search; the documented detector behavior (verbatim sentence match against a covering waiver/invariant) is unchanged, so docs/modules/gates.md#inv006-t-0408 needs no update -- doc edits are owned by the concurrent T-1372 DOC006 drain, out of this ticket's scope"  # noqa: E501
# frob:waive ARCH001 reason="T-1371's EXHAUST001/002 fix wraps the pre-existing per-candidate body in one try/except (text/graph lookup surprise -> skip this candidate) -- boilerplate exception handling, not a new independently meaningful phase; splitting it out would just move the same lines behind an indirection"  # noqa: E501
def find_carried_waiver(
    root: Path,
    moved_text: str,
    *,
    exclude_rel: str,
    candidate_dirs: tuple[str, ...],
    candidate_suffixes: tuple[str, ...],
    snapshot: GraphSnapshot,
) -> tuple[str, str, str] | None:
    """Reusable T-1134 detector: does ANY exclusivity-claim sentence in
    `moved_text` (`find_exclusivity_claim_sentences`) appear VERBATIM
    (whitespace-normalized) in some OTHER file under `candidate_dirs`/
    `candidate_suffixes` (excluding `exclude_rel`) that already carries a
    covering INV006 waiver or bound `frob:invariant` edge?

    Returns `(source_rel, kind, fixit_text)` on the first match --
    `kind` is `"waiver"` or `"invariant"`, `fixit_text` is the literal
    directive text to carry (a `frob:waive INV006 reason="..."` line, or
    the source's `frob:invariant INV-###` id) -- or `None` if no claim in
    `moved_text` matches verbatim anywhere with a covering disposition.
    Reads every candidate file's CURRENT text fresh (no caching); cheap in
    practice because it only ever runs once per already-unwaived INV006
    finding (a handful per repo), never in a hot loop over every file."""
    sentences = tuple(
        _normalize_prose(s) for s in find_exclusivity_claim_sentences(moved_text)
    )
    if not sentences:
        return None
    for src_dir in candidate_dirs:
        src_root = root / src_dir
        if not src_root.is_dir():
            continue
        for suffix in candidate_suffixes:
            for path in iter_files(src_root, suffix=suffix):
                rel = path.relative_to(root).as_posix()
                if rel == exclude_rel:
                    continue
                try:
                    candidate_text = path.read_text(encoding="utf-8")
                except OSError:
                    continue
                try:
                    normalized_candidate = _normalize_prose(candidate_text)
                    if not any(s in normalized_candidate for s in sentences):
                        continue
                    covering = _covering_waiver_directive_attrs(rel, snapshot)
                except Exception:
                    # One candidate file's text/graph lookup being
                    # surprising must not abort the whole carried-waiver
                    # search over every OTHER candidate (EXHAUST001/
                    # EXHAUST002, T-1371) -- this detector's own docstring
                    # already tolerates "no match anywhere" as a normal
                    # `None` result, so skipping one bad candidate is the
                    # same outcome class.
                    continue
                if covering is not None:
                    reason, preset = covering
                    # T-1176/T-1177: carry a PRESET REFERENCE, not a copy
                    # of its resolved reason text, whenever the source
                    # itself was written with preset= -- the whole point
                    # of a preset is that the reason prose lives in one
                    # place; copying its resolved text at every carry
                    # site would silently recreate the exact duplication
                    # presets exist to remove.
                    fixit = (
                        f'frob:waive INV006 preset="{preset}"'
                        if preset is not None
                        else f'frob:waive INV006 reason="{reason}"'
                    )
                    return (rel, "waiver", fixit)
                inv_id = _covering_invariant_id(rel, snapshot)
                if inv_id is not None:
                    return (rel, "invariant", f"frob:invariant {inv_id}")
    return None


__all__ = ["find_carried_waiver"]
