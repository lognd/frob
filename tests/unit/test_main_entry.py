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


# frob:ticket T-2443
class TestMainInstallsSigtermReaper:
    """`main` must install T-2443's SIGTERM reaper before dispatching --
    the fix for `frob check` leaking `multiprocessing.forkserver`
    processes on a `timeout`-driven SIGTERM kill only takes effect if it
    runs on every real CLI invocation, before whatever subcommand follows
    has a chance to construct a process pool."""

    def test_main_installs_the_reaper_before_dispatch(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestMainInstallsSigtermReaper.test_main_installs_the_reaper_before_dispatch  # noqa: E501
        calls: list[str] = []

        def _record_install() -> None:
            calls.append("install")

        def _record_dispatch(argv: list[str]) -> None:
            calls.append("dispatch")

        monkeypatch.setattr("frob.process.install_sigterm_reaper", _record_install)
        monkeypatch.setattr(main_module, "_dispatch", _record_dispatch)
        monkeypatch.setattr("sys.argv", ["frob", "outline", "x.py"])

        main_module.main()

        assert calls == ["install", "dispatch"]


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


class TestVerboseFlag:
    """`_apply_verbose_env_override` (T-2979): the global `-v`/`--verbose`
    argv scan that sets `FROB_VERBOSE=1` before `main` dispatches, so the
    flag reaches every subcommand -- including the direct-dispatch verbs
    that bypass the main argparse tree entirely."""

    def test_dash_v_sets_debug_env_var(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestVerboseFlag.test_dash_v_sets_debug_env_var  # noqa: E501
        monkeypatch.delenv("FROB_VERBOSE", raising=False)
        monkeypatch.delenv("FROB_LOG_LEVEL", raising=False)
        main_module._apply_verbose_env_override(["-v", "doctor"])
        assert main_module.os.environ["FROB_VERBOSE"] == "1"

    def test_dash_dash_verbose_sets_debug_env_var(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestVerboseFlag.test_dash_dash_verbose_sets_debug_env_var  # noqa: E501
        monkeypatch.delenv("FROB_VERBOSE", raising=False)
        monkeypatch.delenv("FROB_LOG_LEVEL", raising=False)
        main_module._apply_verbose_env_override(["doctor", "--verbose"])
        assert main_module.os.environ["FROB_VERBOSE"] == "1"

    def test_no_verbose_flag_leaves_env_var_untouched(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestVerboseFlag.test_no_verbose_flag_leaves_env_var_untouched  # noqa: E501
        monkeypatch.delenv("FROB_VERBOSE", raising=False)
        monkeypatch.delenv("FROB_LOG_LEVEL", raising=False)
        main_module._apply_verbose_env_override(["doctor"])
        assert "FROB_VERBOSE" not in main_module.os.environ

    def test_existing_explicit_frob_log_level_is_not_clobbered(
        self, monkeypatch
    ) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestVerboseFlag.test_existing_explicit_frob_log_level_is_not_clobbered  # noqa: E501
        monkeypatch.delenv("FROB_VERBOSE", raising=False)
        monkeypatch.setenv("FROB_LOG_LEVEL", "ERROR")
        main_module._apply_verbose_env_override(["-v", "doctor"])
        assert main_module.os.environ["FROB_LOG_LEVEL"] == "ERROR"
        assert "FROB_VERBOSE" not in main_module.os.environ


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
            # T-2385: entries render one indent level DEEPER (4 spaces) than
            # their section header (2 spaces) -- see
            # test_section_headers_indent_strictly_less_than_entries below.
            assert f"\n    {name} " in groups_section, (
                f"{name!r} expected between the two headings"
            )

    def test_non_group_verb_listed_after_also_available_directly(self) -> None:
        """A representative non-group top-level command (`scaffold`) is
        listed under the "also available directly" heading, not the
        "verb groups" one."""
        parser = main_module._build_parser()
        help_text = parser.format_help()

        rest_idx = help_text.index("also available directly:")
        scaffold_idx = help_text.index("\n    scaffold ")
        assert scaffold_idx > rest_idx

    def test_section_headers_indent_strictly_less_than_entries(self) -> None:
        """T-2385: each section header renders at a strictly SMALLER indent
        than the command entries beneath it, so it can no longer be
        mistaken for a command itself (the original bug: both rendered at
        the same hardcoded 2-space indent)."""
        parser = main_module._build_parser()
        help_text = parser.format_help()

        for header in (
            "verb groups (each also usable standalone):",
            "also available directly:",
        ):
            lines = help_text.splitlines()
            header_idx, line = next(
                (i, ln) for i, ln in enumerate(lines) if header in ln
            )
            header_indent = len(line) - len(line.lstrip(" "))
            entry_line = next(ln for ln in lines[header_idx + 1 :] if ln.strip())
            entry_indent = len(entry_line) - len(entry_line.lstrip(" "))
            assert header_indent < entry_indent, (
                f"{header!r} indent ({header_indent}) must be strictly less "
                f"than its first entry's indent ({entry_indent})"
            )

    def test_no_help_text_breaks_inside_a_word(self) -> None:
        """T-2385 acceptance[0]: no rendered `--help` line may end mid-word
        (the narrower description column from the deeper entry indent
        previously broke `ops`'s help string as "...clean/c" / "lean/...").
        A genuine word-wrap break always falls on whitespace; textwrap
        never hyphenates, so a broken word shows up as a line ending in an
        orphan 1-2 character fragment that only forms a real word when
        joined with the next line's leading fragment with NO space."""
        parser = main_module._build_parser()
        help_text = parser.format_help()
        lines = help_text.splitlines()

        for line in lines:
            stripped = line.rstrip()
            if not stripped or not stripped[-1].isalpha():
                continue
            # A single trailing letter with no preceding space (i.e. the
            # line was truncated mid-token, not wrapped between tokens) is
            # the original bug's exact signature -- "...doctor/c".
            last_token = stripped.split()[-1] if stripped.split() else ""
            assert not (len(last_token) == 1 and stripped.endswith("/" + last_token)), (
                f"line appears to break mid-word: {stripped!r}"
            )

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


# frob:ticket T-2473
class TestConcurrentCheckAdvisory:
    """`_report_concurrent_check_advisory_best_effort` (T-2473) -- best-
    effort, advisory-only startup log line; never raises, never blocks."""

    def test_no_other_checks_logs_nothing(self, monkeypatch, caplog) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory.test_no_other_checks_logs_nothing  # noqa: E501
        monkeypatch.setattr("frob.process._reap.count_running_checks", lambda: 0)
        with caplog.at_level("INFO"):
            main_module._report_concurrent_check_advisory_best_effort()
        assert "other check" not in caplog.text

    def test_other_checks_logs_info_below_four(self, monkeypatch, caplog) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory.test_other_checks_logs_info_below_four  # noqa: E501
        monkeypatch.setattr("frob.process._reap.count_running_checks", lambda: 2)
        with caplog.at_level("INFO"):
            main_module._report_concurrent_check_advisory_best_effort()
        assert "2 other check(s)" in caplog.text
        info_records = [r for r in caplog.records if "other check" in r.message]
        assert all(r.levelname == "INFO" for r in info_records)

    def test_four_or_more_checks_logs_warning(self, monkeypatch, caplog) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory.test_four_or_more_checks_logs_warning  # noqa: E501
        monkeypatch.setattr("frob.process._reap.count_running_checks", lambda: 4)
        with caplog.at_level("INFO"):
            main_module._report_concurrent_check_advisory_best_effort()
        warn_records = [r for r in caplog.records if "other check" in r.message]
        assert warn_records and all(r.levelname == "WARNING" for r in warn_records)

    def test_never_raises_on_a_broken_count(self, monkeypatch) -> None:
        # frob:tests tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory.test_never_raises_on_a_broken_count  # noqa: E501
        def _boom() -> int:
            raise OSError("simulated /proc failure")

        monkeypatch.setattr("frob.process._reap.count_running_checks", _boom)
        # Must not raise -- best-effort, never fatal to the real check.
        main_module._report_concurrent_check_advisory_best_effort()

    # frob:ticket T-2484
    def test_force_stderr_writes_to_stderr_not_stdout(
        self, monkeypatch, capsys
    ) -> None:
        """T-2484 regression: `force_stderr=True` (the `--json` path) must
        never touch stdout -- that stream is the JSON payload -- and must
        still reach the operator, on stderr, so the advisory is not
        silently dropped instead of merely relocated."""
        # frob:tests tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory.test_force_stderr_writes_to_stderr_not_stdout  # noqa: E501
        monkeypatch.setattr("frob.process._reap.count_running_checks", lambda: 1)
        main_module._report_concurrent_check_advisory_best_effort(force_stderr=True)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "1 other check(s)" in captured.err

    # frob:ticket T-2484
    def test_force_stderr_below_four_still_reaches_stderr(
        self, monkeypatch, capsys
    ) -> None:
        """T-2484: the below-four case logs at INFO under the default
        (non-json) path, and `config.toml`'s stderr handler only accepts
        WARNING+ -- so relying on that handler's level threshold would
        silently drop this exact case. `force_stderr=True` must bypass
        that threshold entirely, not just relocate it."""
        # frob:tests tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory.test_force_stderr_below_four_still_reaches_stderr  # noqa: E501
        monkeypatch.setattr("frob.process._reap.count_running_checks", lambda: 2)
        main_module._report_concurrent_check_advisory_best_effort(force_stderr=True)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert "2 other check(s)" in captured.err

    # frob:ticket T-2484
    def test_force_stderr_idle_machine_stays_quiet(self, monkeypatch, capsys) -> None:
        """T-2484 must-stay-quiet: an idle machine (0 other checks) must
        add no noise on either stream, `force_stderr` or not."""
        # frob:tests tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory.test_force_stderr_idle_machine_stays_quiet  # noqa: E501
        monkeypatch.setattr("frob.process._reap.count_running_checks", lambda: 0)
        main_module._report_concurrent_check_advisory_best_effort(force_stderr=True)
        captured = capsys.readouterr()
        assert captured.out == ""
        assert captured.err == ""

    # frob:ticket T-2484
    def test_dispatch_passes_force_stderr_only_for_json(self, monkeypatch) -> None:
        """`_dispatch` must derive `force_stderr` from the parsed
        `check_json` flag, not from some other proxy -- a plain (non-
        json) `frob check` keeps the old level-routed behavior."""
        # frob:tests tests/unit/test_main_entry.py::TestConcurrentCheckAdvisory.test_dispatch_passes_force_stderr_only_for_json  # noqa: E501
        calls = []
        monkeypatch.setattr(
            main_module,
            "_report_concurrent_check_advisory_best_effort",
            lambda **kw: calls.append(kw),
        )
        monkeypatch.setattr(
            main_module, "_reap_orphaned_forkservers_best_effort", lambda: None
        )
        monkeypatch.setattr(
            main_module, "_print_startup_warnings", lambda *a, **kw: None
        )
        monkeypatch.setattr(
            main_module.AppConfig, "from_external", lambda *a, **kw: object()
        )
        monkeypatch.setattr(main_module, "App", lambda cfg: lambda: None)
        main_module._dispatch(["check", "--json"])
        assert calls == [{"force_stderr": True}]
        calls.clear()
        main_module._dispatch(["check"])
        assert calls == [{"force_stderr": False}]
