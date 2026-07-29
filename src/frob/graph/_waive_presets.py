# frob:waive INV006 reason="T-1176: this module's docstring describes its own \
# already-implemented preset-table behavior in design-rationale prose (verifiable by \
# reading the code it annotates), not a separate cross-module contract needing its own \
# tracked invariant -- same disposition as the calibration-batch class this file's own \
# WAIVE_PRESETS['split-carried-prose'] documents, written inline rather than through \
# that preset to avoid a confusing self-reference"
"""Named `frob:waive` reason presets (T-1176).

A `frob:waive RULE preset="<name>"` directive still names the rule and
still carries an explicit, per-site directive -- only the REASON prose
deduplicates, via this one table, instead of every site hand-writing its
own copy of the same boilerplate paragraph (the NO DUPLICATION principle
applied to comment prose, not just code). `docs/modules/gates.md`'s
"Waiver presets" section is the documented, human-facing mirror of this
table; `tests/test_gates.py::TestWaivePresets` is the drift-lock that
keeps the two in sync -- this module is the single reference source a
`preset=` attribute resolves against, not a second normative copy.

Adding a preset: add an entry here, add the matching row to
`docs/modules/gates.md#waiver-presets-t-1176`, and the drift-lock test
enforces they never diverge. Removing one is a breaking change for every
site that still cites it -- migrate those sites' directives back to an
inline `reason=...` (or a different preset) in the same change.
"""

from __future__ import annotations

__all__ = ["WAIVE_PRESETS", "resolve_preset"]

# frob:doc docs/modules/gates.md#waiver-presets-t-1176
WAIVE_PRESETS: dict[str, str] = {
    # T-0585's INV006 "first-turn-on pool" calibration batch: an
    # exclusivity-vocabulary hit that is source-level design-rationale/
    # scope-cut prose (a docstring or comment describing already-
    # implemented internal behavior, verifiable by reading the code it
    # annotates) rather than a separate cross-module contract needing its
    # own tracked invariant. Carried verbatim by every T-0585-lineage site
    # (0abc4e3a lineage) -- the site's own file/line already identifies
    # which module the finding is in, so the reason text no longer needs
    # to repeat the filename the way the pre-T-1176 per-site copies did.
    "split-carried-prose": (
        "INV006 first-turn-on pool (T-0585 lineage): this exclusivity-"
        "vocabulary hit is source-level design-rationale/scope-cut prose "
        "(a docstring or comment describing already-implemented internal "
        "behavior, verifiable by reading the code it annotates) rather "
        "than a separate cross-module contract needing its own tracked "
        "invariant; disposed as a calibration batch, not claim-by-claim"
    ),
    # The T-1099 REF002 split-fragment family: a module split out of a
    # package's own `__init__.py`/dispatch table by design, imported only
    # by that dispatch table -- the same package-split shape every
    # sibling `_*.py` submodule in that package has, so a second consumer
    # would not be a genuine second consumer.
    "split-fragment": (
        "a split submodule of its owning package's own dispatch table, "
        "imported only by that package's __init__.py by design -- the "
        "same package-split structure every sibling submodule in that "
        "package has, so a second consumer would not be genuine"
    ),
}


# frob:doc docs/modules/gates.md#waiver-presets-t-1176
def resolve_preset(name: str) -> str | None:
    """The reason text `preset=name` resolves to, or `None` if `name` is
    not a recognized preset (the caller turns that into a malformed-
    directive error -- an unknown preset is never silently accepted)."""
    return WAIVE_PRESETS.get(name)
