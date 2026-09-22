"""Tests for `frob._cli_parsers._shims` (T-4690): the single deprecation-
shim mechanism every deleted/renamed CLI verb in the T-4687 CLI-surface-
reduction story is built on."""

from __future__ import annotations

import datetime as dt
from pathlib import Path

import pytest

from frob._cli_parsers._root import _build_parser
from frob._cli_parsers._shims import announce_shim, is_past_sunset
from frob.app.app import _DEPRECATED_SPELLINGS
from frob.app.config import Subcommand


class TestIsPastSunset:
    """`is_past_sunset` is the single source of truth for the boundary
    date comparison -- both the runtime shim and this test call it rather
    than duplicating the comparison as a literal."""

    # frob:tests src/frob/_cli_parsers/_shims.py::is_past_sunset  # noqa: E501
    def test_before_sunset_is_false(self) -> None:
        """A date strictly before the sunset has not yet passed it."""
        assert not is_past_sunset("2026-12-01", today=dt.date(2026, 11, 30))
# frob:tests src/frob/_cli_parsers/_shims.py::is_past_sunset  # noqa: E501

    def test_on_sunset_is_false(self) -> None:
        """The sunset date itself is still within the working window
        (the boundary is exclusive: `today > sunset`, not `>=`)."""
        assert not is_past_sunset("2026-12-01", today=dt.date(2026, 12, 1))

    def test_after_sunset_is_true(self) -> None:
        """A date strictly after the sunset has passed it."""
        assert is_past_sunset("2026-12-01", today=dt.date(2026, 12, 2))


class TestAnnounceShim:
    """`announce_shim` is what every deleted verb's runner calls once, at
    # frob:tests src/frob/_cli_parsers/_shims.py::announce_shim  # noqa: E501
    the top of its `run()` (the fmt_runner precedent, generalized)."""

    # frob:tests src/frob/_cli_parsers/_shims.py::announce_shim  # noqa: E501
    def test_before_sunset_prints_notice_and_returns(self, capsys) -> None:
        """Before the sunset date: a stderr notice naming the survivor,
        and the call returns normally (exit 0) so the old spelling keeps
        working through the deprecation window."""
        announce_shim(
            old_name="explore",
            new_name="explore <subverb>",
            sunset="2026-12-01",
            ticket="T-4690",
            today=dt.date(2026, 9, 19),
        )
        captured = capsys.readouterr()
        assert "DEPRECATED" in captured.err
        assert "explore" in captured.err
        assert captured.out == ""

    def test_after_sunset_exits_nonzero(self, capsys) -> None:
        """Past the sunset date: `SystemExit` with a non-zero code, and
        the stderr notice explains what replaced the removed spelling."""
        with pytest.raises(SystemExit) as exc_info:
            announce_shim(
                old_name="fmt",
                new_name="format --directives",
                sunset="2026-12-01",
                ticket="T-3911",
                today=dt.date(2026, 12, 2),
            )
        assert exc_info.value.code != 0
        captured = capsys.readouterr()
        assert "removed" in captured.err
        assert "format --directives" in captured.err

    def test_never_writes_to_stdout(self, capsys) -> None:
        """The notice must never touch stdout -- a `--json`-producing
        runner's stdout is the JSON payload itself (the T-2492 precedent
        `fmt_runner.py` documents), so a leading human-readable line here
        would corrupt it exactly the same way."""
        announce_shim(
            old_name="whereis",
            new_name="doctor --whereis",
            sunset="2026-12-01",
            ticket="T-4690",
            today=dt.date(2026, 9, 19),
        )
        captured = capsys.readouterr()
        assert captured.out == ""


# frob:ticket T-4690
class TestDeprecatedSpellingsTable:
    """`frob.app.app._DEPRECATED_SPELLINGS` (T-4690): the single dispatch
    table `App.__call__` consults before every dispatch to decide whether
    to call `announce_shim` -- covers every deleted verb-GROUP spelling
    (`quality`/`design`/`ops`) and every deleted flat MIRROR spelling
    (`outline`/`map`/`xref`, and `verify status`/`fleet status` folded
    into top-level `status`) T-4690's acceptance criteria name."""

    def test_every_deleted_group_verb_is_covered(self) -> None:
        """The three deleted group verbs are each present as a
        whole-group (`subverb=None`) entry."""
        for subcommand in (Subcommand.quality, Subcommand.design, Subcommand.ops):
            assert (subcommand, None) in _DEPRECATED_SPELLINGS

    def test_every_deleted_explore_mirror_is_covered(self) -> None:
        """`outline`/`map`/`xref` each redirect to their `explore` twin."""
        assert _DEPRECATED_SPELLINGS[(Subcommand.outline, None)] == (
            "outline",
            "explore outline",
        )
        assert _DEPRECATED_SPELLINGS[(Subcommand.map, None)] == ("map", "explore map")
        assert _DEPRECATED_SPELLINGS[(Subcommand.xref, None)] == (
            "xref",
            "explore xref",
        )

    def test_verify_status_and_fleet_status_redirect_to_top_level_status(self) -> None:
        """`verify status`/`fleet status` (two of the three prior
        spellings T-4690's owner decision names) redirect to `status`,
        the one surviving spelling -- keyed by subverb, not the whole
        `verify`/`fleet` group (their other subcommands are unaffected)."""
        assert _DEPRECATED_SPELLINGS[(Subcommand.verify, "status")] == (
            "verify status",
            "status",
        )
        assert _DEPRECATED_SPELLINGS[(Subcommand.fleet, "status")] == (
            "fleet status",
            "status",
        )
        assert (Subcommand.verify, "now") not in _DEPRECATED_SPELLINGS
        assert (Subcommand.fleet, "route") not in _DEPRECATED_SPELLINGS


