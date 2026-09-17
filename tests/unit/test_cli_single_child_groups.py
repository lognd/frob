"""Unit tests for flattening single-child verb groups (T-4522): `frob
claude` and `frob natives` must dispatch straight to their one child
(`sync` / `build`) when invoked without a subverb, while the two-word
spelling keeps working as a documented alias for one release.

`agent env`, `narrative move`, and `worktree sweep` are NOT covered here:
`agent`/`worktree` are registered in `src/frob/_cli_parsers/_core.py`,
which collided with T-4523's live cross-worktree lease at scope time, and
`narrative` is registered via `frob.narrative._cli.add_narrative_parser`
from `src/frob/_cli_parsers/_root.py` -- both out of this ticket's scope
(see the Done report)."""

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
