"""T-3308: `frob ticket new --json` printed the plain human `created
T-####: <title>` line regardless of `--json` -- a scripted caller had to
regex the id out of prose despite explicitly asking for JSON, unlike
`frob ticket show --json` (`ticket.model_dump_json`), which already
honors the flag. `_new` now emits a parseable JSON object on stdout
(id/title/kind/warnings) when `--json` is passed, and leaves the
human-readable path byte-for-byte unchanged otherwise."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from frob.app.config import AppConfig
from frob.app.ticket_runner._new import _new


def _cfg(tmp_path: Path, *, json_flag: bool) -> AppConfig:
    """A minimal `frob ticket new`-shaped `AppConfig` -- test helper only,
    mirroring `test_new_ticket_scope_overlap_warning.py`'s own precedent
    for calling `_new` directly against a bare `tmp_path`, no git repo
    required."""
    return AppConfig(
        ticket_command="new",
        ticket_title="json output subject",
        ticket_body="## Description\nx\n",
        ticket_kind="bug",
        ticket_path=tmp_path,
        ticket_scope=["src/x.py"],
        ticket_ack_related=True,
        ticket_json=json_flag,
    )


# frob:ticket T-3308
class TestNewJsonOutput:
    """`frob ticket new --json` (T-3308): a parseable JSON object naming
    the created ticket's id, printed on stdout via the same `_log.info`
    channel `frob ticket show --json` already uses."""

    # frob:tests tests/unit/test_ticket_new_json.py::TestNewJsonOutput.test_json_flag_prints_parseable_json_with_id  # noqa: E501
    def test_json_flag_prints_parseable_json_with_id(
        self, tmp_path: Path, caplog
    ) -> None:
        """MUST-FIRE: `--json` must produce valid, parseable JSON on
        stdout containing the created ticket's id -- not the human
        `created T-####: <title>` prose line."""
        with caplog.at_level(logging.INFO):
            _new(tmp_path, _cfg(tmp_path, json_flag=True))

        info_records = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert info_records, "expected at least one INFO record"
        payload = json.loads(info_records[-1])
        assert payload["id"].startswith("T-")
        assert payload["title"] == "json output subject"
        assert payload["kind"] == "bug"
        assert isinstance(payload["warnings"], list)
        # the plain-text "created ..." line must NOT also have been
        # logged -- --json replaces it, never supplements it.
        assert not any(m.startswith("created ") for m in info_records)

    # frob:tests tests/unit/test_ticket_new_json.py::TestNewJsonOutput.test_without_json_flag_output_is_unchanged  # noqa: E501
    def test_without_json_flag_output_is_unchanged(
        self, tmp_path: Path, caplog
    ) -> None:
        """MUST-STAY-QUIET: without `--json`, output is unchanged -- the
        plain `created T-####: <title>` line, no JSON anywhere."""
        with caplog.at_level(logging.INFO):
            _new(tmp_path, _cfg(tmp_path, json_flag=False))

        info_records = [r.message for r in caplog.records if r.levelno == logging.INFO]
        assert any(
            m.startswith("created T-") and "json output subject" in m
            for m in info_records
        )
        for message in info_records:
            try:
                json.loads(message)
            except (json.JSONDecodeError, ValueError):
                continue
            raise AssertionError(
                f"unexpected JSON-parseable INFO record without --json: {message!r}"
            )
