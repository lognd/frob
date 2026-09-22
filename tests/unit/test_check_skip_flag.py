"""`frob check --skip STAGE[,STAGE]` (T-4524): the unified, repeatable,
comma-splittable flag that replaces the 20 individual `--skip-<stage>`
flags, mirroring `--only`'s stage vocabulary.

Covers all three acceptance criteria:
  1. `--skip ruff,ty` skips the same stages `--skip-ruff --skip-ty` did.
  2. Every old `--skip-<stage>` spelling still works, but is hidden from
     the rendered `--help` block and DEPRECATED-tagged.
  3. `--skip` and `--only` naming the same stage refuses, naming the stage.
"""

from __future__ import annotations

import pytest

from frob._cli_parsers._check import _SKIP_STAGE_FIELDS
from frob._cli_parsers._root import _build_parser
from frob.app.check_runner import _refuse_skip_only_conflict
from frob.app.config import AppConfig


def _parse(argv: list[str]):
    """Parse `argv` through the real top-level parser (T-4524 tests)."""
    return _build_parser().parse_args(argv)


class TestUnifiedSkipFlag:
    """Criterion 1: `--skip STAGE[,STAGE]` mirrors the legacy flags."""

    def test_comma_split_sets_both_legacy_attributes(self) -> None:
        """`--skip ruff,ty` sets the same `check_skip_ruff`/`check_skip_ty`
        namespace attributes `--skip-ruff --skip-ty` did."""
        unified = _parse(["check", "--skip", "ruff,ty"])
        legacy = _parse(["check", "--skip-ruff", "--skip-ty"])
        assert unified.check_skip_ruff == legacy.check_skip_ruff is True
        assert unified.check_skip_ty == legacy.check_skip_ty is True

    def test_repeatable(self) -> None:
        """`--skip ruff --skip ty` (two separate occurrences) also works."""
        args = _parse(["check", "--skip", "ruff", "--skip", "ty"])
        assert args.check_skip_ruff is True
        assert args.check_skip_ty is True

    def test_whitespace_around_commas_is_trimmed(self) -> None:
        """`--skip "ruff, ty"` still resolves both stage names."""
        args = _parse(["check", "--skip", "ruff, ty"])
        assert args.check_skip_ruff is True
        assert args.check_skip_ty is True

    def test_unrecognized_stage_refuses(self, capsys) -> None:
        """An unknown stage name is a usage error (exit 2), naming the
        stage and the known vocabulary -- never a silent no-op."""
        with pytest.raises(SystemExit) as exc_info:
            _parse(["check", "--skip", "bogus"])
        assert exc_info.value.code == 2
        stderr = capsys.readouterr().err
        assert "bogus" in stderr

    def test_skip_ruff_stage_covers_both_ruff_check_and_ruff_format(self) -> None:
        """`--skip ruff` (the bundle) sets only `check_skip_ruff` -- the
        same single legacy flag `--skip-ruff` set -- and downstream
        (`frob.check._python_skip_flags`) ORs it with the split
        `check_skip_ruff_check`/`check_skip_ruff_format` flags, so a bare
        `--skip ruff` skips both stages exactly as `--skip-ruff` always
        did (T-2320's pre-existing OR, unchanged by this ticket)."""
        args = _parse(["check", "--skip", "ruff"])
        assert args.check_skip_ruff is True
        assert args.check_skip_ruff_check is False
        assert args.check_skip_ruff_format is False

    def test_every_legacy_stage_name_resolves(self) -> None:
        """Every one of the 20 legacy stage names is in the unified
        vocabulary and sets a real, distinct `AppConfig` field."""
        assert len(_SKIP_STAGE_FIELDS) == 20
        cfg_fields = set(AppConfig.model_fields)
        for stage, field in _SKIP_STAGE_FIELDS.items():
            assert field in cfg_fields, f"{stage!r} -> {field!r} not on AppConfig"


