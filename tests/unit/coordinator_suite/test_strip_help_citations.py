"""`scripts/strip_help_citations.py` -- T-5134's help-string citation
remover.

WHY THIS EXISTS. `scripts/count_ticket_citations.py --scope help` only
measures; this module is the AST-precise rewrite that actually drove
the 274-citation count under `src/frob/_cli_parsers/` to zero. Its own
tests exercise `strip_citation_text` (the regex pipeline on a raw
source segment), `rewrite_file` (the AST splice), and `main` (the CLI
entry point), so a future regression in any of the three is caught
here rather than by hand-inspecting the next `--apply` diff.
"""

from __future__ import annotations

import importlib.util
import os
import textwrap
from pathlib import Path
from types import ModuleType

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _load_script(name: str) -> ModuleType:
    """Import `scripts/<name>.py` by path, same local technique
    `test_count_ticket_citations.py::_load_script` uses.
    """
    path = _SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_scripts_under_test.{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


strip_help_citations = _load_script("strip_help_citations")


class TestStripCitationText:
    """`strip_help_citations.strip_citation_text` -- the regex pipeline
    applied to one help-string source segment.
    """

    # frob:tests tests/unit/coordinator_suite/test_strip_help_citations.py::TestStripCitationText.test_bare_parenthetical_citation_is_removed  # noqa: E501
    # frob:tests scripts/strip_help_citations.py::strip_citation_text  # noqa: E501
    def test_bare_parenthetical_citation_is_removed(self) -> None:
        """A citation that is its own whole parenthetical aside
        disappears along with the now-empty parens.
        """
        out = strip_help_citations.strip_citation_text('"do widget things (T-1234)"')
        assert out == '"do widget things"'
        assert "T-1234" not in out

    # frob:tests tests/unit/coordinator_suite/test_strip_help_citations.py::TestStripCitationText.test_possessive_citation_keeps_the_sentence_grammatical  # noqa: E501
    # frob:tests scripts/strip_help_citations.py::strip_citation_text  # noqa: E501
    def test_possessive_citation_keeps_the_sentence_grammatical(self) -> None:
        """`T-1615's uniform auto-commit` must become `uniform
        auto-commit`, never the broken `'s uniform auto-commit`.
        """
        out = strip_help_citations.strip_citation_text(
            '"skip T-1615\'s uniform auto-commit"'
        )
        assert out == '"skip uniform auto-commit"'

    # frob:tests tests/unit/coordinator_suite/test_strip_help_citations.py::TestStripCitationText.test_no_citation_is_a_no_op  # noqa: E501
    # frob:tests scripts/strip_help_citations.py::strip_citation_text  # noqa: E501
    def test_no_citation_is_a_no_op(self) -> None:
        """A string with no `T-####` token is returned unchanged."""
        text = '"do widget things"'
        assert strip_help_citations.strip_citation_text(text) == text


class TestRewriteFile:
    """`strip_help_citations.rewrite_file` -- the AST-precise per-file
    rewrite, scoped to `help=`/`description=`/`epilog=` literals only.
    """

    # frob:tests tests/unit/coordinator_suite/test_strip_help_citations.py::TestRewriteFile.test_help_citation_removed_docstring_untouched  # noqa: E501
    # frob:tests scripts/strip_help_citations.py::rewrite_file  # noqa: E501
    def test_help_citation_removed_docstring_untouched(self, tmp_path: Path) -> None:
        """A citation in a `help=` string is stripped; the SAME citation
        in a docstring two lines away survives -- that is T-4691's scope,
        not this rewrite's.
        """
        path = tmp_path / "_planted.py"
        path.write_text(
            textwrap.dedent(
                '''
                import argparse


                def build(sub) -> None:
                    """Docstring cites T-9999 -- must NOT be touched."""
                    sub.add_parser("widget", help="do widget things (T-9999)")
                '''
            ),
            encoding="utf-8",
        )

        new_text = strip_help_citations.rewrite_file(path)

        assert new_text is not None
        assert 'help="do widget things"' in new_text
        assert "Docstring cites T-9999 -- must NOT be touched." in new_text

    # frob:tests tests/unit/coordinator_suite/test_strip_help_citations.py::TestRewriteFile.test_file_with_no_citations_returns_none  # noqa: E501
    # frob:tests scripts/strip_help_citations.py::rewrite_file  # noqa: E501
    def test_file_with_no_citations_returns_none(self, tmp_path: Path) -> None:
        """A file with no help-string citation is left alone (`None`
        signals "nothing to rewrite" to `main`'s changed-file count).
        """
        path = tmp_path / "_clean.py"
        path.write_text(
            "import argparse\n\n\ndef build(sub) -> None:\n"
            '    sub.add_parser("widget", help="do widget things")\n',
            encoding="utf-8",
        )

        assert strip_help_citations.rewrite_file(path) is None


class TestMain:
    """`strip_help_citations.main` -- the CLI entry point (dry-run diff
    preview by default, `--apply` to write).
    """

    # frob:tests tests/unit/coordinator_suite/test_strip_help_citations.py::TestMain.test_apply_rewrites_the_file_on_disk  # noqa: E501
    # frob:tests scripts/strip_help_citations.py::main  # noqa: E501
    def test_apply_rewrites_the_file_on_disk(self, tmp_path: Path) -> None:
        """`--apply` actually writes the stripped text back to disk."""
        parsers_dir = tmp_path / "src" / "frob" / "_cli_parsers"
        parsers_dir.mkdir(parents=True)
        target = parsers_dir / "_planted.py"
        target.write_text(
            "import argparse\n\n\ndef build(sub) -> None:\n"
            '    sub.add_parser("widget", help="do widget things (T-1234)")\n',
            encoding="utf-8",
        )
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            rc = strip_help_citations.main(["--apply"])
        finally:
            os.chdir(cwd)

        assert rc == 0
        assert "T-1234" not in target.read_text(encoding="utf-8")

    # frob:tests tests/unit/coordinator_suite/test_strip_help_citations.py::TestMain.test_without_apply_leaves_the_file_untouched  # noqa: E501
    # frob:tests scripts/strip_help_citations.py::main  # noqa: E501
    def test_without_apply_leaves_the_file_untouched(self, tmp_path: Path) -> None:
        """Without `--apply`, `main` only previews a diff -- the file on
        disk is unchanged.
        """
        parsers_dir = tmp_path / "src" / "frob" / "_cli_parsers"
        parsers_dir.mkdir(parents=True)
        target = parsers_dir / "_planted.py"
        original = (
            "import argparse\n\n\ndef build(sub) -> None:\n"
            '    sub.add_parser("widget", help="do widget things (T-1234)")\n'
        )
        target.write_text(original, encoding="utf-8")
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            rc = strip_help_citations.main([])
        finally:
            os.chdir(cwd)

        assert rc == 0
        assert target.read_text(encoding="utf-8") == original
