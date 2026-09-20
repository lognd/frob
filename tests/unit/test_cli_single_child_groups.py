"""Unit tests for flattening single-child verb groups (T-4522/T-4546):
`frob claude`/`frob natives` (T-4522), and `frob agent`/`frob narrative`
(T-4546), must dispatch straight to their one child (`sync` / `build` /
`env` / `move`) when invoked without a subverb, while the two-word
spelling keeps working as a documented alias for one release.

`frob worktree sweep` is deliberately NOT flattened here: `worktree` was
a single-child group when T-4546 was filed, but real dispatch
(`frob.app.worktree_runner._build_worktree_parser`) has since grown a
`remove` and a `release-lease` child alongside `sweep` -- it is no longer
a single-child group, so defaulting bare `frob worktree` to `sweep`
(which REMOVES worktrees) would silently pick one of three destructive/
non-destructive actions on the user's behalf. See the Done report.

`agent`/`narrative`'s REAL dispatch bypasses `_build_parser()` entirely
(`__main__._dispatch` special-cases both), so their flattening is tested
at the actual dispatch layer -- `frob.app.agent_runner.run`/
`_normalize_agent_argv` and `frob.__main__._normalize_narrative_argv`
-- not merely against `_build_parser()`'s own help-only tree (which
`TestAgentGroupFlattened`/`TestNarrativeGroupFlattened` also cover, for
the `--help` rendering)."""

from __future__ import annotations

from frob._cli_parsers._root import _build_parser


# frob:ticket T-4522
class TestClaudeGroupFlattened:
    """`frob claude` wraps exactly one child (`sync`); bare invocation must
    run what `frob claude sync` ran (T-4522)."""

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened.test_bare_claude_defaults_to_sync  # noqa: E501
    def test_bare_claude_defaults_to_sync(self) -> None:
        """`frob claude` with no subverb resolves `claude_command` to
        `sync`, the same dest value the two-word form produces."""
        parser = _build_parser()
        args = parser.parse_args(["claude"])
        assert args.claude_command == "sync"
        assert args.claude_check is False

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened.test_bare_claude_check_flag  # noqa: E501
    def test_bare_claude_check_flag(self) -> None:
        """`frob claude --check` (no `sync`) must set `claude_check` the
        same way `frob claude sync --check` does -- flattening must not
        drop the child's own flags."""
        parser = _build_parser()
        args = parser.parse_args(["claude", "--check"])
        assert args.claude_command == "sync"
        assert args.claude_check is True

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened.test_two_word_alias_still_works  # noqa: E501
    def test_two_word_alias_still_works(self) -> None:
        """`frob claude sync --check` -- the documented one-release alias
        -- must still parse to the identical dest values as the flat
        form."""
        parser = _build_parser()
        args = parser.parse_args(["claude", "sync", "--check"])
        assert args.claude_command == "sync"
        assert args.claude_check is True

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestClaudeGroupFlattened.test_help_notes_alias  # noqa: E501
    def test_help_notes_alias(self, capsys) -> None:
        """`frob claude --help` documents the flattening/alias (T-4522)."""
        parser = _build_parser()
        try:
            parser.parse_args(["claude", "--help"])
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "T-4522" in out


# frob:ticket T-4522
class TestNativesGroupFlattened:
    """`frob natives` wraps exactly one child (`build`); bare invocation
    must run what `frob natives build` ran (T-4522)."""

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestNativesGroupFlattened.test_bare_natives_defaults_to_build  # noqa: E501
    def test_bare_natives_defaults_to_build(self) -> None:
        """`frob natives` with no subverb resolves `natives_command` to
        `build`, the same dest value the two-word form produces."""
        parser = _build_parser()
        args = parser.parse_args(["natives"])
        assert args.natives_command == "build"
        assert args.natives_path == "."

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestNativesGroupFlattened.test_bare_natives_path_flag  # noqa: E501
    def test_bare_natives_path_flag(self) -> None:
        """`frob natives --path DIR` (no `build`) must set `natives_path`
        the same way `frob natives build --path DIR` does."""
        parser = _build_parser()
        args = parser.parse_args(["natives", "--path", "rust/frob-core"])
        assert args.natives_command == "build"
        assert args.natives_path == "rust/frob-core"

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestNativesGroupFlattened.test_two_word_alias_still_works  # noqa: E501
    def test_two_word_alias_still_works(self) -> None:
        """`frob natives build --path DIR` -- the documented one-release
        alias -- must still parse to the identical dest values as the
        flat form."""
        parser = _build_parser()
        args = parser.parse_args(["natives", "build", "--path", "rust/frob-core"])
        assert args.natives_command == "build"
        assert args.natives_path == "rust/frob-core"

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestNativesGroupFlattened.test_help_notes_alias  # noqa: E501
    def test_help_notes_alias(self, capsys) -> None:
        """`frob natives --help` documents the flattening/alias (T-4522)."""
        parser = _build_parser()
        try:
            parser.parse_args(["natives", "--help"])
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "T-4522" in out


