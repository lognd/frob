"""T-0756: the NEW-GATE-RULE ACCEPTANCE POLICY -- a ticket whose diff adds a
new `_KNOWN_GATE_RULES` entry (`src/frob/gates/__init__.py`) must carry a
bound before-fails/after-passes fixture acceptance criterion, or close/land
refuses. Each test is written to FAIL against the pre-T-0756 behavior (no
such check existed at all) and PASS after it.
"""
# frob:ticket T-0756

from __future__ import annotations

import subprocess
from datetime import date
from pathlib import Path

from frob.tickets import (
    Origin,
    Ticket,
    TicketError,
    TicketKind,
    TicketState,
    transition,
)
from frob.tickets._models import AcceptanceCriterion
from frob.tickets._new_gate_rule_acceptance import (
    missing_acceptance_for_new_rules,
    new_gate_rule_ids,
)
from frob.tickets._store import _serialize_ticket

_GATES_REL = "src/frob/gates/__init__.py"

_BASE_GATES_SOURCE = (
    "_KNOWN_GATE_RULES = frozenset(\n"
    "    {\n"
    '        "COV001",\n'
    '        "TEST001",\n'
    "    }\n"
    ")\n"
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=root, check=True, capture_output=True)


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")


def _commit_all(root: Path, message: str) -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)


def _write_gates_source(root: Path, source: str) -> None:
    path = root / _GATES_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


# frob:waive DUP001 reason="parallel per-domain test scaffolding across \
# test_evidence_integrity.py, \
# test_tickets_new_gate_rule_acceptance.py (2 sites) -- each file \
# exercises a structurally similar check for a distinct \
# domain/module with the same arrange-act shape; extracting would \
# blur which domain owns which check"
def _ticket(
    *,
    ticket_id: str = "T-0001",
    state: TicketState = TicketState.IN_PROGRESS,
    kind: TicketKind = TicketKind.SECURITY,
    evidence: tuple[str, ...] = ("tests/test_thing.py::test_it",),
    acceptance: tuple[AcceptanceCriterion, ...] = (),
    body: str = "## Description\nsomething\n\n## Done report\nDone.\n",
) -> Ticket:
    return Ticket(
        id=ticket_id,
        title="sample",
        state=state,
        kind=kind,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        evidence=evidence,
        acceptance=acceptance,
        body=body,
    )


def _write_ticket(root: Path, ticket: Ticket, slug: str = "sample") -> Path:
    tickets_dir = root / "tickets"
    tickets_dir.mkdir(parents=True, exist_ok=True)
    path = tickets_dir / f"{ticket.id}-{slug}.md"
    path.write_text(_serialize_ticket(ticket), encoding="utf-8")
    return path


