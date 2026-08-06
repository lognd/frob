"""End-to-end CLI test for `frob ticket promote <draft-id>` (T-1637) --
exercises the real subprocess entrypoint (`frob.app.ticket_runner._promote`),
not just the library-level `finalize_draft` it wraps."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.system.conftest import run


# frob:ticket T-1637
def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


# frob:ticket T-1637
def _init_repo(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", "-b", "main", cwd=root)
    _git("config", "user.email", "test@example.com", cwd=root)
    _git("config", "user.name", "Test", cwd=root)
    (root / "tickets.md").write_text("# Tickets\n\n")
    _git("add", "-A", cwd=root)
    _git("commit", "-q", "-m", "init", cwd=root)


# frob:ticket T-1637
class TestPromoteCLI:
    """`frob ticket promote <draft-id>` -- allocates the draft's real id
    and rewrites the ledger block plus every code reference, atomically,
    in one CLI call."""

    # frob:ticket T-1637
    def test_promotes_a_draft_carrying_evidence_and_done_report(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/app/ticket_runner/_query.py::_promote kind="unit"
        # frob:waive COV006 reason="confirmed exercised: this is a system test that \
        # spawns the real frob CLI as a subprocess (run of ticket promote) -- the \
        # process boundary is structurally invisible to the in-process best-effort \
        # callgraph, same class as this repo's other subprocess-dispatch COV006 \
        # waivers (see tests/system/test_cli_ticket_land.py)"
        repo = tmp_path / "main"
        _init_repo(repo)

        wt = tmp_path / "wt"
        _git("worktree", "add", "-b", "feature-promote", str(wt), cwd=repo)

        created = run(
            "ticket",
            "new",
            "--title",
            "Filed off-branch",
            "--kind",
            "bug",
            "--path",
            str(wt),
        )
        assert created.returncode == 0, created.stdout + created.stderr
        out = created.stdout + created.stderr
        start = out.index("T-draft-")
        draft_id = out[start : start + len("T-draft-XXXXXXXX")]

        # Give it evidence and a Done report -- the exact content T-1636's
        # hand-rolled recipe discarded.
        planned = run("ticket", "plan", draft_id, "--path", str(wt))
        assert planned.returncode == 0, planned.stdout + planned.stderr
        started = run("ticket", "start", draft_id, "--path", str(wt))
        assert started.returncode == 0, started.stdout + started.stderr

        from frob.tickets._store import load_all, write_ticket

        loaded = load_all(wt)
        assert loaded.is_ok
        ticket = loaded.danger_ok[draft_id]
        ticket = ticket.model_copy(
            update={
                "evidence": ("tests/test_x.py::test_ok",),
                "body": ticket.body + "\n## Done report\n\nshipped\n",
            }
        )
        assert write_ticket(wt, ticket).is_ok

        # Promote it -- this reaches all the way to MAIN's ledger, since
        # `promote` (like `renumber`) reads/writes wherever `--path` points,
        # not just the worktree's own view.
        promoted = run("ticket", "promote", draft_id, "--path", str(wt))
        assert promoted.returncode == 0, promoted.stdout + promoted.stderr
        assert "promoted" in (promoted.stdout + promoted.stderr)

        loaded_after = load_all(wt)
        assert loaded_after.is_ok
        assert draft_id not in loaded_after.danger_ok
        finalized = [
            t
            for t in loaded_after.danger_ok.values()
            if t.title == "Filed off-branch"
        ]
        assert len(finalized) == 1
        final = finalized[0]
        assert not final.id.startswith("T-draft-")
        # Evidence and Done report both survived the promotion intact.
        assert final.evidence == ("tests/test_x.py::test_ok",)
        assert "## Done report" in final.body

    # frob:ticket T-1637
    def test_promoting_an_already_final_id_is_a_no_op(self, tmp_path: Path) -> None:
        # frob:tests src/frob/app/ticket_runner/_query.py::_promote kind="unit"
        # frob:waive COV006 reason="confirmed exercised: this is a system test that \
        # spawns the real frob CLI as a subprocess (run of ticket promote) -- the \
        # process boundary is structurally invisible to the in-process best-effort \
        # callgraph, same class as this repo's other subprocess-dispatch COV006 \
        # waivers (see tests/system/test_cli_ticket_land.py)"
        repo = tmp_path / "main"
        _init_repo(repo)

        created = run(
            "ticket", "new", "--title", "Already real", "--kind", "bug", "--path", str(repo)
        )
        assert created.returncode == 0, created.stdout + created.stderr
        out = created.stdout + created.stderr
        start = out.index("created ") + len("created ")
        final_id = out[start : out.index(":", start)]
        assert final_id.startswith("T-0")

        promoted = run("ticket", "promote", final_id, "--path", str(repo))
        assert promoted.returncode == 0, promoted.stdout + promoted.stderr
        assert "already a final id" in (promoted.stdout + promoted.stderr)
