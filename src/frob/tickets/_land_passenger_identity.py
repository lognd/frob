"""T-4474: directive-IDENTITY comparison for `_land._check_passenger_
tickets`.

T-2082 fixed the false-negative half of the passenger check (a passenger
whose line text was physically added must refuse) by requiring an exact
line-for-line multiset match between a directive's added and removed
occurrences before exempting it as a "pure relocation". That exactness
turned out to be too strict: five 2026-09-13 lands (T-4443, T-4465,
T-4448, T-4179, T-4463's sibling) refused because a genuinely pre-existing
`frob:ticket <id>` directive was merely MOVED, RE-WRAPPED to a different
column width, or carried along an ARCH001-style symbol extraction --
none of which change the directive's own semantic content, only its
surrounding whitespace/indentation. Comparing raw line text treats that
whitespace difference exactly like a real code change and refuses.

This module normalizes a directive line to a width/indentation-
independent IDENTITY string before `_land`'s multiset comparison runs, so
a moved-and-rewrapped directive still compares equal to its pre-move
self, while a directive whose actual WORDING changed (T-2082's own
`test_relocation_that_also_edits_the_directive_line_still_refuses` case:
"# frob:ticket X" reworded to "# see frob:ticket X for context") still
does not -- normalization only erases whitespace, never words."""

from __future__ import annotations

import re

# frob:waive REF002 reason="fresh T-4474 split out of _land.py's own \
# _passenger_ids_from_line_buckets/_directive_ticket_ids_in_diff pair; _land.py is its \
# one and only intentional anchor, matching the _lock_msvcrt.py/T-3577 precedent for a \
# small single-purpose helper split"

#: A directive line's trailing continuation marker (this repo's
#: over-width-directive convention: a line ending in a backslash,
#: optionally preceded by whitespace, continues on the next physical
#: line). Stripped before comparison so a directive re-wrapped across a
#: different number of physical lines still normalizes identically to an
#: un-wrapped (or differently-wrapped) prior form of the SAME line.
_CONTINUATION_SUFFIX_RE = re.compile(r"\s*\\\s*$")

#: Leading comment-delimiter run (`#`, `//`, `/*`, a continuation `*`),
#: plus any whitespace around it -- stripped so the same directive text
#: compares equal whether it was reached via a `#`-comment file or a
#: `//`-comment one, and so a changed INDENTATION depth (the common
#: symptom of moving a directive into a differently-nested scope) never
#: registers as a content difference.
_COMMENT_LEADER_RE = re.compile(r"^\s*(?:#+|//+|/\*+|\*+)\s*")

#: Any run of internal whitespace, collapsed to a single space -- the
#: actual re-wrap fix: reflowing a directive to a different column width
#: changes how much whitespace sits between words without changing the
#: words themselves.
_WHITESPACE_RUN_RE = re.compile(r"\s+")


# frob:doc docs/modules/tickets-landing.md#passenger-ticket-disclosure-t-1618
def normalize_directive_text(text: str) -> str:
    """Collapse one directive-bearing source line to a width- and
    indentation-independent identity string (T-4474): strip a trailing
    backslash line-continuation marker (`_CONTINUATION_SUFFIX_RE`), strip
    the leading comment-delimiter run (`_COMMENT_LEADER_RE`), then
    collapse every internal whitespace run to a single space
    (`_WHITESPACE_RUN_RE`) and trim the ends. Two directive lines that
    normalize to the same string are the SAME directive regardless of
    which file they sit in, how deeply indented they are, or how many
    columns wide the surrounding code wraps them to; two that normalize
    differently differ in actual wording (or in a genuinely distinct
    directive), never merely in whitespace."""
    without_continuation = _CONTINUATION_SUFFIX_RE.sub("", text)
    without_leader = _COMMENT_LEADER_RE.sub("", without_continuation)
    return _WHITESPACE_RUN_RE.sub(" ", without_leader).strip()


# frob:doc docs/modules/tickets-landing.md#passenger-ticket-disclosure-t-1618
def classify_directive_ids(
    added_lines: dict[str, list[str]], removed_lines: dict[str, list[str]]
) -> tuple[frozenset[str], frozenset[str]]:
    """Split the ticket ids named in `added_lines` (`_land`'s per-id
    added/removed diff-line buckets) into `(new_ids, moved_ids)` by
    comparing NORMALIZED directive identity (`normalize_directive_text`)
    rather than raw line text (T-4474, replacing T-2082's exact-text
    rule): an id whose normalized added-side multiset is not covered by
    its normalized removed-side multiset (a strictly larger count, or any
    normalized string present on the added side but absent from the
    removed side) is genuinely NEW code and belongs in `new_ids`; an id
    whose normalized multisets match exactly on both sides is a pure
    relocation/rewrap of a directive that already existed in the base
    tree and belongs in `moved_ids` instead. Still a MULTISET comparison,
    not a set one (T-2082's own posture, preserved): two copies of the
    same directive relocating is a real accounting fact, not noise, and
    one copy added alongside one genuine relocation must still register
    as one new occurrence."""
    new_ids: set[str] = set()
    moved_ids: set[str] = set()
    for directive_id, adds in added_lines.items():
        removes = removed_lines.get(directive_id, [])
        # frob:waive PERF004 reason="adds/removes are this directive_id's own small \
        # distinct per-id line list (typically 1-2 entries), not a shared collection \
        # re-sorted identically across iterations -- same posture as the identical \
        # PERF004 waiver on _land.py's own _passenger_ids_from_line_buckets predecessor"
        norm_adds = sorted(normalize_directive_text(line) for line in adds)
        norm_removes = sorted(normalize_directive_text(line) for line in removes)
        if len(norm_adds) > len(norm_removes) or norm_adds != norm_removes:
            new_ids.add(directive_id)
        else:
            moved_ids.add(directive_id)
    return frozenset(new_ids), frozenset(moved_ids)


__all__ = ["classify_directive_ids", "normalize_directive_text"]