class TestNewGateRuleIds:
    # frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_detects_freshly_added_rule_id  # noqa: E501
    def test_detects_freshly_added_rule_id(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write_gates_source(tmp_path, _BASE_GATES_SOURCE)
        _commit_all(tmp_path, "base gates")
        _write_gates_source(
            tmp_path,
            _BASE_GATES_SOURCE.replace(
                '        "TEST001",\n', '        "TEST001",\n        "NEWRULE001",\n'
            ),
        )
        found = new_gate_rule_ids(tmp_path, base_ref="main")
        assert found == ("NEWRULE001",)

    # frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_no_new_rules_is_empty  # noqa: E501
    def test_no_new_rules_is_empty(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write_gates_source(tmp_path, _BASE_GATES_SOURCE)
        _commit_all(tmp_path, "base gates")
        assert new_gate_rule_ids(tmp_path, base_ref="main") == ()

    # frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_unresolvable_base_ref_degrades_to_none  # noqa: E501
    def test_unresolvable_base_ref_degrades_to_none(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write_gates_source(tmp_path, _BASE_GATES_SOURCE)
        _commit_all(tmp_path, "base gates")
        assert new_gate_rule_ids(tmp_path, base_ref="does-not-exist") is None

    def test_no_gates_file_at_all_is_empty(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        (tmp_path / "README.md").write_text("hi\n", encoding="utf-8")
        _commit_all(tmp_path, "init")
        assert new_gate_rule_ids(tmp_path, base_ref="main") == ()


class TestMissingAcceptanceForNewRules:
    # frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules.test_flags_when_no_fixture_criterion_bound  # noqa: E501
    def test_flags_when_no_fixture_criterion_bound(self) -> None:
        ticket = _ticket(
            acceptance=(AcceptanceCriterion(text="GIVEN x THEN y", evidence=("a",)),)
        )
        assert missing_acceptance_for_new_rules(ticket, ("NEWRULE001",)) == (
            "NEWRULE001",
        )

    # frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules.test_clear_when_a_bound_fixture_criterion_exists  # noqa: E501
    def test_clear_when_a_bound_fixture_criterion_exists(self) -> None:
        ticket = _ticket(
            acceptance=(
                AcceptanceCriterion(
                    text=(
                        "GIVEN a fixture that FAILS frob check before the "
                        "change WHEN the fix lands THEN it PASSES"
                    ),
                    evidence=("tests/test_x.py::test_fixture",),
                ),
            )
        )
        assert missing_acceptance_for_new_rules(ticket, ("NEWRULE001",)) == ()

    def test_unbound_fixture_shaped_criterion_still_flags(self) -> None:
        # text matches fail/pass but carries NO evidence -- not actually
        # bound, must still flag.
        ticket = _ticket(
            acceptance=(
                AcceptanceCriterion(text="fails before, passes after", evidence=()),
            )
        )
        assert missing_acceptance_for_new_rules(ticket, ("NEWRULE001",)) == (
            "NEWRULE001",
        )

    # frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules.test_empty_new_rule_ids_is_always_clear  # noqa: E501
    def test_empty_new_rule_ids_is_always_clear(self) -> None:
        ticket = _ticket(acceptance=())
        assert missing_acceptance_for_new_rules(ticket, ()) == ()


class TestTransitionRefusesOnUnacceptedNewGateRule:
    """`transition(..., DONE)` (the direct `frob ticket close` path, and
    transitively `frob ticket land`'s finalize step) always runs the new-
    gate-rule acceptance check -- no injection needed, mirroring
    `TestTransitionRefusesOnLiveTrackerCitation`."""

    def test_close_refused_when_new_rule_has_no_fixture_acceptance(
        self, tmp_path: Path
    ) -> None:
        _init_repo(tmp_path)
        _write_gates_source(tmp_path, _BASE_GATES_SOURCE)
        ticket = _ticket(ticket_id="T-0756", acceptance=())
        _write_ticket(tmp_path, ticket)
        _commit_all(tmp_path, "base gates + ticket")
        _write_gates_source(
            tmp_path,
            _BASE_GATES_SOURCE.replace(
                '        "TEST001",\n', '        "TEST001",\n        "NEWRULE001",\n'
            ),
        )
        result = transition(tmp_path, "T-0756", TicketState.DONE)
        assert result.is_err
        assert result.danger_err == TicketError.NewGateRuleUnaccepted

    def test_close_allowed_when_fixture_acceptance_bound(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write_gates_source(tmp_path, _BASE_GATES_SOURCE)
        ticket = _ticket(
            ticket_id="T-0756",
            acceptance=(
                AcceptanceCriterion(
                    text=(
                        "GIVEN a fixture that FAILS frob check before this "
                        "change WHEN NEWRULE001 lands THEN it PASSES"
                    ),
                    evidence=("tests/test_thing.py::test_it",),
                ),
            ),
        )
        _write_ticket(tmp_path, ticket)
        _commit_all(tmp_path, "base gates + ticket")
        _write_gates_source(
            tmp_path,
            _BASE_GATES_SOURCE.replace(
                '        "TEST001",\n', '        "TEST001",\n        "NEWRULE001",\n'
            ),
        )
        result = transition(tmp_path, "T-0756", TicketState.DONE)
        assert result.is_ok

    def test_close_allowed_when_no_new_rule_added(self, tmp_path: Path) -> None:
        _init_repo(tmp_path)
        _write_gates_source(tmp_path, _BASE_GATES_SOURCE)
        ticket = _ticket(ticket_id="T-0700", acceptance=())
        _write_ticket(tmp_path, ticket)
        _commit_all(tmp_path, "base gates + ticket")
        result = transition(tmp_path, "T-0700", TicketState.DONE)
        assert result.is_ok