# frob:ticket T-4546
class TestAgentGroupFlattened:
    """`frob agent` wraps exactly one child (`env`); bare invocation must
    run what `frob agent env` ran (T-4546). Real dispatch bypasses
    `_build_parser()` entirely (`__main__._dispatch` special-cases
    `agent`), so the REAL behavior is tested against `frob.app.
    agent_runner` directly; `_build_parser()` is only checked for its
    `--help` rendering."""

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened.test_normalize_inserts_implied_env  # noqa: E501
    def test_normalize_inserts_implied_env(self) -> None:
        """`_normalize_agent_argv` inserts `env` ahead of a bare path, and
        leaves an already-explicit `env`/help flag untouched."""
        from frob.app.agent_runner import _normalize_agent_argv

        assert _normalize_agent_argv([]) == ["env"]
        assert _normalize_agent_argv(["/tmp/wt"]) == ["env", "/tmp/wt"]
        assert _normalize_agent_argv(["env", "/tmp/wt"]) == ["env", "/tmp/wt"]
        assert _normalize_agent_argv(["-h"]) == ["-h"]
        assert _normalize_agent_argv(["--help"]) == ["--help"]

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened.test_bare_agent_defaults_to_env  # noqa: E501
    def test_bare_agent_defaults_to_env(self) -> None:
        """`frob agent [path]` (no `env`) resolves the SAME `agent_command`/
        `path` dest values `frob agent env [path]` produces, at the real
        `_build_agent_parser` dispatch layer."""
        from frob.app.agent_runner import _build_agent_parser, _normalize_agent_argv

        parser = _build_agent_parser()
        flat = parser.parse_args(_normalize_agent_argv(["/tmp/wt"]))
        two_word = parser.parse_args(_normalize_agent_argv(["env", "/tmp/wt"]))
        assert flat.agent_command == two_word.agent_command == "env"
        assert flat.path == two_word.path == "/tmp/wt"

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened.test_run_dispatches_bare_invocation_to_env  # noqa: E501
    def test_run_dispatches_bare_invocation_to_env(self, monkeypatch) -> None:
        """`frob.app.agent_runner.run([])` (bare, no `env`) calls `_run_env`
        exactly as `run(["env"])` would."""
        import frob.app.agent_runner as agent_runner_mod

        calls: list[str] = []
        monkeypatch.setattr(agent_runner_mod, "_run_env", calls.append)

        agent_runner_mod.run([])
        agent_runner_mod.run(["env"])
        assert calls == [".", "."]

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestAgentGroupFlattened.test_help_notes_alias  # noqa: E501
    def test_help_notes_alias(self, capsys) -> None:
        """`frob agent --help` documents the flattening/alias (T-4546)."""
        parser = _build_parser()
        try:
            parser.parse_args(["agent", "--help"])
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "T-4546" in out


# frob:ticket T-4546
class TestNarrativeGroupFlattened:
    """`frob narrative` wraps exactly one child (`move`); bare invocation
    must run what `frob narrative move` ran (T-4546). Real dispatch
    bypasses `_build_parser()` entirely (`__main__._dispatch_narrative`
    builds its own fresh parser), so the REAL behavior is tested against
    `frob.__main__._normalize_narrative_argv` directly;
    `_build_parser()` is only checked for its `--help` rendering."""

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened.test_normalize_inserts_implied_move  # noqa: E501
    def test_normalize_inserts_implied_move(self) -> None:
        """`_normalize_narrative_argv` inserts `move` ahead of a bare
        `FILE LINE ...` tail, and leaves an already-explicit `move`/help
        flag untouched."""
        from frob.__main__ import _normalize_narrative_argv

        assert _normalize_narrative_argv([]) == ["move"]
        assert _normalize_narrative_argv(["f.py", "5", "--reason", "x"]) == [
            "move",
            "f.py",
            "5",
            "--reason",
            "x",
        ]
        assert _normalize_narrative_argv(["move", "f.py", "5"]) == [
            "move",
            "f.py",
            "5",
        ]
        assert _normalize_narrative_argv(["-h"]) == ["-h"]

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened.test_bare_narrative_defaults_to_move  # noqa: E501
    def test_bare_narrative_defaults_to_move(self) -> None:
        """`frob narrative FILE LINE --reason X` (no `move`) resolves the
        SAME dest values `frob narrative move FILE LINE --reason X`
        produces, at the real `add_narrative_parser` dispatch layer."""
        import argparse

        from frob.__main__ import _normalize_narrative_argv
        from frob.narrative._cli import add_narrative_parser

        def build_and_parse(tail: list[str]):
            p = argparse.ArgumentParser(prog="frob")
            sub = p.add_subparsers(dest="subcommand")
            add_narrative_parser(sub)
            return p.parse_args(["narrative", *_normalize_narrative_argv(tail)])

        flat = build_and_parse(["f.py", "5", "--reason", "x"])
        two_word = build_and_parse(["move", "f.py", "5", "--reason", "x"])
        assert flat.narrative_subcommand == two_word.narrative_subcommand == "move"
        assert flat.file == two_word.file
        assert flat.line == two_word.line == 5
        assert flat.reason == two_word.reason == "x"

    # frob:tests tests/unit/test_cli_single_child_groups.py::TestNarrativeGroupFlattened.test_help_notes_alias  # noqa: E501
    def test_help_notes_alias(self, capsys) -> None:
        """`frob narrative --help` documents the flattening/alias
        (T-4546)."""
        parser = _build_parser()
        try:
            parser.parse_args(["narrative", "--help"])
        except SystemExit:
            pass
        out = capsys.readouterr().out
        assert "T-4546" in out
