"""T-1929: `frob ticket evidence --designate-repro` validates against the
ticket's parent commit AT DESIGNATE TIME (requirement A) and `--check-repro`
exposes the same classification on demand without mutating anything
(requirement B). Both channels go through the SAME shared entrypoint,
`frob.gates.bug_repro_outcome_at_ref` -- these tests mock that one function
to drive all three(+)-way outcomes, matching how
`tests/test_gates_mutation_evidence.py::TestBugReproViolations` already
mocks `_bug_repro_outcome_at_ref` for the land/close-time gate, so nothing
here spawns a real subprocess or `git worktree add`.

These are the tests acceptance criterion 4 requires FAIL BEFORE the T-1929
fix: before `_validate_designate_repro_at_parent` existed, `--designate-
repro` unconditionally wrote the designation (this file's
`test_refuses_passed_at_parent`/`test_refuses_no_verdict` would have found
no refusal at all), and before `--check-repro` existed there was no on-
demand path (`TestEvidenceCheckRepro` would have failed to even parse the
CLI flag)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from typani import Ok

from frob.app.config import AppConfig
from frob.app.ticket_runner import _evidence, _new
from frob.gates._mutation_evidence import _BugReproOutcome
from frob.testing._models import CollectedTests
from frob.tickets import load_queue


def _patch_collect(monkeypatch: pytest.MonkeyPatch, node_ids: frozenset[str]) -> None:
    """Same hermetic stand-in `tests/test_tickets_evidence_cli.py` uses:
    `collect_python_tests` returns `node_ids` without spawning pytest."""
    import frob.testing as testing_mod

    monkeypatch.setattr(
        testing_mod,
        "collect_python_tests",
        lambda root: Ok(CollectedTests(node_ids=node_ids)),
    )


def _patch_passing(monkeypatch: pytest.MonkeyPatch) -> None:
    """Same hermetic stand-in `tests/test_tickets_evidence_cli.py` uses:
    every id asked about is reported passing, no real subprocess."""
    import frob.app.ticket_runner as runner_mod

    monkeypatch.setattr(
        runner_mod,
        "_verify_ids_passing",
        lambda root, node_ids, python_collected, rust_collected, runners: frozenset(
            node_ids
        ),
    )


def _test_make_bug_ticket(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    node_id: str = "tests/x.py::test_a",
) -> str:
    """Create a `bug`-kind ticket with `node_id` already bound as evidence,
    return its id -- the shared setup every test in this file starts from."""
    _patch_collect(monkeypatch, frozenset({node_id}))
    _patch_passing(monkeypatch)
    cfg = AppConfig(
        ticket_command="new",
        ticket_title="designate repro parent-check",
        ticket_kind="bug",
        ticket_path=tmp_path,
        ticket_evidence_ids=[node_id],
    )
    _new(tmp_path, cfg)
    return "T-0001"


# frob:ticket T-1929
class TestValidateDesignateReproAtParent:
    """Requirement A: `--designate-repro` refuses unless the node id
    genuinely FAILED_AT_PARENT."""

    def test_refuses_passed_at_parent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_refuses_passed_at_parent  # noqa: E501
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.PASSED_AT_PARENT,
            ),
        ):
            designate_cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_designate_repro="tests/x.py::test_a",
            )
            with pytest.raises(SystemExit) as exc:
                _evidence(tmp_path, designate_cfg)
        assert exc.value.code == 1
        ticket = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        assert ticket.designated_repro_test is None

    def test_refuses_no_verdict(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_refuses_no_verdict  # noqa: E501
        # T-1907's original shape: the parent-commit run could not even
        # COLLECT (pytest exit 5) -- this must never be treated as a pass.
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.NO_VERDICT,
            ),
        ):
            designate_cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_designate_repro="tests/x.py::test_a",
            )
            with pytest.raises(SystemExit) as exc:
                _evidence(tmp_path, designate_cfg)
        assert exc.value.code == 1
        ticket = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        assert ticket.designated_repro_test is None

    def test_accepts_failed_at_parent(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_accepts_failed_at_parent  # noqa: E501
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.FAILED_AT_PARENT,
            ),
        ):
            designate_cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_designate_repro="tests/x.py::test_a",
            )
            _evidence(tmp_path, designate_cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        assert ticket.designated_repro_test == "tests/x.py::test_a"

    def test_force_overrides_loudly(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_force_overrides_loudly  # noqa: E501
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.PASSED_AT_PARENT,
            ),
        ):
            designate_cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_designate_repro="tests/x.py::test_a",
                ticket_designate_repro_force=True,
            )
            _evidence(tmp_path, designate_cfg)
        ticket = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        assert ticket.designated_repro_test == "tests/x.py::test_a"

    def test_non_bug_kind_skips_the_check(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestValidateDesignateReproAtParent.test_non_bug_kind_skips_the_check  # noqa: E501
        node_id = "tests/x.py::test_a"
        _patch_collect(monkeypatch, frozenset({node_id}))
        _patch_passing(monkeypatch)
        new_cfg = AppConfig(
            ticket_command="new",
            ticket_title="feature-kind designation",
            ticket_kind="feature",
            ticket_path=tmp_path,
            ticket_evidence_ids=[node_id],
        )
        _new(tmp_path, new_cfg)
        with patch("frob.gates._mutation_evidence._bug_repro_outcome_at_ref") as mocked:
            designate_cfg = AppConfig(
                ticket_command="evidence",
                ticket_id="T-0001",
                ticket_path=tmp_path,
                ticket_designate_repro=node_id,
            )
            _evidence(tmp_path, designate_cfg)
        mocked.assert_not_called()
        ticket = load_queue(tmp_path).danger_ok.tickets["T-0001"]
        assert ticket.designated_repro_test == node_id


# frob:ticket T-1929
class TestEvidenceCheckRepro:
    """Requirement B: `--check-repro` runs the same classification on
    demand, mutates nothing."""

    def test_reports_failed_at_parent_exit0(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_reports_failed_at_parent_exit0  # noqa: E501
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.FAILED_AT_PARENT,
            ),
        ):
            cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_check_repro="tests/x.py::test_a",
            )
            # A clean check returns normally, no SystemExit.
            _evidence(tmp_path, cfg)
        # Nothing was mutated by the read-only channel.
        ticket = load_queue(tmp_path).danger_ok.tickets[ticket_id]
        assert ticket.designated_repro_test is None

    def test_reports_passed_at_parent_exit1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_reports_passed_at_parent_exit1  # noqa: E501
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.PASSED_AT_PARENT,
            ),
        ):
            cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_check_repro="tests/x.py::test_a",
            )
            with pytest.raises(SystemExit) as exc:
                _evidence(tmp_path, cfg)
        assert exc.value.code == 1

    def test_reports_no_verdict_exit1(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_reports_no_verdict_exit1  # noqa: E501
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.NO_VERDICT,
            ),
        ):
            cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_check_repro="tests/x.py::test_a",
            )
            with pytest.raises(SystemExit) as exc:
                _evidence(tmp_path, cfg)
        assert exc.value.code == 1

    # frob:ticket T-2025
    def test_reports_test_absent_at_parent_exit1_with_explanatory_message(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_reports_test_absent_at_parent_exit1_with_explanatory_message  # noqa: E501
        """T-2025: `TEST_ABSENT_AT_PARENT` refuses (exit 1, same as
        `NO_VERDICT`) but with the squash-history explanation, not the
        generic 'e.g. it calls a function that does not exist there yet'
        wording -- an agent reading this message should not conclude the
        failure might be transient/retryable."""
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.TEST_ABSENT_AT_PARENT,
            ),
        ):
            cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_check_repro="tests/x.py::test_a",
            )
            with pytest.raises(SystemExit) as exc:
                _evidence(tmp_path, cfg)
        assert exc.value.code == 1
        assert "TEST_ABSENT_AT_PARENT" in caplog.text
        assert "squash" in caplog.text.lower()

    def test_no_node_id_resolves_designated_test(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCheckRepro.test_no_node_id_resolves_designated_test  # noqa: E501
        ticket_id = _test_make_bug_ticket(tmp_path, monkeypatch)
        with (
            patch(
                "frob.gitio._merge_base",
                return_value=Ok("deadbeef"),
            ),
            patch(
                "frob.gates._mutation_evidence._bug_repro_outcome_at_ref",
                return_value=_BugReproOutcome.FAILED_AT_PARENT,
            ) as mocked,
        ):
            cfg = AppConfig(
                ticket_command="evidence",
                ticket_id=ticket_id,
                ticket_path=tmp_path,
                ticket_check_repro="",
            )
            _evidence(tmp_path, cfg)
        mocked.assert_called_once_with(tmp_path, "tests/x.py::test_a", "deadbeef")


# frob:ticket T-1929
class TestEvidenceCliFlagsSurviveFromExternal:
    """T-0749's own precedent (`tests/test_tickets_acceptance.py::
    test_from_external_carries_accepts_from_parsed_argv`): a CLI flag's
    argparse `dest` must survive `AppConfig.from_external`'s allowlist
    (T-1422's shape) or it is silently dropped before `AppConfig(**d)`
    ever sees it -- WIRE001 caught exactly this for `ticket_check_repro`/
    `ticket_designate_repro_force` during T-1929's own implementation;
    these tests pin that it stays fixed."""

    def test_check_repro_and_base_ref_survive_from_external(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal.test_check_repro_and_base_ref_survive_from_external  # noqa: E501
        from frob.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "evidence",
                "T-0001",
                "--check-repro",
                "tests/x.py::test_a",
                "--base-ref",
                "deadbeef",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_check_repro == "tests/x.py::test_a"
        assert cfg.ticket_base_ref == "deadbeef"

    def test_check_repro_with_no_node_id_survives_as_empty_string(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal.test_check_repro_with_no_node_id_survives_as_empty_string  # noqa: E501
        from frob.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            ["ticket", "evidence", "T-0001", "--check-repro", "--path", str(tmp_path)]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_check_repro == ""

    def test_designate_repro_force_survives_from_external(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_runner_designate_repro.py::TestEvidenceCliFlagsSurviveFromExternal.test_designate_repro_force_survives_from_external  # noqa: E501
        from frob.__main__ import _build_parser

        parser = _build_parser()
        args = parser.parse_args(
            [
                "ticket",
                "evidence",
                "T-0001",
                "--designate-repro",
                "tests/x.py::test_a",
                "--designate-repro-force",
                "--path",
                str(tmp_path),
            ]
        )
        cfg = AppConfig.from_external(args, tmp_path / "pyproject.toml")
        assert cfg.ticket_designate_repro_force is True
