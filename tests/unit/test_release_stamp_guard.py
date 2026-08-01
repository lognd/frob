"""T-1381: `frob release stamp` must refuse to absorb an un-bumped API change.

This reproduces a real coordinator mistake from 2026-08-01, in order:
REL001 said "public API changed (minor) since 0.293.0; bump the version to
>= 0.294.0, then run: frob release stamp". Running the stamp half at the
UNCHANGED version made REL001 go quiet -- stamping rebaselines the recorded
API at whatever version is current -- so the gate was satisfied and the
minor bump silently never happened.

The remedy text invites the mistake: it names bump-then-stamp as one
instruction, and stamp alone is the half that appears to work.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.graph._models import Digests, GraphSnapshot, SymbolId, SymbolRecord
from frob.lang import SymbolKind
from frob.release import ReleaseError, ReleaseManifest, manifest_path, stamp


@pytest.fixture
def _snapshot() -> GraphSnapshot:
    """A snapshot carrying one public symbol, so its API differs from every
    manifest below (which record a symbol that is not in it)."""
    ref = "src/mod.py::kept"
    return GraphSnapshot(
        root="/repo",
        symbols={
            ref: SymbolRecord(
                id=SymbolId(path="src/mod.py", qualname="kept"),
                kind=SymbolKind.FUNCTION,
                public=True,
                digests=Digests(sig="sig-kept", body="b", doc="d"),
                span=(1, 2),
            )
        },
        edges=(),
        malformed=(),
        file_hashes={},
    )


def _write_manifest(root: Path, version: str, api: dict[str, str]) -> None:
    manifest_path(root).write_text(
        ReleaseManifest(version=version, api=api).model_dump_json(indent=2),
        encoding="utf-8",
    )


class TestStampRefusesUnbumped:
    # frob:tests src/frob/release/__init__.py::stamp kind="unit"
    # frob:ticket T-1381
    def test_refuses_when_api_changed_and_version_not_bumped(
        self, tmp_path: Path, _snapshot
    ) -> None:
        """The exact footgun: an API change stamped at the OLD version."""
        _write_manifest(tmp_path, "0.1.0", {"gone::symbol": "deadbeef"})
        before = manifest_path(tmp_path).read_text(encoding="utf-8")

        result = stamp(tmp_path, _snapshot, "0.1.0")

        assert result.is_err
        assert result.danger_err is ReleaseError.UnbumpedApiChange
        assert manifest_path(tmp_path).read_text(encoding="utf-8") == before, (
            "a refused stamp must write NOTHING -- a partial write would "
            "rebaseline the API it just refused to accept"
        )

    # frob:tests src/frob/release/__init__.py::stamp kind="unit"
    # frob:ticket T-1381
    def test_allows_when_version_is_bumped(self, tmp_path: Path, _snapshot) -> None:
        """The correct order still works: bump first, then stamp."""
        _write_manifest(tmp_path, "0.1.0", {"gone::symbol": "deadbeef"})

        result = stamp(tmp_path, _snapshot, "99.0.0")

        assert result.is_ok, result.danger_err
        assert result.danger_ok == "99.0.0"

    # frob:tests src/frob/release/__init__.py::stamp kind="unit"
    # frob:ticket T-1381
    def test_allow_unbumped_is_an_explicit_override(
        self, tmp_path: Path, _snapshot
    ) -> None:
        """The escape hatch must actually escape -- a refusal with no way
        past it would just move the footgun somewhere worse."""
        _write_manifest(tmp_path, "0.1.0", {"gone::symbol": "deadbeef"})

        result = stamp(tmp_path, _snapshot, "0.1.0", allow_unbumped=True)

        assert result.is_ok, result.danger_err

    # frob:tests src/frob/release/__init__.py::stamp kind="unit"
    # frob:ticket T-1381
    def test_first_ever_stamp_is_not_blocked(self, tmp_path: Path, _snapshot) -> None:
        """With no manifest to compare against there is no bump to be short
        of, so bootstrapping a fresh repo must not be refused."""
        assert not manifest_path(tmp_path).exists()

        result = stamp(tmp_path, _snapshot, "0.1.0")

        assert result.is_ok, result.danger_err


class TestGuardIsOnByDefault:
    """The guard is only worth having if it is the DEFAULT. A flipped
    `release_allow_unbumped` default would silently disable it everywhere
    while every other test here still passed."""

    # frob:tests src/frob/app/config.py::AppConfig kind="unit"
    # frob:ticket T-1381
    def test_appconfig_default_does_not_allow_unbumped(self) -> None:
        from frob.app.config import AppConfig

        assert AppConfig().release_allow_unbumped is False

    # frob:tests src/frob/_cli_parsers/_misc.py kind="unit"
    # frob:ticket T-1381
    def test_cli_without_the_flag_does_not_allow_unbumped(self, tmp_path) -> None:
        """End of the chain: parsing `frob release stamp` with no flag must
        reach AppConfig as False."""
        import argparse

        from frob._cli_parsers._misc import _add_release_parser
        from frob.app.config import AppConfig

        parser = argparse.ArgumentParser(prog="frob")
        sub = parser.add_subparsers(dest="command")
        _add_release_parser(sub)
        args = parser.parse_args(["release", "stamp"])
        cfg = AppConfig.from_external(args, tmp_path / "frob.toml")
        assert cfg.release_allow_unbumped is False

    # frob:tests src/frob/_cli_parsers/_misc.py kind="unit"
    # frob:ticket T-1381
    def test_cli_with_the_flag_allows_unbumped(self, tmp_path) -> None:
        import argparse

        from frob._cli_parsers._misc import _add_release_parser
        from frob.app.config import AppConfig

        parser = argparse.ArgumentParser(prog="frob")
        sub = parser.add_subparsers(dest="command")
        _add_release_parser(sub)
        args = parser.parse_args(["release", "stamp", "--allow-unbumped"])
        cfg = AppConfig.from_external(args, tmp_path / "frob.toml")
        assert cfg.release_allow_unbumped is True
