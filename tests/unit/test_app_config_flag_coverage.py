"""T-2004: "a CLI flag can be parsed, tested, and silently dropped by
`from_external`'s allowlist -- tested is not reached" -- unit coverage for
`frob.app._config_external.find_dropped_cli_flags`, the static check that
catches this class rather than one instance of it.

Real incidents this generalizes: T-1995's `--ack-related` (a string field
never added to `_STRING_FIELDS`) and this very series' own T-1925
`sys_threats_boundary` (a positional never added at all) -- both parsed
correctly, both had passing unit tests (each constructed `AppConfig`
directly, bypassing argparse), and both silently never reached the
runner they configured. `find_dropped_cli_flags` is built to make BOTH
classes of gap (a name present in the wrong tuple's shape, and a name
present in NO tuple) show up the same way: absent from the forwarded
set.
"""

from __future__ import annotations

import argparse

from frob.__main__ import _build_parser
from frob.app import _config_external as ce
from frob.app.config import AppConfig


class _FakeConfig:
    """A minimal `config_cls`-shaped test double: `find_dropped_cli_flags`
    only ever reads `.model_fields` (a pydantic v2 convention), so a
    plain class attribute is enough to reconstruct T-1995's state without
    touching the real, 340-field `AppConfig`."""

    model_fields = {"ack_related": None, "other_field": None}


def _reconstructed_parser() -> argparse.ArgumentParser:
    """A tiny synthetic parser mirroring T-1995's actual shape: one
    subcommand (`ticket`) with a `--ack-related` flag whose `dest`
    matches a real field on `_FakeConfig`, plus one flag `--other` that
    IS correctly forwarded -- so the check must flag exactly the one
    genuinely-dropped flag, not everything."""
    parser = argparse.ArgumentParser(prog="frob")
    sub = parser.add_subparsers(dest="subcommand")
    ticket_p = sub.add_parser("ticket")
    ticket_p.add_argument("--ack-related", dest="ack_related", action="store_true")
    ticket_p.add_argument("--other", dest="other_field", action="store_true")
    return parser


