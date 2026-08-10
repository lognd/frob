"""T-1929: the public entrypoints `frob.gates.bug_repro_outcome_at_ref` and
`frob.gates.designated_repro_test` are thin wrappers around
`frob.gates._mutation_evidence`'s private `_bug_repro_outcome_at_ref`/
`_designated_repro_test` -- they must forward exactly, with no re-
implementation of the classification or resolution logic (DO NOT DUPLICATE
BUG002's machinery). These tests pin the wrapping, not the underlying
classification (`tests/test_gates_mutation_evidence.py::TestBugReproAtRef`
already covers that in depth)."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

from frob.gates import BugReproOutcome, bug_repro_outcome_at_ref, designated_repro_test
from frob.gates._mutation_evidence import _BugReproOutcome
from frob.tickets._models import Origin, Ticket, TicketKind, TicketState


def _ticket(**overrides: object) -> Ticket:
    """Build a `bug`-kind `Ticket` with sane defaults, `.model_copy`d with
    `overrides` -- avoids a loosely-typed `dict[str, object]` splat into
    `Ticket(**...)`, which `ty` cannot narrow field-by-field."""
    base = Ticket(
        id="T-1929",
        title="sample",
        state=TicketState.IN_PROGRESS,
        kind=TicketKind.BUG,
        origin=Origin.HUMAN,
        created=date(2026, 1, 1),
        blocked_by=(),
        parent=None,
        scope=("m.py",),
        evidence=("tests/test_x.py::test_repro", "tests/test_y.py::test_other"),
        attachments=(),
        body="## Description\nsomething\n",
    )
    return base.model_copy(update=overrides)


class TestBugReproOutcomeAtRefPublic:
    def test_wraps_the_private_classifier(self, tmp_path: Path) -> None:
        # frob:tests tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic.test_wraps_the_private_classifier  # noqa: E501
        with patch(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.FAILED_AT_PARENT,
        ) as mocked:
            outcome = bug_repro_outcome_at_ref(
                tmp_path, "tests/test_x.py::test_x", "main"
            )
        mocked.assert_called_once_with(tmp_path, "tests/test_x.py::test_x", "main")
        assert outcome is _BugReproOutcome.FAILED_AT_PARENT

    def test_public_alias_is_the_same_enum(self) -> None:
        # frob:tests tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic.test_public_alias_is_the_same_enum  # noqa: E501
        assert BugReproOutcome is _BugReproOutcome

    def test_default_base_ref_is_main(self, tmp_path: Path) -> None:
        # frob:tests tests/gates/test_bug_repro_at_ref_public.py::TestBugReproOutcomeAtRefPublic.test_default_base_ref_is_main  # noqa: E501
        with patch(
            "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
            return_value=_BugReproOutcome.NO_VERDICT,
        ) as mocked:
            bug_repro_outcome_at_ref(tmp_path, "tests/test_x.py::test_x")
        mocked.assert_called_once_with(tmp_path, "tests/test_x.py::test_x", "main")


class TestDesignatedReproTestPublic:
    def test_wraps_the_private_resolver(self) -> None:
        # frob:tests tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic.test_wraps_the_private_resolver  # noqa: E501
        ticket = _ticket(designated_repro_test="tests/test_y.py::test_other")
        assert designated_repro_test(ticket) == "tests/test_y.py::test_other"

    def test_falls_back_to_first_pytest_node_id(self) -> None:
        # frob:tests tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic.test_falls_back_to_first_pytest_node_id  # noqa: E501
        ticket = _ticket()
        assert designated_repro_test(ticket) == "tests/test_x.py::test_repro"

    def test_no_evidence_is_none(self) -> None:
        # frob:tests tests/gates/test_bug_repro_at_ref_public.py::TestDesignatedReproTestPublic.test_no_evidence_is_none  # noqa: E501
        ticket = _ticket(evidence=())
        assert designated_repro_test(ticket) is None
