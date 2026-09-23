"""`scripts/count_ticket_citations.py` -- T-5134's citation counter.

WHY THIS EXISTS. The owner directive of 2026-09-20 (T-5134) requires the
`help=`/`description=`/`epilog=` count under `src/frob/_cli_parsers/` to
stay at zero going forward, and this script is what both the removal
work and any future re-measurement rely on. A positive control -- plant
a real citation in a synthetic argparse call and assert the detector
reports it -- is the only way to know the detector fires at all, rather
than trivially returning zero because it never ran or its regex broke.
"""

from __future__ import annotations

import importlib.util
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

_SCRIPTS = Path(__file__).resolve().parents[3] / "scripts"


def _load_script(name: str) -> ModuleType:
    """Import `scripts/<name>.py` by path (`scripts/` has no
    `__init__.py`), same technique `tests/unit/conftest.py::_load_script`
    uses for its own shared script loads -- kept local here rather than
    added to that shared fixture set since this module is this ticket's
    only consumer.
    """
    path = _SCRIPTS / f"{name}.py"
    spec = importlib.util.spec_from_file_location(f"_scripts_under_test.{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


count_ticket_citations = _load_script("count_ticket_citations")


class TestFindHelpCitations:
    """`count_ticket_citations.find_help_citations` -- AST scan of
    `help=`/`description=`/`epilog=` string literals for `T-####`.
    """

    # frob:tests tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindHelpCitations.test_positive_control_plants_a_citation_the_detector_must_report  # noqa: E501
    # frob:tests scripts/count_ticket_citations.py::find_help_citations  # noqa: E501
    def test_positive_control_plants_a_citation_the_detector_must_report(
        self, tmp_path: Path
    ) -> None:
        """MUST FAIL if the detector silently returns 0 for any reason
        (never ran, regex broke, wrong keyword set) -- a planted `T-1234`
        inside a `help=` string is the one thing this scan can never miss.
        """
        parsers_dir = tmp_path / "src" / "frob" / "_cli_parsers"
        parsers_dir.mkdir(parents=True)
        (parsers_dir / "_planted.py").write_text(
            textwrap.dedent(
                """
                import argparse

                def build(sub: argparse._SubParsersAction) -> None:
                    sub.add_parser(
                        "widget",
                        help="do widget things (T-1234)",
                    )
                """
            ),
            encoding="utf-8",
        )

        hits = count_ticket_citations.find_help_citations(parsers_dir)

        tokens = [token for _path, _line, token in hits]
        assert "T-1234" in tokens

    # frob:tests tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindHelpCitations.test_docstring_and_comment_citations_are_not_counted  # noqa: E501
    # frob:tests scripts/count_ticket_citations.py::find_help_citations  # noqa: E501
    def test_docstring_and_comment_citations_are_not_counted(
        self, tmp_path: Path
    ) -> None:
        """A `T-####` in a docstring or `#` comment is T-4691's scope
        (source comment narrative), not this ticket's -- the help-string
        scan must not flag it.
        """
        parsers_dir = tmp_path / "src" / "frob" / "_cli_parsers"
        parsers_dir.mkdir(parents=True)
        (parsers_dir / "_clean.py").write_text(
            textwrap.dedent(
                """
                # T-9999: this comment cites a ticket but is not help text.
                def build() -> None:
                    \"\"\"T-9999 also here, in a docstring.\"\"\"
                    return None
                """
            ),
            encoding="utf-8",
        )

        hits = count_ticket_citations.find_help_citations(parsers_dir)

        assert hits == []


class TestFindDocsCitations:
    """`count_ticket_citations.find_docs_citations` -- docs/ prose scan,
    excluding directive-grammar examples and exempt subtrees.
    """

    # frob:tests tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindDocsCitations.test_prose_citation_is_reported  # noqa: E501
    # frob:tests scripts/count_ticket_citations.py::find_docs_citations  # noqa: E501
    def test_prose_citation_is_reported(self, tmp_path: Path) -> None:
        """A plain prose mention of a real-shaped ticket id is a finding."""
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text(
            "This behavior was added in T-1234 and has stayed stable.\n",
            encoding="utf-8",
        )

        hits = count_ticket_citations.find_docs_citations(docs_dir)

        tokens = [token for _path, _line, token in hits]
        assert "T-1234" in tokens

    # frob:tests tests/unit/coordinator_suite/test_count_ticket_citations.py::TestFindDocsCitations.test_directive_grammar_example_is_exempt  # noqa: E501
    # frob:tests scripts/count_ticket_citations.py::find_docs_citations  # noqa: E501
    def test_directive_grammar_example_is_exempt(self, tmp_path: Path) -> None:
        """A line documenting the `frob:` directive grammar itself (an
        HTML-comment example naming a real-shaped ticket id as syntax,
        not a citation) is not a finding.
        """
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "guide.md").write_text(
            "<!-- frob:ticket T-1234 -->\nfrob:tests some/path.py::thing\n",
            encoding="utf-8",
        )

        hits = count_ticket_citations.find_docs_citations(docs_dir)

        assert hits == []


class TestMain:
    """`count_ticket_citations.main` -- the CLI entry point wrapping
    `find_help_citations`/`find_docs_citations`.
    """

    # frob:tests tests/unit/coordinator_suite/test_count_ticket_citations.py::TestMain.test_help_scope_prints_the_count  # noqa: E501
    # frob:tests scripts/count_ticket_citations.py::main  # noqa: E501
    def test_help_scope_prints_the_count(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        """`--scope help` run from a synthetic `src/frob/_cli_parsers/`
        tree prints the citation count on its own line.
        """
        import os

        parsers_dir = tmp_path / "src" / "frob" / "_cli_parsers"
        parsers_dir.mkdir(parents=True)
        (parsers_dir / "_planted.py").write_text(
            'import argparse\n\n\ndef build(sub):\n    sub.add_parser("w", help="w (T-1234)")\n',
            encoding="utf-8",
        )
        cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            rc = count_ticket_citations.main(["--scope", "help"])
        finally:
            os.chdir(cwd)
        out = capsys.readouterr().out
        assert rc == 0
        assert out.strip().splitlines()[-1] == "1"
