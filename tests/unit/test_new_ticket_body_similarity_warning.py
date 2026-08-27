"""T-3124: `frob ticket new` warns on scope overlap (T-2257) and refuses on
an exact/near-exact TITLE match (T-1995), but had no signal at all for two
tickets with DIFFERENT titles whose BODIES are near-duplicates -- the
dimension `_body_similarity_warnings` adds. WARN only, never a refusal
(unlike T-1995's title gate): a similar body is a weaker signal than an
identical title, since tickets commonly share boilerplate sections."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._new import _new


# frob:ticket T-3124
def _cfg(tmp_path: Path, *, title: str, body: str) -> AppConfig:
    """A minimal `frob ticket new`-shaped `AppConfig` -- test helper only,
    mirroring `test_new_ticket_scope_overlap_warning.py::_file_cfg`'s own
    precedent for calling `_new` directly against a bare `tmp_path`, no
    git repo required. `--ack-related` is passed unconditionally so
    T-1995's OWN title-similarity refusal never masks what these tests
    exercise (deliberately DIFFERENT titles throughout, so it would not
    fire regardless, but T-1995's own fixtures follow this same
    precaution)."""
    return AppConfig(
        ticket_command="new",
        ticket_title=title,
        ticket_body=body,
        ticket_kind="bug",
        ticket_path=tmp_path,
        ticket_scope=[],
        ticket_ack_related=True,
    )


# frob:ticket T-3124
_LONG_BODY = (
    "MEASURED 2026-08-27. The evidence-reach classifier (T-3046) computes "
    "a per-symbol reach score but frob check never surfaces it as a real "
    "gate finding -- it is wired into the graph but nothing ever reads the "
    "score back out at check time, so a symbol with zero reachable tests "
    "sails through green. This ticket wires the classifier's output into "
    "frob check as a genuine WARN-severity gate finding (never an error, "
    "never a refusal) so an agent sees the gap without the land itself "
    "being blocked on it. Scope is the classifier's own consumer site "
    "plus the gate registration; the classifier's scoring logic itself is "
    "out of scope and already covered by T-3046's own tests."
)


# frob:ticket T-3124
class TestBodySimilarityWarnings:
    """Acceptance (T-3124): a near-duplicate body warns naming the other
    ticket; a genuinely distinct body prints nothing; filing is never
    refused on this dimension."""

    # frob:ticket T-3124
    def test_near_identical_body_different_title_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_body_similarity_warning.py::TestBodySimilarityWarnings.test_near_identical_body_different_title_warns  # noqa: E501
        """(MUST FAIL FIRST on main): the T-3063/T-3070 shape -- two
        DIFFERENT titles (title alone would file cleanly), byte-for-byte
        identical body, must warn naming the first ticket."""
        first_cfg = _cfg(
            tmp_path,
            title="Wire evidence-reach classifier (T-3046) into frob check",
            body=_LONG_BODY,
        )
        _new(tmp_path, first_cfg)
        first_id = next(p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir())

        caplog.clear()
        second_cfg = _cfg(
            tmp_path,
            title="Surface the T-3046 reach score as a real check gate",
            body=_LONG_BODY,
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, second_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert first_id in messages, (
            f"expected the body-similarity warning to name {first_id}; got:\n{messages}"
        )
        assert "similar" in messages.lower()

    # frob:ticket T-3124
    def test_genuinely_distinct_body_prints_nothing(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_body_similarity_warning.py::TestBodySimilarityWarnings.test_genuinely_distinct_body_prints_nothing  # noqa: E501
        """Must-stay-quiet: a second ticket with an unrelated body must
        print no similarity warning at all."""
        first_cfg = _cfg(
            tmp_path,
            title="Wire evidence-reach classifier (T-3046) into frob check",
            body=_LONG_BODY,
        )
        _new(tmp_path, first_cfg)

        caplog.clear()
        second_cfg = _cfg(
            tmp_path,
            title="Fix the fleet_status.py orphan false-positive",
            body=(
                "fleet_status.py reports an orphaned worktree for one that "
                "is still actively held by a live session -- the liveness "
                "check races the lease file write. Fix the ordering so the "
                "liveness probe always runs after the lease is durable."
            ),
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, second_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "similar to" not in messages

    # frob:ticket T-3124
    def test_never_refuses_on_body_similarity_alone(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_new_ticket_body_similarity_warning.py::TestBodySimilarityWarnings.test_never_refuses_on_body_similarity_alone  # noqa: E501
        """Acceptance: filing is never REFUSED on body-similarity grounds
        -- warn only. A near-duplicate body under a distinct title must
        still create the ticket (no SystemExit)."""
        first_cfg = _cfg(
            tmp_path,
            title="Wire evidence-reach classifier (T-3046) into frob check",
            body=_LONG_BODY,
        )
        _new(tmp_path, first_cfg)

        second_cfg = _cfg(
            tmp_path,
            title="Surface the T-3046 reach score as a real check gate",
            body=_LONG_BODY,
        )
        _new(tmp_path, second_cfg)  # must not raise SystemExit

        ticket_dirs = [p for p in (tmp_path / "tickets").iterdir() if p.is_dir()]
        assert len(ticket_dirs) == 2

    # frob:ticket T-3124
    # frob:waive DUP002 reason="shares the \
    # create-first-ticket/create-second-with-same-body setup with \
    # test_near_identical_body_different_title_warns above (95% similar) -- both are \
    # genuinely distinct acceptance checks (a fresh-ledger warning vs. the \
    # terminal-state exclusion), and the shared setup is the SAME established \
    # fixture-repetition idiom this module's own DUP001 waivers on _run/_git_init/ \
    # _commit_all already document; extracting a shared helper is a real, independent \
    # cleanup outside T-3124's own scope"
    def test_terminal_ticket_body_is_not_compared(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_new_ticket_body_similarity_warning.py::TestBodySimilarityWarnings.test_terminal_ticket_body_is_not_compared  # noqa: E501
        """A DONE ticket's old body is history, not a live duplicate risk
        -- matches `_scope_overlap_warnings`'s own terminal-state
        exclusion precedent."""
        first_cfg = _cfg(
            tmp_path,
            title="Wire evidence-reach classifier (T-3046) into frob check",
            body=_LONG_BODY,
        )
        _new(tmp_path, first_cfg)
        first_id = next(p.name for p in (tmp_path / "tickets").iterdir() if p.is_dir())

        from frob.tickets._models import TicketState
        from frob.tickets._store import load_all, write_ticket

        loaded = load_all(tmp_path)
        assert loaded.is_ok
        ticket = loaded.danger_ok[first_id]
        done_ticket = ticket.model_copy(update={"state": TicketState.DONE})
        write_ticket(tmp_path, done_ticket)

        caplog.clear()
        second_cfg = _cfg(
            tmp_path,
            title="Surface the T-3046 reach score as a real check gate",
            body=_LONG_BODY,
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, second_cfg)

        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "similar to" not in messages
