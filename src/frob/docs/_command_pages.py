"""Generate a minimal `docs/commands/<verb>.md` page straight from the live
argparse tree (T-4702).

The ticket's own instruction: prefer generating docs/commands/ from the
argparse tree over hand-writing more files, and wire it so the docs
cannot drift again silently. This module is that generator -- it produces
a small, honest page (title, help summary, usage line, flag list) for any
top-level verb that has none yet, rather than attempting to synthesize
the rich worked-examples/output-samples prose the 19 pre-existing,
hand-written pages carry (that content requires human judgment about
which examples are illustrative, not something argparse's own metadata
can produce). `sync_missing_command_pages` never overwrites an existing
file -- regenerating a hand-written page's prose is explicitly out of
scope for this mechanical pass; it only fills genuine gaps and reports
what it created, so `frob docs --sync-command-pages` is safe to re-run
after every CLI change without clobbering curated content."""

from __future__ import annotations

import argparse
from pathlib import Path

_DOCS_COMMANDS_DIR = Path("docs/commands")


# frob:ticket T-4702
# frob:tests \
# tests/unit/test_docs_commands_coverage.py::TestLiveSurfaceMatchesDocsCommands::test_every_live_verb_has_a_doc_page  # noqa: E501
# frob:doc docs/modules/app.md#frobdocs_command_pages-t-4702
def live_top_level_verbs(
    parser: argparse.ArgumentParser,
) -> dict[str, tuple[argparse.ArgumentParser, str]]:
    """Every top-level verb NOT suppressed from `frob --help` (i.e. not on
    a T-4690-style deprecation sunset clock), mapped to its own
    `(sub_parser, help_text)` pair -- the "final surface" T-4702's own
    acceptance criterion means by "every top-level verb". `help_text`
    comes from the PARENT's choice pseudo-action (the one-line summary
    `frob --help` itself prints), since a leaf subparser has no
    `description` of its own unless one was explicitly set. A verb
    registered only for `--help` discovery with dispatch bypassing this
    tree entirely (`bind`/`agent`/`worktree`/`whereis`/`run`/`build`,
    T-0355's own precedent) still has a real subparser here and is
    included: its --help output is the only argparse-derived metadata
    this generator has for it, and it is still a live, undeprecated
    verb."""
    sub_action = next(
        a
        for a in parser._actions
        if isinstance(a, argparse._SubParsersAction)  # noqa: SLF001
    )
    live_actions = {
        a.dest: a
        for a in sub_action._choices_actions  # noqa: SLF001
        if a.help != argparse.SUPPRESS
    }
    return {
        name: (sub_action.choices[name], action.help or "")
        for name, action in live_actions.items()
    }


# frob:ticket T-4702
# frob:tests \
# tests/unit/test_docs_commands_coverage.py::TestLiveSurfaceMatchesDocsCommands::test_every_doc_page_names_a_registered_verb  # noqa: E501
# frob:doc docs/modules/app.md#frobdocs_command_pages-t-4702
def all_registered_verbs(parser: argparse.ArgumentParser) -> frozenset[str]:
    """Every top-level name argparse itself knows about -- LIVE and
    deprecated-but-still-dispatchable alike (a suppressed choice, e.g.
    `cycle`/`gitlog`, is still a real `_SubParsersAction` entry through
    its sunset window). Used to tell "a docs/commands page documents a
    deprecation notice for a spelling still on its sunset clock" apart
    from "a docs/commands page documents a spelling argparse has never
    heard of" -- only the second is a genuine T-4702 coverage finding."""
    sub_action = next(
        a
        for a in parser._actions
        if isinstance(a, argparse._SubParsersAction)  # noqa: SLF001
    )
    return frozenset(sub_action.choices)


# frob:ticket T-4702
# frob:tests \
# tests/unit/test_docs_commands_coverage.py::TestSyncMissingCommandPages::test_generate_command_page_renders_help_text_and_usage  # noqa: E501
# frob:doc docs/modules/app.md#frobdocs_command_pages-t-4702
def generate_command_page(
    verb: str, sub_parser: argparse.ArgumentParser, help_text: str
) -> str:
    """Render one minimal `docs/commands/<verb>.md` page -- a title, the
    one-line `help_text` `frob --help` itself prints for this verb, the
    real `--help`-formatted usage block, and a generated-stub footer.
    Mechanical, not prose: this is deliberately a STUB a human can
    enrich later, not a substitute for the worked examples the 19
    pre-existing, hand-written pages already carry."""
    lines = [f"# frob {verb}", ""]
    lines.append(help_text or f"`frob {verb}` -- see usage below.")
    lines.append("")
    lines.append("## Usage")
    lines.append("")
    lines.append("```")
    lines.append(sub_parser.format_usage().strip())
    lines.append("```")
    lines.append("")
    lines.append(
        "*Generated from the live argparse tree (T-4702, "
        "`frob docs --sync-command-pages`) -- a stub; enrich with worked "
        "examples as this verb's real usage patterns become clear.*"
    )
    lines.append("")
    return "\n".join(lines)


# frob:ticket T-4702
# frob:tests \
# tests/unit/test_docs_commands_coverage.py::TestSyncMissingCommandPages::test_sync_writes_only_missing_pages_and_never_overwrites  # noqa: E501
# frob:doc docs/modules/app.md#frobdocs_command_pages-t-4702
def sync_missing_command_pages(
    parser: argparse.ArgumentParser, docs_dir: Path = _DOCS_COMMANDS_DIR
) -> tuple[str, ...]:
    """Write a generated stub page for every live top-level verb that has
    no `docs/commands/<verb>.md` yet -- never overwrites an existing
    file. Returns the sorted tuple of verb names it actually wrote (for
    `frob docs --sync-command-pages`'s own summary line)."""
    docs_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []
    for verb, (sub_parser, help_text) in sorted(live_top_level_verbs(parser).items()):
        page_path = docs_dir / f"{verb}.md"
        if page_path.exists():
            continue
        page_path.write_text(generate_command_page(verb, sub_parser, help_text))
        written.append(verb)
    return tuple(written)
