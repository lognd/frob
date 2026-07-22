"""Unit tests for `frob.__main__`'s top-level entry point (T-0355)."""

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