class TestLegacyFlagsDeprecated:
    """Criterion 2: legacy `--skip-<stage>` flags still work but are
    hidden from `--help` and DEPRECATED-tagged."""

    @pytest.mark.parametrize(
        "flag",
        [
            "--skip-ruff",
            "--skip-ruff-check",
            "--skip-ruff-format",
            "--skip-ty",
            "--skip-arch",
            "--skip-cycle",
            "--skip-dup",
            "--skip-bind",
            "--skip-exports",
            "--skip-gates",
            "--skip-tests",
            "--skip-build",
            "--skip-clang-tidy",
            "--skip-clang-format",
            "--skip-cargo-check",
            "--skip-clippy",
            "--skip-fmt",
            "--skip-tsc",
            "--skip-eslint",
            "--skip-prettier",
        ],
    )
    def test_legacy_flag_still_works(self, flag: str) -> None:
        """Each of the 20 legacy flags still parses without error (one
        release of back-compat, T-4524)."""
        _parse(["check", flag])

    def test_help_block_lists_20_fewer_flags(self, capsys) -> None:
        """`frob check --help`'s rendered options/usage text names none of
        the 20 legacy `--skip-<stage>` flags any more."""
        with pytest.raises(SystemExit):
            _parse(["check", "--help"])
        out = capsys.readouterr().out
        rendered_flags = set(out.split())
        for stage, _field in _SKIP_STAGE_FIELDS.items():
            legacy_flag = f"--skip-{stage}"
            assert legacy_flag not in rendered_flags, (
                f"{legacy_flag} still in --help output"
            )
        assert "--skip STAGE" in out

    def test_legacy_action_help_is_deprecated_tagged(self) -> None:
        """Every legacy `--skip-<stage>` action's real (unrendered) help
        string starts with DEPRECATED, so it stays discoverable to
        anything introspecting the parser directly.

        `argparse._SubParsersAction.choices` and `ArgumentParser.
        _subparsers`/`_group_actions` are typed loosely (`dict | None`,
        `_ArgumentGroup | None`) at the stub level even though they are
        always populated once `add_subparsers()`/`add_parser()` have
        actually run -- narrowing asserts for `ty`, same precedent as
        `tests/unit/test_cli_hygiene_checklist_t1556.py`."""
        root = _build_parser()
        assert root._subparsers is not None
        check_action = next(
            action
            for action in root._subparsers._group_actions
            if action.choices is not None and "check" in action.choices
        )
        assert check_action.choices is not None
        check_p = dict(check_action.choices)["check"]
        seen_stages: set[str] = set()
        for action in check_p._actions:
            opt = next(
                (o for o in getattr(action, "option_strings", []) if o != "--skip"),
                None,
            )
            if opt and opt.startswith("--skip-"):
                assert isinstance(action.help, str)
                assert action.help.startswith("DEPRECATED")
                seen_stages.add(opt)
        assert len(seen_stages) == 20


# frob:tests src/frob/app/check_runner.py::_refuse_skip_only_conflict
class TestSkipOnlyConflict:
    """Criterion 3: `--skip` and `--only` naming the same stage refuses."""

    def test_conflicting_stage_detected(self) -> None:
        """`--only ruff` plus `check_skip_ruff=True` conflict on 'ruff'."""
        cfg = AppConfig(check_only=["ruff"], check_skip_ruff=True)
        assert _refuse_skip_only_conflict(cfg) == "ruff"

    def test_disjoint_stages_do_not_conflict(self) -> None:
        """`--only ty` plus `--skip ruff` name different stages: no
        conflict."""
        cfg = AppConfig(check_only=["ty"], check_skip_ruff=True)
        assert _refuse_skip_only_conflict(cfg) is None

    def test_no_only_never_conflicts(self) -> None:
        """No `--only` at all means nothing to conflict with."""
        cfg = AppConfig(check_skip_ruff=True)
        assert _refuse_skip_only_conflict(cfg) is None

    def test_cli_refuses_with_stage_named(self, tmp_path, caplog) -> None:
        """`run(cfg)` exits 1 and logs the conflicting stage by name when
        `--skip` and `--only` overlap."""
        import logging

        from frob.app.check_runner import run

        cfg = AppConfig(check_path=tmp_path, check_only=["ruff"], check_skip_ruff=True)
        with caplog.at_level(logging.ERROR):
            with pytest.raises(SystemExit) as exc_info:
                run(cfg)
        assert exc_info.value.code == 1
        assert any("ruff" in rec.message for rec in caplog.records)
