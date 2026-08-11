"""Unit tests for `frob.__main__`'s top-level entry point (T-0355), CLI
vocabulary normalization (T-0578), and the lazy log stream handlers that
keep this module's own stderr assertions from being polluted by a stale
captured stream (T-1385)."""

from __future__ import annotations

import io
import logging
import sys

import pytest

from frob import __main__ as main_module
from frob.logging.handler import _LazyStderrHandler, _LazyStdoutHandler


# frob:ticket T-0355
class TestMainSigint:
    """A `KeyboardInterrupt` during dispatch must print a clean one-line
    message and exit 130 (128+SIGINT), not spill a bare traceback (T-0355)."""

    def test_keyboard_interrupt_prints_clean_message_and_exits_130(
        self, monkeypatch, capsys
    ) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestMainSigint.test_keyboard_interrupt_prints_clean_message_and_exits_130  # noqa: E501
        def _raise(argv: list[str]) -> None:
            raise KeyboardInterrupt

        monkeypatch.setattr(main_module, "_dispatch", _raise)
        monkeypatch.setattr("sys.argv", ["frob", "check"])

        with pytest.raises(SystemExit) as exc_info:
            main_module.main()

        assert exc_info.value.code == 130
        captured = capsys.readouterr()
        assert "interrupted" in captured.err
        assert "Traceback" not in captured.err

    def test_normal_dispatch_is_unaffected(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestMainSigint.test_normal_dispatch_is_unaffected  # noqa: E501
        calls: list[list[str]] = []

        def _record(argv: list[str]) -> None:
            calls.append(argv)

        monkeypatch.setattr(main_module, "_dispatch", _record)
        monkeypatch.setattr("sys.argv", ["frob", "outline", "x.py"])

        main_module.main()

        assert calls == [["outline", "x.py"]]


# frob:ticket T-1022
class TestMainUnhandledException:
    """An unhandled exception during dispatch must be logged (with a real
    traceback, `exc_info=True`) and reported as a clean one-line `frob:
    <exc>` message with exit 1 -- never a raw traceback crossing the CLI
    boundary (EXHAUST002 burn-down, T-1022)."""

    def test_unhandled_exception_prints_clean_message_and_exits_1(
        self, monkeypatch, capsys
    ) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestMainUnhandledException.test_unhandled_exception_prints_clean_message_and_exits_1  # noqa: E501
        def _raise(argv: list[str]) -> None:
            raise ValueError("boom")

        monkeypatch.setattr(main_module, "_dispatch", _raise)
        monkeypatch.setattr("sys.argv", ["frob", "check"])

        with pytest.raises(SystemExit) as exc_info:
            main_module.main()

        assert exc_info.value.code == 1
        captured = capsys.readouterr()
        assert "frob: boom" in captured.err
        assert "Traceback" not in captured.err

    def test_unhandled_exception_logs_with_exc_info(self, monkeypatch, capsys) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestMainUnhandledException.test_unhandled_exception_logs_with_exc_info  # noqa: E501
        def _raise(argv: list[str]) -> None:
            raise ValueError("boom")

        logged: list[dict] = []

        def _fake_error(msg, *args, **kwargs) -> None:  # noqa: ANN001, ANN002, ANN003
            logged.append(kwargs)

        monkeypatch.setattr(main_module, "_dispatch", _raise)
        monkeypatch.setattr("sys.argv", ["frob", "check"])
        monkeypatch.setattr(main_module._log, "error", _fake_error)

        with pytest.raises(SystemExit):
            main_module.main()

        assert logged == [{"exc_info": True}]


# frob:ticket T-1483
class TestRefactorDispatch:
    """`frob refactor` is routed by `_dispatch` the same way `bind`/
    `agent`/`worktree` already are (T-1483) -- `run_refactor_command`
    takes a parsed `Namespace` and returns a raw exit code, not the
    uniform `run(AppConfig)` shape every `Subcommand`-mapped runner
    shares."""

    def test_refactor_subcommand_dispatches_to_run_refactor_command(
        self, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestRefactorDispatch.test_refactor_subcommand_dispatches_to_run_refactor_command  # noqa: E501
        calls: list = []

        def _fake_run(args) -> int:  # noqa: ANN001
            calls.append(args)
            return 0

        monkeypatch.setattr("frob.refactor._cli.run_refactor_command", _fake_run)

        with pytest.raises(SystemExit) as exc_info:
            main_module._dispatch(["refactor", "rename", "pkg.mod:x", "pkg.mod:y"])

        assert exc_info.value.code == 0
        assert len(calls) == 1
        assert calls[0].source.module == "pkg.mod"
        assert calls[0].source.qualname == "x"
        assert calls[0].destination.qualname == "y"

    def test_refactor_exit_code_propagates(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestRefactorDispatch.test_refactor_exit_code_propagates  # noqa: E501
        monkeypatch.setattr("frob.refactor._cli.run_refactor_command", lambda args: 1)

        with pytest.raises(SystemExit) as exc_info:
            main_module._dispatch(["refactor", "rename", "pkg.mod:x", "pkg.mod:y"])

        assert exc_info.value.code == 1


# frob:ticket T-0578
class TestDidYouMean:
    """`_build_parser`'s `_SuggestingArgumentParser` appends a "did you
    mean" suggestion to argparse's own error for an unknown subcommand or
    an unrecognized flag (T-0578); see `docs/commands/cli-vocabulary.md`
    for the full vocabulary/back-compat-alias contract this exercises."""

    # frob:ticket T-0578
    def test_unknown_subcommand_suggests_closest(self, capsys) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestDidYouMean.test_unknown_subcommand_suggests_closest  # noqa: E501
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["tikcet"])
        assert "did you mean: ticket?" in capsys.readouterr().err

    # frob:ticket T-0578
    def test_unknown_ticket_subcommand_suggests_closest(self, capsys) -> None:
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "lst"])
        assert "did you mean: list?" in capsys.readouterr().err

    # frob:ticket T-0578
    def test_unrecognized_flag_suggests_closest_known_flag(self, capsys) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestDidYouMean.test_unrecognized_flag_suggests_closest_known_flag  # noqa: E501
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "list", "--statuz", "queued"])
        assert "did you mean: --status?" in capsys.readouterr().err

    # frob:ticket T-0578
    def test_far_off_flag_gets_no_suggestion(self, capsys) -> None:
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "list", "--zzzzzzzzzzz"])
        assert "did you mean" not in capsys.readouterr().err

    # frob:ticket T-2107
    def test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand(
        self, capsys
    ) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestDidYouMean.test_unrecognized_flag_suggestion_scoped_to_invoked_subcommand  # noqa: E501
        """`--limit` exists on `frob ticket list` but NOT on `frob ticket
        doable` (T-2107): passing it to `doable` must not "suggest" the
        exact flag that just failed, since that flag does not exist on
        this subcommand either -- a suggestion drawn from the whole CLI
        tree is actively misleading, not merely unhelpful."""
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "doable", "--limit", "25"])
        assert "did you mean: --limit?" not in capsys.readouterr().err

    # frob:ticket T-2107
    def test_unrecognized_flag_error_shows_invoked_subcommand_usage(
        self, capsys
    ) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestDidYouMean.test_unrecognized_flag_error_shows_invoked_subcommand_usage  # noqa: E501
        """The usage block printed on an unrecognized-flag error must be
        the INVOKED subcommand's own (`frob ticket doable`), not the
        top-level `frob` usage listing every verb group (T-2107)."""
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "doable", "--limit", "25"])
        err = capsys.readouterr().err
        assert "usage: frob ticket doable" in err
        assert "{scaffold,cycle,explore" not in err


