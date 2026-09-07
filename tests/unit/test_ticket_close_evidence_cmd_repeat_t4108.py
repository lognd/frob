"""T-4108: `frob ticket close` silently kept only the LAST `--evidence-cmd`
while accumulating every `--accepts` index (F-306, T-0265) -- a caller
pairing two commands with two criteria got one command bound to both, and
the close SUCCEEDED with a false record (worse than a dropped flag, which
would have failed loudly on an unbound criterion).

The mechanism is an argparse asymmetry in
`src/frob/_cli_parsers/_ticket/_closeout.py`: `--evidence-cmd` had no
`action=` (last-wins) while `--accepts` is `action="append"`
(accumulates). Three sites define this exact flag pair -- `close`,
`reverify` (documented as sharing close's flags verbatim), and `evidence`
itself (the identical asymmetry, independently confirmed) -- all three
now refuse a second `--evidence-cmd` via `_RefuseRepeatedEvidenceCmd`
rather than silently dropping the first.

Covers all three of the ticket's own fixtures, enumerated per site:
  - MUST-FIRE: two `--evidence-cmd` values in one invocation are refused,
    naming the per-call `frob ticket evidence` path.
  - MUST-STAY-QUIET: one `--evidence-cmd` with several `--accepts` still
    binds that one command to all of them, unchanged.
  - THIRD FIXTURE: every site sharing this flag block (close, reverify,
    evidence) is proven to refuse identically, not merely assumed to.
"""

from __future__ import annotations

import pytest

from frob import __main__ as main_module


class TestSecondEvidenceCmdIsRefused:
    """MUST-FIRE fixture, proven at all three sites (THIRD FIXTURE) --
    `close`/`reverify`/`evidence` each refuse a second `--evidence-cmd`
    naming the per-call `frob ticket evidence` path."""

    @pytest.mark.parametrize(
        "argv",
        [
            [
                "ticket",
                "close",
                "T-0001",
                "--evidence-cmd",
                "cmd A",
                "--accepts",
                "1",
                "--evidence-cmd",
                "cmd B",
                "--accepts",
                "2",
            ],
            [
                "ticket",
                "reverify",
                "T-0001",
                "--evidence-cmd",
                "cmd A",
                "--accepts",
                "1",
                "--evidence-cmd",
                "cmd B",
                "--accepts",
                "2",
            ],
            [
                "ticket",
                "evidence",
                "T-0001",
                "--evidence-cmd",
                "cmd A",
                "--evidence-cmd",
                "cmd B",
            ],
        ],
        ids=["close", "reverify", "evidence"],
    )
    def test_second_evidence_cmd_refuses_naming_the_evidence_verb(
        self, argv: list[str], capsys
    ) -> None:
        parser = main_module._build_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(argv)
        assert exc_info.value.code == 2
        err = capsys.readouterr().err
        assert "given more than once" in err
        assert "frob ticket evidence" in err
        assert "--accepts" in err


class TestOneCommandManyAcceptsUnchanged:
    """MUST-STAY-QUIET fixture, proven at all three sites -- a single
    `--evidence-cmd` bound to several `--accepts` indexes still parses
    exactly as before; this is a legitimate, supported use and must not
    regress."""

    def test_close_one_command_several_accepts(self) -> None:
        parser = main_module._build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "close",
                "T-0001",
                "--evidence-cmd",
                "pytest foo",
                "--accepts",
                "1",
                "--accepts",
                "2",
            ]
        )
        assert ns.ticket_evidence_cmd == "pytest foo"
        assert ns.ticket_accepts == [1, 2]

    def test_reverify_one_command_several_accepts(self) -> None:
        parser = main_module._build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "reverify",
                "T-0001",
                "--evidence-cmd",
                "pytest foo",
                "--accepts",
                "1",
                "--accepts",
                "2",
            ]
        )
        assert ns.ticket_evidence_cmd == "pytest foo"
        assert ns.ticket_accepts == [1, 2]

    def test_evidence_one_command_several_accepts(self) -> None:
        parser = main_module._build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "evidence",
                "T-0001",
                "--evidence-cmd",
                "pytest foo",
                "--accepts",
                "1",
                "--accepts",
                "2",
            ]
        )
        assert ns.ticket_evidence_cmd == "pytest foo"
        assert ns.ticket_accepts == [1, 2]


class TestUnaffectedFlagsStillAccumulate:
    """`--evidence`/positional node-ids and `--accepts` are untouched by
    this fix -- only `--evidence-cmd` gained a refusal action."""

    def test_close_evidence_node_ids_still_accumulate(self) -> None:
        parser = main_module._build_parser()
        ns = parser.parse_args(
            [
                "ticket",
                "close",
                "T-0001",
                "--evidence",
                "tests/a.py::t1",
                "--evidence",
                "tests/b.py::t2",
            ]
        )
        assert ns.ticket_evidence_ids == ["tests/a.py::t1", "tests/b.py::t2"]

    def test_evidence_positional_node_ids_still_accumulate(self) -> None:
        parser = main_module._build_parser()
        ns = parser.parse_args(
            ["ticket", "evidence", "T-0001", "tests/a.py::t1", "tests/b.py::t2"]
        )
        assert ns.ticket_evidence_ids == ["tests/a.py::t1", "tests/b.py::t2"]
