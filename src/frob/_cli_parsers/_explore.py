# frob:ticket T-1238
"""CLI parser builder for the `frob explore` verb group (T-1238): regroups
the navigation porcelain (`map`/`outline`/`xref`/`docs-search`) under one
intent-named subcommand instead of four top-level entries, per the
`docs/design/cli-regrouping.md` taxonomy. The four members' standalone
top-level forms keep working unchanged (see `outline_runner`/`map_runner`/
`xref_runner`/`docs_runner`'s own T-1238 notes) -- this is a second
entry point onto the same argument dests, not a replacement.

T-4520: `map`/`outline`/`xref` are declared as inline `add_argument` calls
by their flat twins (`_add_map_parser`/`_add_outline_parser`/
`_add_xref_parser`, `_core.py`) rather than a `_populate_*` helper this
module could import and call a second time -- `_core.py` is out of this
ticket's scope to split one out of. Instead of hand-redeclaring the same
flags here (the exact divergence risk this ticket exists to close),
`_mirror_subparser` reuses the flat parser objects `_root._build_parser`
has already built by the time it calls `_add_explore_parser` (see
`_root._add_analysis_subparsers`'s ordering comment): the group leaf IS
the flat parser, so a flag added to the flat twin is visible through the
group with no edit here, ever. `docs-search` (previously the one member
with no flat twin) now has one (`_add_docs_search_parser`, this module)
and is mirrored the same way, making the mapping total."""

from __future__ import annotations


# frob:ticket T-4520
def _mirror_subparser(dest_sub, flat_sub, name: str) -> None:
    """Register `flat_sub`'s already-built `name` leaf onto `dest_sub` by
    reusing the identical `ArgumentParser` instance instead of building a
    second one (T-4520) -- argparse's own `_SubParsersAction.add_parser`
    only ever constructs a NEW parser, so true reuse means writing
    directly into its `choices`/`_choices_actions` bookkeeping, the same
    private surface `_root._collect_option_strings` already reads (T-0578)
    -- `flat_sub` must already have `name` registered (`_root.py`'s
    `_build_parser` ordering guarantees this for every caller here)."""
    parser = flat_sub.choices[name]
    dest_sub.choices[name] = parser
    for act in flat_sub._choices_actions:  # noqa: SLF001
        if act.dest == name:
            dest_sub._choices_actions.append(type(act)(name, (), act.help))  # noqa: SLF001
            break


# frob:ticket T-1238
def _add_explore_parser(sub) -> None:
    """Register the `frob explore` subcommand group and its four
    subcommands (`map`, `outline`, `xref`, `docs-search`), each mirroring
    (T-4520, `_mirror_subparser`) its standalone top-level counterpart's
    already-built `ArgumentParser` instance -- identical flags and
    dispatch dest by construction, not by manual copying."""
    explore_p = sub.add_parser(
        "explore",
        help="navigation: map/outline/xref/docs-search grouped under one verb (T-1238)",
    )
    explore_sub = explore_p.add_subparsers(dest="explore_command")

    for name in ("map", "outline", "xref", "docs-search"):
        _mirror_subparser(explore_sub, sub, name)


# frob:ticket T-4520
def _add_docs_search_parser(sub) -> None:
    """Register the flat top-level `frob docs-search` verb (T-4520): the
    standalone twin of `frob explore docs-search` -- it used to be the
    one `explore` member with no flat form, which made the group-to-flat
    mapping non-total. Shares `_populate_docs_search_args` with the group
    leaf (`_add_explore_parser`, via `_mirror_subparser`) so the flag
    list is declared exactly once."""
    search_p = sub.add_parser(
        "docs-search",
        help="full-text search through docs/ -- also available as "
        "`frob explore docs-search` (T-1238)",
    )
    _populate_docs_search_args(search_p)


# frob:ticket T-4520
def _populate_docs_search_args(search_p) -> None:
    """Add `docs-search`'s arguments onto `search_p` (T-4520) -- shared by
    the flat `frob docs-search` verb and (indirectly, via
    `_mirror_subparser`'s object reuse) the `frob explore docs-search`
    group leaf, so neither duplicates the flag list."""
    search_p.add_argument("docs_path", metavar="path")
    search_p.add_argument("docs_search", metavar="query")
    search_p.add_argument("--json", dest="docs_json", action="store_true")