# frob:ticket T-0578
class TestVocabularyAliases:
    """Back-compat aliases for the pre-T-0578 misuses named in the ticket
    body: `list --status` (canonical: `--state`) and `done-report --body`
    (canonical: `--why`)."""

    # frob:ticket T-0578
    def test_ticket_list_status_alias_sets_state_dest(self) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestVocabularyAliases.test_ticket_list_status_alias_sets_state_dest  # noqa: E501
        parser = main_module._build_parser()
        args = parser.parse_args(["ticket", "list", "--status", "queued"])
        assert args.ticket_state == "queued"

    # frob:ticket T-0578
    def test_ticket_done_report_body_alias_sets_why_dest(self) -> None:
        parser = main_module._build_parser()
        args = parser.parse_args(
            ["ticket", "done-report", "T-0001", "--body", "narrative"]
        )
        assert args.ticket_why == "narrative"


# frob:ticket T-1385
class TestLazyLogHandlers:
    """`_LazyStdoutHandler`/`_LazyStderrHandler` must resolve sys.stdout/
    sys.stderr live at emit time, never cache the stream dictConfig saw at
    bind time -- otherwise a pytest capsys/capfd stream closed at test
    teardown leaves a stale handle that raises on the next emit and
    pollutes an unrelated test's captured stderr (T-1385)."""

    @pytest.mark.parametrize(
        ("handler_cls", "attr"),
        [(_LazyStderrHandler, "stderr"), (_LazyStdoutHandler, "stdout")],
        ids=["stderr", "stdout"],
    )
    def test_handler_follows_stream_swap_not_bind_time_capture(
        self, monkeypatch, handler_cls, attr
    ) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestLazyLogHandlers.test_handler_follows_stream_swap_not_bind_time_capture  # noqa: E501
        handler = handler_cls()
        first = io.StringIO()
        monkeypatch.setattr(sys, attr, first)
        assert handler.stream is first
        second = io.StringIO()
        monkeypatch.setattr(sys, attr, second)
        assert handler.stream is second

    def test_stderr_handler_never_emits_against_a_closed_captured_stream(
        self, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestLazyLogHandlers.test_stderr_handler_never_emits_against_a_closed_captured_stream  # noqa: E501
        handler = _LazyStderrHandler()
        stale = io.StringIO()
        monkeypatch.setattr(sys, "stderr", stale)
        stale.close()  # simulates a pytest capsys stream closed at teardown

        live = io.StringIO()
        monkeypatch.setattr(sys, "stderr", live)  # a later test's capture

        record = logging.LogRecord("x", logging.WARNING, __file__, 1, "msg", (), None)
        handler.emit(record)  # must resolve `live`, never the closed `stale`

        assert "msg" in live.getvalue()


# frob:ticket T-1571
class TestGroupedHelpFormatter:
    """`frob --help` (T-1571, acceptance[0] on T-1238): the root parser's
    subcommand listing presents verb groups first, then every other
    top-level command under a separate heading."""

    def test_verb_groups_listed_before_also_available_directly_section(self) -> None:
        """Every `_VERB_GROUP_NAMES` member appears under the "verb
        groups" heading, strictly before the "also available directly"
        heading, in the rendered `--help` text."""
        parser = main_module._build_parser()
        help_text = parser.format_help()

        groups_idx = help_text.index("verb groups (each also usable standalone):")
        rest_idx = help_text.index("also available directly:")
        assert groups_idx < rest_idx

        # Slice once instead of re-`.index()`ing per name in a loop (PERF002).
        groups_section = help_text[groups_idx:rest_idx]
        for name in main_module._VERB_GROUP_NAMES:
            assert f"\n  {name} " in groups_section, (
                f"{name!r} expected between the two headings"
            )

    def test_non_group_verb_listed_after_also_available_directly(self) -> None:
        """A representative non-group top-level command (`scaffold`) is
        listed under the "also available directly" heading, not the
        "verb groups" one."""
        parser = main_module._build_parser()
        help_text = parser.format_help()

        rest_idx = help_text.index("also available directly:")
        scaffold_idx = help_text.index("\n  scaffold ")
        assert scaffold_idx > rest_idx

    def test_nested_subparser_help_is_unaffected(self) -> None:
        """`frob quality --help` keeps the ordinary flat argparse listing
        -- `formatter_class` is not inherited by `add_parser()`-created
        nested subparsers."""
        import argparse as _argparse

        parser = main_module._build_parser()
        subparsers_action = next(
            a for a in parser._actions if isinstance(a, _argparse._SubParsersAction)
        )
        quality_parser = subparsers_action.choices["quality"]
        help_text = quality_parser.format_help()
        assert "verb groups" not in help_text
        assert "also available directly" not in help_text
