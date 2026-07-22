"""Unit tests for frob.fleet.route_ticket (docs/modules/fleet.md#routing)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.fleet import FleetError, FleetManifest, RepoEntry, route_ticket
from frob.tickets import Origin, Priority, TicketKind, TicketSpec


def _init_git_repo(path: Path, *, frob_enabled: bool = True) -> None:
    """A minimal git repo, with an empty `tickets.md` ledger unless
    `frob_enabled=False` (for the not-frob-enabled test)."""
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    # frob:secret-fake -- fixture-only git identity, not a real address
    subprocess.run(["git", "config", "user.email", "a@b.c"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "a"], cwd=path, check=True)
    (path / "README.md").write_text("hello\n")
    if frob_enabled:
        (path / "tickets.md").write_text("# Tickets\n")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=path, check=True)


class TestRouteTicket:
    def test_route_ticket_ok(self, tmp_path: Path) -> None:
        repo_dir = tmp_path / "target-repo"
        _init_git_repo(repo_dir)
        manifest = FleetManifest(repos=(RepoEntry(name="target", path=repo_dir),))
        spec = TicketSpec(
            title="found while probing the fleet",
            kind=TicketKind.BUG,
            origin=Origin.AGENT,
            priority=Priority.MEDIUM,
        )
        result = route_ticket(manifest, "target", spec)
        assert result.is_ok
        assert result.danger_ok.startswith("T-")
        assert (repo_dir / "tickets.md").exists()

    def test_route_ticket_unknown_repo(self, tmp_path: Path) -> None:
        manifest = FleetManifest(repos=())
        spec = TicketSpec(
            title="x", kind=TicketKind.BUG, origin=Origin.AGENT, priority=Priority.LOW
        )
        result = route_ticket(manifest, "nope", spec)
        assert result.is_err
        assert result.danger_err is FleetError.RepoNotFound

    def test_route_ticket_missing_path(self, tmp_path: Path) -> None:
        manifest = FleetManifest(
            repos=(RepoEntry(name="ghost", path=tmp_path / "does-not-exist"),)
        )
        spec = TicketSpec(
            title="x", kind=TicketKind.BUG, origin=Origin.AGENT, priority=Priority.LOW
        )
        result = route_ticket(manifest, "ghost", spec)
        assert result.is_err
        assert result.danger_err is FleetError.RepoPathMissing

    def test_route_ticket_not_frob_enabled(self, tmp_path: Path) -> None:
        """MINOR fix (T-0573 review finding): a directory with no
        tickets.md and no legacy tickets/ dir is not a frob-enabled repo
        -- route_ticket must refuse rather than silently bootstrapping a
        brand-new ledger there via new_ticket's create-on-first-write."""
        repo_dir = tmp_path / "not-frob-enabled"
        repo_dir.mkdir()
        (repo_dir / "README.md").write_text("just a plain directory\n")
        manifest = FleetManifest(repos=(RepoEntry(name="plain", path=repo_dir),))
        spec = TicketSpec(
            title="x", kind=TicketKind.BUG, origin=Origin.AGENT, priority=Priority.LOW
        )
        result = route_ticket(manifest, "plain", spec)
        assert result.is_err
        assert result.danger_err is FleetError.RouteFailed
        assert not (repo_dir / "tickets.md").exists()
