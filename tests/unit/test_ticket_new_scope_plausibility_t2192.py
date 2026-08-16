"""T-2192: T-2177's scope-plausibility check missed every one of the real
mis-scopings it was built for, because plain word overlap passes ANY
same-subject-area file -- and a wrong file in the RIGHT area (not a
wildly unrelated one) is exactly the T-2157/T-2173/T-2189 failure shape.
Ordinary prose words ("land", "merge", "conflict") recur across every
file in a subject area by construction, so counting a bare-word overlap
as a match could never distinguish the wrong file from the right one.

Acceptance criterion 1 (must FAIL against current main, i.e. T-2177's own
bare-word implementation): a ticket whose title names a hyphenated
compound ("auto-rebase") gets scoped to a same-subject-area file that
shares only ORDINARY prose vocabulary (not the real "rebase"-shaped
identifier) with the ticket -- the bare-word implementation matches on
the shared prose and stays silent; the fixed, identifier-shaped-only
implementation correctly warns. Criterion 2: the SAME ticket, scoped to
the file that genuinely defines the `..._rebase_...` symbol, still files
without friction."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._new import _new


def _write(path: Path, text: str) -> None:
    """Create `path`'s parent dirs and write `text` -- test helper only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# frob:ticket T-2192
class TestScopePlausibilityIdentifierShaped:
    """Acceptance criteria 1-2: identifier-shaped-only ticket-side
    matching catches a wrong-file-in-the-right-area mis-scoping that
    plain word overlap misses (T-2192)."""

    # frob:ticket T-2192
    def test_same_area_wrong_file_now_warns(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped.test_same_area_wrong_file_now_warns  # noqa: E501
        # A same-subject-area file: shares ordinary prose ("conflict",
        # "worktree", "merge") with the ticket, but defines nothing
        # "rebase"-shaped -- the T-2157/T-2173/T-2189 shape exactly.
        _write(
            tmp_path / "src/frob/tickets/_land_git_ops.py",
            "def merge_worktree_into_main(root):\n"
            "    '''Merge the worktree branch into main.'''\n"
            "    log.info('land: auto-resolve of out-of-scope conflict')\n"
            "    return run_merge(root)\n",
        )
        cfg = AppConfig(
            ticket_command="new",
            ticket_title=(
                "auto-rebase conflicts on ledger files leaves worktrees stale"
            ),
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_scope=["src/frob/tickets/_land_git_ops.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, cfg)
        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "scope plausibility" in messages.lower(), (
            "expected a scope-plausibility warning -- the scope file shares "
            "only ordinary prose with the ticket, not the real "
            f"'rebase'-shaped identifier; got:\n{messages}"
        )

    # frob:ticket T-2192
    def test_same_area_right_file_still_files_without_friction(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_scope_plausibility_t2192.py::TestScopePlausibilityIdentifierShaped.test_same_area_right_file_still_files_without_friction  # noqa: E501
        _write(
            tmp_path / "src/frob/tickets/_land.py",
            "def auto_rebase_worktree_onto_main(root):\n"
            "    '''Rebase the worktree onto the current main tip.'''\n"
            "    return run_rebase(root)\n",
        )
        cfg = AppConfig(
            ticket_command="new",
            ticket_title=(
                "auto-rebase conflicts on ledger files leaves worktrees stale"
            ),
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_scope=["src/frob/tickets/_land.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, cfg)
        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "scope plausibility" not in messages.lower(), (
            f"scope genuinely defines the referenced symbol; got:\n{messages}"
        )
