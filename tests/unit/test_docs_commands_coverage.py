"""T-4702 (regenerate docs/commands from the final CLI surface): the
positive-control coverage test -- walks the live argparse tree and
asserts every top-level verb has a docs/commands entry AND every
docs/commands entry names a live verb, in BOTH directions (a planted
verb with no doc, and a planted doc with no verb, must each fail)."""

from __future__ import annotations

from pathlib import Path

from frob.docs._command_pages import (
    all_registered_verbs,
    generate_command_page,
    live_top_level_verbs,
    sync_missing_command_pages,
)

_DOCS_COMMANDS_DIR = Path(__file__).resolve().parents[2] / "docs" / "commands"

# Pages under docs/commands/ that document a CONCEPT, not one live
# top-level verb by that exact name -- excluded from the 1:1 name match
# this coverage test otherwise enforces.
_NON_VERB_DOC_STEMS = frozenset({"cli-vocabulary"})

# Verbs dispatched entirely by raw argv (T-4759's own `run`/`build`
# precedent, mirroring `bind`/`agent`) with NO subparser registered at
# all -- argparse has no record of them whatsoever, so they can never be
# confirmed "live" from the parser tree the way every other verb here
# is. Their docs/commands page is real and hand-maintained; excluded
# from both directions of this coverage test for the same reason
# `_NON_VERB_DOC_STEMS` is.
_RAW_DISPATCH_ONLY_VERBS = frozenset({"run"})


def _missing_docs(
    verb_names: frozenset[str], doc_stems: frozenset[str]
) -> frozenset[str]:
    """Live verbs with no `docs/commands/<verb>.md` -- the direction
    T-4702 acceptance[1]'s "every top-level verb has a docs/commands
    entry" half checks."""
    return verb_names - doc_stems - _RAW_DISPATCH_ONLY_VERBS


def _orphaned_docs(
    registered_verbs: frozenset[str], doc_stems: frozenset[str]
) -> frozenset[str]:
    """`docs/commands/*.md` pages naming a verb argparse has NEVER heard
    of -- the direction T-4702 acceptance[1]'s "every docs/commands
    entry names a live verb" half checks. Compared against EVERY
    registered name (live and deprecated-but-still-dispatchable alike,
    `all_registered_verbs`), not just the live subset `_missing_docs`
    uses: a page documenting a deprecation notice for a spelling still
    on its T-4690 sunset clock (`cycle`/`gitlog`/`map`/...) is a real,
    correct page, not an orphan -- only a name argparse has genuinely
    never registered is a finding here."""
    return doc_stems - registered_verbs - _NON_VERB_DOC_STEMS - _RAW_DISPATCH_ONLY_VERBS


# frob:ticket T-4702
class TestLiveSurfaceMatchesDocsCommands:
    """T-4702 acceptance[1]: the real, current `frob` argparse tree
    against the real, current `docs/commands/` directory -- both
    directions must be empty."""

    def test_every_live_verb_has_a_doc_page(self) -> None:
        from frob._cli_parsers._root import _build_parser

        verb_names = frozenset(live_top_level_verbs(_build_parser()))
        doc_stems = frozenset(p.stem for p in _DOCS_COMMANDS_DIR.glob("*.md"))
        missing = _missing_docs(verb_names, doc_stems)
        assert not missing, (
            f"live verb(s) with no docs/commands page: {sorted(missing)}"
        )

    def test_every_doc_page_names_a_registered_verb(self) -> None:
        from frob._cli_parsers._root import _build_parser

        registered = all_registered_verbs(_build_parser())
        doc_stems = frozenset(p.stem for p in _DOCS_COMMANDS_DIR.glob("*.md"))
        orphaned = _orphaned_docs(registered, doc_stems)
        assert not orphaned, (
            f"docs/commands page(s) naming an unknown verb: {sorted(orphaned)}"
        )


# frob:ticket T-4702
class TestAssertionFiresInBothDirections:
    """T-4702's own required positive control: "plant one of each in the
    test fixture to prove the assertion fires in both directions" -- a
    verb with no doc, and a doc with no verb, each synthetic and
    independent of the real repo state above."""

    def test_planted_verb_with_no_doc_is_caught(self) -> None:
        verb_names = frozenset({"check", "ticket", "planted_verb_no_doc"})
        doc_stems = frozenset({"check", "ticket"})
        missing = _missing_docs(verb_names, doc_stems)
        assert missing == frozenset({"planted_verb_no_doc"})

    def test_planted_doc_with_no_verb_is_caught(self) -> None:
        registered = frozenset({"check", "ticket"})
        doc_stems = frozenset({"check", "ticket", "planted_doc_no_verb"})
        orphaned = _orphaned_docs(registered, doc_stems)
        assert orphaned == frozenset({"planted_doc_no_verb"})


# frob:ticket T-4702
class TestSyncMissingCommandPages:
    """`frob docs --sync-command-pages`'s own generator (T-4702): a stub page
    is written for a verb with none, an existing hand-written page is never
    touched, and the written page's content is a real render of that verb's
    live `--help` text, not a placeholder-only file."""

    def test_generate_command_page_renders_help_text_and_usage(self) -> None:
        from frob._cli_parsers._root import _build_parser

        parser = _build_parser()
        sub_parser, _help_text = live_top_level_verbs(parser)["check"]
        page = generate_command_page("check", sub_parser, "run the gate suite")
        assert "# frob check" in page
        assert "run the gate suite" in page
        assert "## Usage" in page
        assert "usage: frob check" in page

    def test_sync_writes_only_missing_pages_and_never_overwrites(
        self, tmp_path: Path
    ) -> None:
        from frob._cli_parsers._root import _build_parser

        docs_dir = tmp_path / "commands"
        docs_dir.mkdir()
        preexisting = docs_dir / "check.md"
        preexisting.write_text("hand-written content, must survive")

        parser = _build_parser()
        written = sync_missing_command_pages(parser, docs_dir=docs_dir)

        assert "check" not in written, "must not overwrite an existing page"
        assert preexisting.read_text() == "hand-written content, must survive"
        assert written, "must write at least one genuinely missing page"
        for verb in written:
            assert (docs_dir / f"{verb}.md").exists()

    def test_matched_sets_produce_no_findings(self) -> None:
        """Negative control on the control itself: identical sets fire
        neither direction, so the two tests above are proven to be
        checking real mismatches, not always failing/always passing."""
        names = frozenset({"check", "ticket"})
        assert not _missing_docs(names, names)
        assert not _orphaned_docs(names, names)
