"""Direct-call CLI coverage for T-0715's tier/sprint surface: `frob ticket
new --tier/--sprint`, `frob ticket doable --sprint/--by-parent`, and `frob
ticket sprint assign|show` -- same `AppConfig` + `ticket_runner.run`
direct-call shape as `test_app_runners_batch7.py` (T-0160 rationale: CLI-
subprocess tests don't attribute coverage back to the running process)."""

from __future__ import annotations

from pathlib import Path

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run


class TestTicketNewTierSprint:
    """`frob ticket new --tier ... --sprint ...` (T-0715)."""

    def test_new_carries_tier_and_sprint(self, tmp_path: Path, caplog) -> None:
        # frob:tests tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketNewTierSprint::test_new_carries_tier_and_sprint  # noqa: E501
        cfg = AppConfig(
            ticket_command="new",
            ticket_path=tmp_path,
            ticket_title="a story",
            ticket_kind="feature",
            ticket_tier="story",
            ticket_sprint="sprint-14",
        )
        ticket_run(cfg)

        from frob.tickets import load_all

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        ticket = loaded.danger_ok["T-0001"]
        assert ticket.tier.value == "story"
        assert ticket.sprint == "sprint-14"


class TestTicketDoableSprintByParent:
    """`frob ticket doable --sprint LABEL` / `--by-parent` (T-0715)."""

    def test_doable_sprint_filter(self, tmp_path: Path, caplog) -> None:
        # frob:tests tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_sprint_filter  # noqa: E501
        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=tmp_path,
                ticket_title="in sprint",
                ticket_kind="feature",
                ticket_sprint="sprint-1",
            )
        )
        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=tmp_path,
                ticket_title="not in sprint",
                ticket_kind="feature",
            )
        )
        caplog.clear()
        cfg = AppConfig(
            ticket_command="doable",
            ticket_path=tmp_path,
            ticket_doable_sprint="sprint-1",
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "T-0001  in sprint" in caplog.text
        assert "T-0002" not in caplog.text

    def test_doable_by_parent_groups_leaves(self, tmp_path: Path, caplog) -> None:
        # frob:tests tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketDoableSprintByParent::test_doable_by_parent_groups_leaves  # noqa: E501
        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=tmp_path,
                ticket_title="a story",
                ticket_kind="feature",
                ticket_tier="story",
            )
        )
        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=tmp_path,
                ticket_title="a leaf",
                ticket_kind="feature",
                ticket_parent="T-0001",
            )
        )
        cfg = AppConfig(
            ticket_command="doable",
            ticket_path=tmp_path,
            ticket_doable_by_parent=True,
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "a story" in caplog.text
        assert "a leaf" in caplog.text


class TestTicketSprintAssignShow:
    """`frob ticket sprint assign <id> <label>` / `sprint show <label>`
    (T-0715)."""

    def test_assign_then_show(self, tmp_path: Path, caplog) -> None:
        # frob:tests tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketSprintAssignShow::test_assign_then_show  # noqa: E501
        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=tmp_path,
                ticket_title="a ticket",
                ticket_kind="feature",
            )
        )
        ticket_run(
            AppConfig(
                ticket_command="sprint",
                ticket_path=tmp_path,
                ticket_sprint_command="assign",
                ticket_id="T-0001",
                ticket_sprint="sprint-9",
            )
        )
        cfg = AppConfig(
            ticket_command="sprint",
            ticket_path=tmp_path,
            ticket_sprint_command="show",
            ticket_sprint="sprint-9",
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert "1 ticket(s), 0 closed" in caplog.text
        assert "a ticket" in caplog.text

    def test_show_json_mode(self, tmp_path: Path, caplog) -> None:
        # frob:tests tests/unit/test_app_runners_t0715_sprint_tier.py::TestTicketSprintAssignShow::test_show_json_mode  # noqa: E501
        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=tmp_path,
                ticket_title="a ticket",
                ticket_kind="feature",
                ticket_sprint="sprint-9",
            )
        )
        cfg = AppConfig(
            ticket_command="sprint",
            ticket_path=tmp_path,
            ticket_sprint_command="show",
            ticket_sprint="sprint-9",
            ticket_json=True,
        )
        with caplog.at_level("INFO"):
            ticket_run(cfg)
        assert '"sprint": "sprint-9"' in caplog.text
        assert '"closed": 0' in caplog.text
