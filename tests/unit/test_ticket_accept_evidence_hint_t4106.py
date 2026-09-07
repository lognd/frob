"""T-4106: `frob ticket accept` gives a bare argparse "unrecognized
arguments" error when an agent reaches for an evidence-binding flag on it
-- three consumer agents in a row (F-305) reached for `--evidence-cmd`/
`--accepts` on `accept` (the verb that manages acceptance CRITERION TEXT)
when the flag they wanted lives on `frob ticket evidence` (the verb that
BINDS evidence to a criterion index).

Covers all three of the ticket's own fixtures:
  - MUST-FIRE: an evidence-shaped unrecognized flag on `accept` names
    `frob ticket evidence` and its `--accepts` index flag.
  - MUST-STAY-QUIET: an unrelated unrecognized flag gets the ordinary
    argparse error, unchanged.
  - THIRD FIXTURE: a correct invocation of either verb (including
    `--help`) is byte-for-byte unaffected.

Plus the documented mirror direction (`--criterion`/`--criterion-file`/
`--amend` trapped on `evidence`, hinting back to `accept`) and the
documented non-handling of `--remove`/`--reason` (both already exist on
`evidence` with a different meaning, so trapping them would be exactly
the aliasing this ticket rules out).
"""

from __future__ import annotations

import pytest

from frob import __main__ as main_module


class TestAcceptEvidenceFlagHint:
    """MUST-FIRE fixture: an evidence-shaped unrecognized flag on
    `accept` produces a message naming `frob ticket evidence` and
    `--accepts`."""

    @pytest.mark.parametrize(
        "flag,value", [("--evidence-cmd", "pytest foo"), ("--accepts", "3")]
    )
    def test_evidence_flag_on_accept_names_the_evidence_verb(
        self, flag: str, value: str, capsys
    ) -> None:
        parser = main_module._build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["ticket", "accept", "T-0001", flag, value])
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "frob ticket evidence" in err
        assert "--accepts" in err

    def test_bare_evidence_flag_on_accept_names_the_evidence_verb(self, capsys) -> None:
        """`--evidence` is not a real flag anywhere, but is a plausible
        guess (it matches the confused mental model this ticket
        describes) -- trapped the same way as the two real flags above."""
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "accept", "T-0001", "--evidence"])
        err = capsys.readouterr().err
        assert "frob ticket evidence" in err


class TestAcceptUnrelatedFlagUnchanged:
    """MUST-STAY-QUIET fixture: an unrecognized flag unrelated to
    evidence gets the ordinary argparse error, with no evidence-hint
    text appended."""

    def test_unrelated_unrecognized_flag_gets_the_ordinary_error(self, capsys) -> None:
        parser = main_module._build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(["ticket", "accept", "T-0001", "--bogus-flag", "x"])
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "unrecognized arguments: --bogus-flag" in err
        assert "frob ticket evidence" not in err


class TestCorrectInvocationsUnaffected:
    """THIRD FIXTURE: a correct invocation of either verb is byte-for-
    byte unaffected -- the trap flags are `argparse.SUPPRESS`-hidden and
    never legitimately used by a real invocation."""

    def test_accept_help_does_not_list_the_trap_flags(self, capsys) -> None:
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "accept", "--help"])
        out = capsys.readouterr().out
        assert "--evidence-cmd" not in out
        assert "--accepts" not in out
        assert "--evidence " not in out

    def test_evidence_help_does_not_list_the_trap_flags(self, capsys) -> None:
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "evidence", "--help"])
        out = capsys.readouterr().out
        assert "--criterion" not in out
        assert "--amend" not in out

    def test_accept_plain_criterion_append_still_parses(self) -> None:
        """A real, correct `accept --criterion` invocation must still
        parse exactly as before -- the trap flags are additive, never a
        behavior change on the flags `accept` already owned."""
        parser = main_module._build_parser()
        ns = parser.parse_args(
            ["ticket", "accept", "T-0001", "--criterion", "does the thing"]
        )
        assert ns.ticket_accept_criterion == ["does the thing"]

    def test_evidence_plain_node_id_still_parses(self) -> None:
        """A real, correct `evidence` invocation (positional node id +
        --accepts) must still parse exactly as before."""
        parser = main_module._build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "evidence",
                "T-0001",
                "tests/test_x.py::test_y",
                "--accepts",
                "1",
            ]
        )
        assert ns.ticket_evidence_ids == ["tests/test_x.py::test_y"]
        assert ns.ticket_accepts == [1]


class TestEvidenceCriterionFlagHintMirror:
    """The documented mirror direction: `--criterion`/`--criterion-file`/
    `--amend` on `evidence` hint back to `accept`."""

    @pytest.mark.parametrize(
        "flag,value",
        [("--criterion", "text"), ("--criterion-file", "/tmp/x"), ("--amend", "1")],
    )
    def test_criterion_flag_on_evidence_names_the_accept_verb(
        self, flag: str, value: str, capsys
    ) -> None:
        parser = main_module._build_parser()
        with pytest.raises(SystemExit):
            parser.parse_args(["ticket", "evidence", "T-0001", flag, value])
        err = capsys.readouterr().err
        assert "frob ticket accept" in err

    def test_remove_on_evidence_is_not_trapped_it_is_a_real_flag(self) -> None:
        """`--remove` already exists on `evidence` with ITS OWN meaning
        (drop an evidence id) -- deliberately not trapped, since a real
        flag with a different meaning is not an unrecognized argument to
        attach a hint to (that would mean aliasing, which this ticket
        rules out). Confirms it still parses as evidence's own flag."""
        parser = main_module._build_parser()
        ns = parser.parse_args(
            ["ticket", "evidence", "T-0001", "--remove", "some::node::id"]
        )
        assert ns.ticket_evidence_remove == "some::node::id"