# frob:ticket T-4690
class TestSuppressedFromUsageLine:
    """T-4690 acceptance[1]: every deleted verb/alias is absent from
    `frob --help`'s top-level usage line while `explore` survives."""

    def test_deleted_names_absent_from_usage_choices(self) -> None:
        """`quality`/`design`/`ops`/`outline`/`map`/`xref`/`docs-search`/
        `fmt`/`docs`/`whereis` are all suppressed from the root parser's
        usage-line `{...}` choice set (`_GroupedHelpFormatter.
        _metavar_formatter`), even though most still parse successfully
        (deprecation shims, not deletions)."""
        parser = _build_parser()
        usage = parser.format_usage()
        for deleted in (
            "quality",
            "design",
            "ops",
            "outline",
            "map",
            "xref",
            "docs-search",
            "fmt",
            "docs",
            "whereis",
        ):
            assert f",{deleted}," not in usage.replace("{", ",").replace("}", ","), (
                f"{deleted!r} still appears in the usage line: {usage!r}"
            )

    def test_explore_survives_in_usage_choices(self) -> None:
        """`explore` -- the surviving verb per the coordinator's 2026-09-19
        amendment -- is NOT suppressed."""
        parser = _build_parser()
        usage = parser.format_usage()
        assert "explore" in usage


# frob:ticket T-4690
class TestPrintWhereis:
    """`frob.app.doctor_runner.print_whereis` (T-4690, folded from the
    standalone `frob whereis`, T-4299): shared by `frob doctor --whereis`
    and the deprecated `frob whereis` shim."""

    def test_plain_output_names_the_live_executable(self, capsys) -> None:
        """The plain-text path prints the actually-running interpreter's
        own `sys.executable`, never a PATH lookup."""
        import sys

        from frob.app.config import AppConfig
        from frob.app.doctor_runner import print_whereis

        print_whereis(AppConfig(doctor_json=False))
        captured = capsys.readouterr()
        assert sys.executable in captured.out
        assert "frob package" in captured.out

    def test_json_output_is_parseable(self, capsys) -> None:
        """`--json`/`doctor_json=True` emits a parseable JSON payload with
        the same three keys the plain path's lines name."""
        import json

        from frob.app.config import AppConfig
        from frob.app.doctor_runner import print_whereis

        print_whereis(AppConfig(doctor_json=True))
        captured = capsys.readouterr()
        payload = json.loads(captured.out)
        assert set(payload) == {"executable", "frob_package", "site_packages"}


# frob:ticket T-4690
class TestCitationSweep:
    """T-4690 acceptance[2]: the citation sweep over .claude/, docs/,
    scripts/, src/, tests/ for every deleted name. Scoped to genuine
    OPERATIONAL citations -- a markdown code-fence command line (the
    "run this" recommendation a reader would copy-paste) or a real argv
    literal in source -- not every prose/docstring mention of a deleted
    name, since this ticket's own new deprecation-notice docstrings
    necessarily NAME the spellings they deprecate (a mass rewrite of
    those would make the code self-contradictory, not more correct).
    `~/.claude/refs/frob.md` is the OWNER'S file and out of scope
    (T-4690's own instruction: list its needed edits in the Done report,
    do not touch it) -- this sweep does not reach outside the repo."""

    def test_no_markdown_code_fence_recommends_a_deleted_group_verb(self) -> None:
        """No `docs/`/`.claude/`/`scripts/` file's `frob <verb>` example
        line still recommends running one of the three deleted GROUP
        verbs or the folded/finished `whereis`/`fmt`/`docs-search` as
        the command to type -- the standalone flat leaves this ticket
        keeps as deprecated shims (`outline`/`map`/`xref`) are excluded:
        they still genuinely work through the sunset window, so an
        example naming one is not stale."""
        import re
        import subprocess

        deleted = ("quality", "design", "ops", "whereis", "fmt", "docs-search")
        pattern = re.compile(r"^frob (" + "|".join(deleted) + r")( |$)")
        result = subprocess.run(
            [
                "git",
                "grep",
                "-nE",
                pattern.pattern,
                "--",
                "docs/",
                ".claude/",
                "scripts/",
            ],
            capture_output=True,
            text=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        # git grep exits 1 when it finds nothing -- that is the PASS case.
        assert result.returncode == 1, (
            f"stale command-fence citation(s) of a deleted verb found:\n{result.stdout}"
        )
