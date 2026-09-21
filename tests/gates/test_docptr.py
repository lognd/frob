"""T-5126: DOC006 must skip CLI-pointer resolution for a
ticket's own narrative body (`tickets/<id>/ticket.md`), regardless of
ticket state, while a real unresolved CLI pointer elsewhere still fires.

A separate module from `tests/test_docptr_gate.py` on purpose: that file
is under another in-progress ticket's live cross-worktree file lease
(T-4624), so this ticket cannot add to it without a scope conflict. The
fixture helpers below are a minimal, deliberate duplication of that
file's `_init_repo`/`_write`/`_add_all`/`_snapshot`/`_by_rule` shape --
not a refactor target, since neither file may edit the other while the
lease stands.
"""

# frob:ticket T-5126

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._docptr import doc006_gate
from frob.graph import build_graph

_CLI_CONFIG = (
    '[[docblocks.commands]]\nprog = "frob"\nparser = "frob.__main__:_build_parser"\n'
)


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-C", str(root), *args], check=True, capture_output=True, text=True
    )


def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "-q")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "checkout", "-q", "-b", "main")


def _write(root: Path, rel: str, text: str) -> Path:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


def _add_all(root: Path) -> None:
    _git(root, "add", "-A")


def _snapshot(root: Path):
    return build_graph(root, root / ".frob" / "cache.db").danger_ok


def _by_rule(violations, file: str | None = None):
    return [
        v for v in violations if v.rule == "DOC006" and (file is None or v.file == file)
    ]


def _write_open_ticket(tmp_path: Path, ticket_id: str, body: str) -> None:
    """Write a minimally-valid QUEUED (non-terminal) `ticket.md` -- the
    live-work state a CLI-pointer skip must apply to just as much as a
    terminal one, since a planner backtick-quoting a not-yet-built CLI
    form is true of an open ticket's plan section too."""
    frontmatter = (
        "---\n"
        f"id: {ticket_id}\n"
        "title: placeholder\n"
        "state: queued\n"
        "kind: bug\n"
        "origin: human\n"
        "created: '2026-09-19'\n"
        "---\n"
    )
    _write(tmp_path, f"tickets/{ticket_id}/{body}", frontmatter)


class TestDoc006TicketBodyCliPointerSkip:
    """T-5126 positive controls (a) and (c) from the ticket's
    plan: a ticket body's backticked planned/rejected CLI form produces
    no DOC006 finding, while a real unresolved CLI pointer in an ordinary
    doc still fires."""

    def test_open_ticket_planned_cli_pointer_not_flagged(
        self, tmp_path: Path
    ) -> None:
        """(a) A fixture ticket body with a backticked NONEXISTENT command
        (`frob sys split`, a planned/rejected surface) produces no DOC006
        finding -- the exact repro shape (T-4659/T-4416/T-4684 land
        refusals) this ticket fixes."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write_open_ticket(
            tmp_path,
            "T-7001",
            "ticket.md",
        )
        ticket_path = tmp_path / "tickets/T-7001/ticket.md"
        ticket_path.write_text(
            ticket_path.read_text()
            + "\nPlan: eventually add `frob sys split` as a new subcommand.\n"
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        assert not _by_rule(violations, "tickets/T-7001/ticket.md")

    def test_real_doc_cli_pointer_still_flagged(self, tmp_path: Path) -> None:
        """(c) A real `docs/*.md` unresolved CLI pointer -- NOT a ticket
        body -- still fires; the ticket-body skip must not leak into the
        rest of DOC006's CLI-pointer resolution."""
        _init_repo(tmp_path)
        _write(tmp_path, "frob.toml", _CLI_CONFIG)
        _write(
            tmp_path,
            "docs/guide.md",
            "Run `frob nonexistent-subcommand` first.\n",
        )
        _add_all(tmp_path)
        violations = doc006_gate(tmp_path, _snapshot(tmp_path))
        found = _by_rule(violations, "docs/guide.md")
        assert found
        assert any("nonexistent-subcommand" in v.message for v in found)
