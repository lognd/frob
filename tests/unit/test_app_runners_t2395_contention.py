"""Direct-call CLI coverage for T-2395's `frob ticket contention`: plain
and `--json` render shape, plus the `frob ticket doable` HOT FILE marker
surfacing (automatic-over-commands: a coordinator who never runs
`contention` still sees the collision risk on a returned ticket). Same
`AppConfig` + `ticket_runner.run` direct-call shape as
`test_app_runners_t1738_wave.py` (T-0160 rationale: CLI-subprocess tests
don't attribute coverage back to the running process)."""

from __future__ import annotations

import io
import json
import logging
from pathlib import Path

from frob.app.config import AppConfig
from frob.app.ticket_runner import run as ticket_run

_TITLE_COUNTER = {"n": 0}


def _new(tmp_path: Path, *, scope: list[str] | None = None) -> str:
    """File one queued ticket via the real `ticket new` verb, matching
    `test_app_runners_t1738_wave.py`'s own `_new` helper. Each call gets
    a distinct title (a real `related_tickets` duplicate-title refusal
    otherwise fires on the second call in the same `tmp_path`). Returns
    the logged ticket id (parsed from the info-level log line)."""
    _TITLE_COUNTER["n"] += 1
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("frob.app.ticket_runner")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        ticket_run(
            AppConfig(
                ticket_command="new",
                ticket_path=tmp_path,
                ticket_title=f"a distinct ticket {_TITLE_COUNTER['n']}",
                ticket_kind="feature",
                ticket_scope=scope or [],
                ticket_ack_related=True,
            )
        )
    finally:
        logger.removeHandler(handler)
    out = stream.getvalue()
    # "ticket new: filed T-XXXX ..." is the real log shape this repo's
    # ticket-new command emits; grab the first "T-" token.
    for token in out.split():
        if token.startswith("T-") and token[2:].split(":")[0].isdigit():
            return token.rstrip(":.,")
    raise AssertionError(f"could not parse a ticket id out of: {out!r}")


def _run_captured(cfg: AppConfig) -> str:
    """Run `ticket_run(cfg)` capturing `frob.app.ticket_runner`'s INFO
    log stream, returning it as one string -- the render assertions all
    just substring-match this."""
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    logger = logging.getLogger("frob.app.ticket_runner")
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    try:
        ticket_run(cfg)
    finally:
        logger.removeHandler(handler)
    return stream.getvalue()


class TestContentionCommand:
    """`frob ticket contention [--json]` (T-2395)."""

    def test_plain_render_ranks_and_names_owners(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand.test_plain_render_ranks_and_names_owners  # noqa: E501
        (tmp_path / "src.py").write_text("x\n", encoding="utf-8")
        (tmp_path / "other.py").write_text("y\n", encoding="utf-8")
        _new(tmp_path, scope=["src.py"])
        _new(tmp_path, scope=["src.py"])
        _new(tmp_path, scope=["src.py"])
        _new(tmp_path, scope=["other.py"])

        out = _run_captured(
            AppConfig(ticket_command="contention", ticket_path=tmp_path)
        )
        assert "src.py" in out
        assert "3 ticket(s)" in out
        assert "other.py" not in out.split("Suggested")[0].split("src.py")[0]

    def test_zero_contention_is_explicit_not_silent(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand.test_zero_contention_is_explicit_not_silent  # noqa: E501
        (tmp_path / "a.py").write_text("x\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("y\n", encoding="utf-8")
        _new(tmp_path, scope=["a.py"])
        _new(tmp_path, scope=["b.py"])

        out = _run_captured(
            AppConfig(ticket_command="contention", ticket_path=tmp_path)
        )
        assert "zero contention" in out

    def test_json_render_shape(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand.test_json_render_shape  # noqa: E501
        (tmp_path / "src.py").write_text("x\n", encoding="utf-8")
        t1 = _new(tmp_path, scope=["src.py"])
        t2 = _new(tmp_path, scope=["src.py"])

        out = _run_captured(
            AppConfig(
                ticket_command="contention", ticket_path=tmp_path, ticket_json=True
            )
        )
        payload = json.loads(out)
        assert "entries" in payload
        assert "batches" in payload
        assert len(payload["entries"]) == 1
        entry = payload["entries"][0]
        assert entry["file"] == "src.py"
        assert entry["count"] == 2
        assert set(entry["ticket_ids"]) == {t1, t2}
        assert payload["batches"] == [sorted([t1, t2])]

    def test_suggested_batching_is_transitive_across_files(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_app_runners_t2395_contention.py::TestContentionCommand.test_suggested_batching_is_transitive_across_files  # noqa: E501
        (tmp_path / "a.py").write_text("x\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("y\n", encoding="utf-8")
        t1 = _new(tmp_path, scope=["a.py"])
        t2 = _new(tmp_path, scope=["a.py", "b.py"])
        t3 = _new(tmp_path, scope=["b.py"])

        out = _run_captured(
            AppConfig(
                ticket_command="contention", ticket_path=tmp_path, ticket_json=True
            )
        )
        payload = json.loads(out)
        assert len(payload["batches"]) == 1
        assert set(payload["batches"][0]) == {t1, t2, t3}


class TestDoableHotFileMarker:
    """T-2395's `frob ticket doable` HOT FILE marker (automatic-over-
    commands: surfaced without needing to run `contention` separately)."""

    def test_doable_row_carries_hot_file_marker(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_app_runners_t2395_contention.py::TestDoableHotFileMarker.test_doable_row_carries_hot_file_marker  # noqa: E501
        (tmp_path / "src.py").write_text("x\n", encoding="utf-8")
        _new(tmp_path, scope=["src.py"])
        _new(tmp_path, scope=["src.py"])

        out = _run_captured(AppConfig(ticket_command="doable", ticket_path=tmp_path))
        assert "HOT FILE: src.py (2x open tickets)" in out

    def test_doable_row_has_no_marker_without_contention(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_app_runners_t2395_contention.py::TestDoableHotFileMarker.test_doable_row_has_no_marker_without_contention  # noqa: E501
        (tmp_path / "a.py").write_text("x\n", encoding="utf-8")
        (tmp_path / "b.py").write_text("y\n", encoding="utf-8")
        _new(tmp_path, scope=["a.py"])
        _new(tmp_path, scope=["b.py"])

        out = _run_captured(AppConfig(ticket_command="doable", ticket_path=tmp_path))
        assert "HOT FILE" not in out
