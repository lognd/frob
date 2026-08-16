"""T-2177: `frob ticket new` accepts a scope whose files contain no trace
of the ticket's own subject -- three measured occurrences (T-2157, T-2173,
T-2189), all filed against a plausible-looking file picked from the module
NAME instead of the actual symbol or error string, all caught only after
an implementing agent took a lease and built natives (a full dispatch
cycle wasted per occurrence).

Acceptance criterion 1 (must FAIL against current main): filing a ticket
whose title/body names a symbol/word absent from every declared scope
file's grammar-parsed identifier and string-literal tokens must warn
loudly -- `_new` on main performs no such check at all, so no
"scope plausibility" warning is ever logged, however implausible the
scope. Criterion 2: a genuinely plausible scope (the referenced word
really does appear as a real identifier/string token in a scope file)
proceeds without the warning -- the check must never fire on ordinary,
correctly-scoped work."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from frob.app.config import AppConfig
from frob.app.ticket_runner._new import _new


# frob:ticket T-2177
def _write(path: Path, text: str) -> None:
    """Create `path`'s parent dirs and write `text` -- test helper only."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


# frob:ticket T-2177
class TestScopePlausibility:
    """Acceptance criteria 1-3: token/grammar-based scope-plausibility
    warning at `frob ticket new` filing time (T-2177)."""

    # frob:ticket T-2177
    def test_implausible_scope_warns_loudly(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility.test_implausible_scope_warns_loudly  # noqa: E501
        # Reproduces the T-2157/T-2173 shape exactly: a scope file that
        # contains zero code related to the ticket's own subject.
        _write(
            tmp_path / "src/frob/tickets/_land_git_ops.py",
            "def merge_worktree_into_main(root):\n"
            "    '''Merge the worktree branch into main.'''\n"
            "    return run_merge(root)\n",
        )
        cfg = AppConfig(
            ticket_command="new",
            ticket_title=(
                "frob ticket land's internal rebase step silently drops "
                "unrelated commits"
            ),
            ticket_body=(
                "The rebase_worktree_onto_main helper mis-handles a diverged history."
            ),
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_scope=["src/frob/tickets/_land_git_ops.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, cfg)
        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "scope plausibility" in messages.lower(), (
            "expected a scope-plausibility warning naming the implausible "
            f"scope; got:\n{messages}"
        )

    # frob:ticket T-2177
    def test_plausible_scope_files_without_friction(
        self, tmp_path: Path, caplog: pytest.LogCaptureFixture
    ) -> None:
        # frob:tests tests/unit/test_ticket_new_scope_plausibility.py::TestScopePlausibility.test_plausible_scope_files_without_friction  # noqa: E501
        _write(
            tmp_path / "src/frob/tickets/_land.py",
            "def rebase_worktree_onto_main(root):\n"
            "    '''Rebase the worktree onto the current main tip.'''\n"
            "    return run_rebase(root)\n",
        )
        cfg = AppConfig(
            ticket_command="new",
            ticket_title=(
                "frob ticket land's internal rebase step silently drops "
                "unrelated commits"
            ),
            ticket_body=(
                "The rebase_worktree_onto_main helper mis-handles a diverged history."
            ),
            ticket_kind="bug",
            ticket_path=tmp_path,
            ticket_scope=["src/frob/tickets/_land.py"],
        )
        with caplog.at_level(logging.WARNING):
            _new(tmp_path, cfg)
        messages = "\n".join(r.getMessage() for r in caplog.records)
        assert "scope plausibility" not in messages.lower(), (
            f"scope genuinely contains the referenced symbol; got:\n{messages}"
        )