class TestFindDroppedCliFlags:
    # frob:tests src/frob/app/_config_external.py::find_dropped_cli_flags kind="unit"
    def test_reconstructed_t1995_state_is_caught(self):
        """T-2004 acceptance criterion 1, half 1: a flag present in
        argparse and on the config's field set, but absent from the
        forwarding set, is reported -- through the REAL `find_dropped_
        cli_flags`, not a reimplementation of its set arithmetic."""
        parser = _reconstructed_parser()
        # Mirrors _config_external's own tuple shape, but deliberately
        # omits ack_related (the T-1995 bug) while including
        # other_field (the correctly-forwarded sibling) and subcommand
        # (always ad-hoc-forwarded in the real module).
        narrow_forwarded = frozenset({"other_field", "subcommand"})
        dropped = ce.find_dropped_cli_flags(
            parser, _FakeConfig, forwarded=narrow_forwarded
        )
        assert dropped == frozenset({"ack_related"})

    # frob:tests src/frob/app/_config_external.py::find_dropped_cli_flags kind="unit"
    def test_reconstructed_state_is_clean_once_the_field_is_added(self):
        """T-2004 acceptance criterion 1, half 2: adding `ack_related` to
        the forwarded set (the real fix's shape) clears the finding --
        proves the check is a real ratchet, not a permanently-red probe."""
        parser = _reconstructed_parser()
        fixed_forwarded = frozenset({"other_field", "ack_related", "subcommand"})
        dropped = ce.find_dropped_cli_flags(
            parser, _FakeConfig, forwarded=fixed_forwarded
        )
        assert dropped == frozenset()

    # frob:tests src/frob/app/_config_external.py::find_dropped_cli_flags kind="unit"
    def test_flag_with_no_matching_config_field_is_not_flagged(self):
        """A raw-argv-dispatched subcommand's own flags (`bind`/`agent`/
        `worktree sweep` in the real CLI) have no matching `AppConfig`
        field at all -- `find_dropped_cli_flags` must not report them,
        since they were never meant to reach the model in the first
        place (T-2004's own real-tree measurement confirmed this: `bind_
        json`/`agent_env_path`/`worktree_sweep_*` all fall out of the
        candidate set here, not the forwarded set)."""
        parser = argparse.ArgumentParser(prog="frob")
        parser.add_argument("--bind-only", dest="bind_only_flag", action="store_true")
        found = ce.find_dropped_cli_flags(parser, _FakeConfig)
        assert found == frozenset()

    # frob:tests src/frob/app/_config_external.py::find_dropped_cli_flags kind="unit"
    def test_help_and_version_are_never_flagged(self):
        """`-h`/`--version` have real argparse dests but no `AppConfig`
        field -- excluded via the same candidate-intersection as the
        raw-argv-dispatch case above, not a special-cased name list."""
        parser = argparse.ArgumentParser(prog="frob")
        parser.add_argument("--version", action="version", version="1.0")
        found = ce.find_dropped_cli_flags(parser, _FakeConfig)
        assert found == frozenset()

    # frob:tests src/frob/app/_config_external.py::find_dropped_cli_flags kind="unit"
    def test_current_tree_has_zero_dropped_flags(self):
        """T-2004 acceptance criterion 3, measured (not assumed): the
        REAL `frob` parser against the REAL `AppConfig` reports zero
        dropped flags -- this ratchets the finding at zero going
        forward; a future PR that adds a flag without a matching
        `_apply_*_fields`/`_AD_HOC_FORWARDED_FIELDS` entry fails this
        test immediately, not "whenever someone next stumbles into the
        file" (T-1995's actual discovery path)."""
        parser = _build_parser()
        candidates = ce._all_parser_dests(parser) & frozenset(AppConfig.model_fields)
        dropped = ce.find_dropped_cli_flags(parser, AppConfig)
        # Denominator disclosure (T-2004 acceptance criterion 3): report
        # how many real CLI flags this check actually examined, not just
        # the pass/fail bit -- a green check over zero candidates would
        # be a vacuous, worthless ratchet.
        assert len(candidates) > 300, (
            f"candidate flag count collapsed to {len(candidates)} -- "
            "the check may no longer be examining the real parser/model"
        )
        assert dropped == frozenset(), (
            f"{len(dropped)}/{len(candidates)} CLI flag(s) parse but never "
            f"reach AppConfig: {sorted(dropped)}"
        )


# frob:ticket T-2387
class TestT2320RuffFlagsReachAppConfig:
    """T-2387 regression: T-2320's three ruff-substage flags
    (`--skip-ruff-check`, `--skip-ruff-format`, `--fix-ruff`) parsed
    correctly into argparse's Namespace but were never added to
    `_BOOL_FLAGS`, so `_apply_bool_flags` silently dropped all three
    before `AppConfig(**d)` -- the field always kept its `False` default
    regardless of the CLI flag. Same shape as T-0749's `TestAcceptsCliWiring`:
    goes through the REAL parser and `AppConfig.from_external`, not a
    direct `AppConfig(...)` construction, so this exact class of gap
    (parses + has coverage on the function it configures, but the config
    layer never carries it there) cannot regress silently again."""

    def test_from_external_carries_all_three_ruff_flags_from_parsed_argv(
        self,
    ) -> None:
        """Each of the three T-2320 flags, parsed via the real CLI
        parser, reaches its corresponding `AppConfig` field as `True`."""
        from pathlib import Path

        from frob.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            [
                "check",
                "--skip-ruff-check",
                "--skip-ruff-format",
                "--fix-ruff",
            ]
        )
        cfg = AppConfig.from_external(args, Path("frob.toml"))
        assert cfg.check_skip_ruff_check is True
        assert cfg.check_skip_ruff_format is True
        assert cfg.check_ruff_fix is True

    def test_absent_ruff_flags_default_false(self) -> None:
        """Without the flags, the fields stay at their `False` default --
        confirms the previous test is really observing the flag's
        effect, not a field that was always `True`."""
        from pathlib import Path

        from frob.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(["check"])
        cfg = AppConfig.from_external(args, Path("frob.toml"))
        assert cfg.check_skip_ruff_check is False
        assert cfg.check_skip_ruff_format is False
        assert cfg.check_ruff_fix is False
