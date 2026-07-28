"""Unit tests for `frob.__main__`'s top-level entry point (T-0355) and CLI
vocabulary normalization (T-0578)."""

from __future__ import annotations

import pytest

from frob import __main__ as main_module


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
