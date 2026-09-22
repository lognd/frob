"""T-3233 drift-lock: `frob cycle`/`frob xref`/`frob exports --consumers`'s
`--lang` argparse `choices` used to be 3 separately hand-typed
`['python', 'cpp', 'c']` literals, narrower than `frob.lang`'s own
extension registry (T-2996 measured this, unfixed until now) -- a new
grammar `frob.lang` gained (kotlin, csharp, cuda, zig, bash) was silently
unreachable through any of these three flags. `_LANG_CHOICES`
(`frob._cli_parsers._core`) is now the single derived source all three
route through; this test locks that wiring so a future edit cannot
reintroduce a separate hard-coded copy at any of the three call sites
without this test catching it.
"""

from __future__ import annotations

import argparse
from typing import cast

from frob.__main__ import _build_parser
from frob.lang import language_for_extension, tree_sitter_extensions


def _top_level_action(dest_name: str):
    """The real, registered top-level subparser whose primary positional
    or first argument carries `dest_name` -- exercised through the actual
    `_build_parser()` tree (not a re-implementation), so this test fails
    the moment the real CLI surface drifts from what it locks."""
    root = _build_parser()
    assert root._subparsers is not None
    for group_action in root._subparsers._group_actions:
        choices = group_action.choices
        # `argparse.Action.choices` is typed `Iterable[Any] | None` by
        # typeshed, but `_SubParsersAction.choices` is always a real
        # `dict[str, ArgumentParser]` at runtime (stdlib source); narrow
        # explicitly so `ty`/mypy can see `.values()` is valid here.
        if not isinstance(choices, dict):
            continue
        parser_map = cast("dict[str, argparse.ArgumentParser]", choices)
        for subparser in parser_map.values():
            for action in subparser._actions:
                if action.dest == dest_name:
                    return action
    raise AssertionError(f"no argparse action found with dest={dest_name!r}")


class TestLangChoicesDeriveFromFrobLangRegistry:
    """`--lang` on `frob cycle`, `frob xref`, and `frob exports
    --consumers` must all resolve to the SAME choices tuple, and that
    tuple must equal what `frob.lang`'s own tree-sitter extension
    registry reports right now -- not a separately hand-maintained copy
    that could silently fall behind it again."""

    def _expected_choices(self) -> tuple[str, ...]:
        """The registry-derived set this test expects every `--lang`
        flag to expose, computed independently of
        `frob._cli_parsers._core._LANG_CHOICES` itself (straight from
        `frob.lang`'s public extension/language functions) so a bug in
        the shared constant's own derivation cannot hide behind a test
        that just re-imports and compares it to itself."""
        return tuple(
            sorted(
                {
                    lang
                    for ext in tree_sitter_extensions()
                    if (lang := language_for_extension(ext)) is not None
                }
            )
        )

    # frob:tests src/frob/_cli_parsers/_core.py::_LANG_CHOICES  # noqa: E501
    def test_lang_choices_track_frob_lang_registry(self) -> None:
        """The registry-derived set is neither the old, narrower
        `['python', 'cpp', 'c']` literal nor empty -- a real, current
        measurement of `frob.lang`'s grammar table, not a frozen
        snapshot."""
        expected = self._expected_choices()
        assert "python" in expected
        assert "cpp" in expected
        assert "c" in expected
        # T-2996's measured gap: at least one grammar frob.lang gained
        # since the old 3-item literal was written must be present.
        assert len(expected) > 3

    def test_cycle_lang_choices_match_registry(self) -> None:
        """`frob cycle --lang`'s choices equal the registry-derived set."""
        action = _top_level_action("cycle_lang")
        assert action.choices is not None
        assert tuple(action.choices) == self._expected_choices()

    def test_xref_lang_choices_match_registry(self) -> None:
        """`frob xref --lang`'s choices equal the registry-derived set."""
        action = _top_level_action("xref_lang")
        assert action.choices is not None
        assert tuple(action.choices) == self._expected_choices()

    def test_exports_lang_choices_match_registry(self) -> None:
        """`frob exports --lang`'s choices equal the registry-derived set."""
        action = _top_level_action("exports_lang")
        assert action.choices is not None
        assert tuple(action.choices) == self._expected_choices()

    def test_all_three_lang_flags_share_the_identical_choices_object(self) -> None:
        """Not just equal values -- the SAME derived tuple
        (`frob._cli_parsers._core._LANG_CHOICES`), so there is
        structurally only one place this list is ever computed, never
        three independently-evaluated copies that could drift apart
        again even if each individually still matched the registry at
        the moment this test was written."""
        from frob._cli_parsers._core import _LANG_CHOICES

        for dest in ("cycle_lang", "xref_lang", "exports_lang"):
            action = _top_level_action(dest)
            assert action.choices is _LANG_CHOICES, (
                f"{dest}'s --lang choices is not the shared _LANG_CHOICES object"
            )
