"""T-0338: unit tests for `frob.app.ticket_runner`'s land-time REL001
version-bump and native-rebuild-trigger helpers, exercised directly (no
real git worktree/subprocess needed for these pure/monkeypatched pieces --
the real end-to-end path is covered by tests/test_ticket_land.py's
`TestReleaseBump`/`TestRebuildNatives` against the library's injected
callables)."""

# frob:waive OPAQUE001 reason="T-1038: every setattr(...) in this file is \
# monkeypatch-style test isolation (pytest fixtures reassigning a module/object \
# attribute by a name the test itself constructs) -- deliberate test infrastructure, \
# not an evasion risk over untrusted input"

from __future__ import annotations

from pathlib import Path

import pytest
from typani.result import Err, Ok

from frob.app import ticket_runner
from frob.process import _guard
from frob.release import BumpClass, ReleaseError, ReleaseManifest
from frob.tickets._models import LandError


class _FakeTicket:
    title = "Do the thing"


def _write_repo_files(root: Path, *, version: str = "0.1.0") -> None:
    (root / "pyproject.toml").write_text(
        f'[project]\nname = "x"\nversion = "{version}"\n'
    )
    (root / "CHANGELOG.md").write_text("# Changelog\n\n## [0.1.0] - unreleased\n")


class TestWriteReleaseBump:
    def test_rewrites_version_and_prepends_changelog_entry(
        self, tmp_path: Path
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump.test_rewrites_version_and_prepends_changelog_entry  # noqa: E501
        _write_repo_files(tmp_path)

        result = ticket_runner._write_release_bump(
            tmp_path, _FakeTicket(), "T-0001", "0.2.0"
        )
        assert result.is_ok

        pyproject = (tmp_path / "pyproject.toml").read_text()
        assert 'version = "0.2.0"' in pyproject
        assert 'version = "0.1.0"' not in pyproject

        changelog = (tmp_path / "CHANGELOG.md").read_text()
        assert "## [0.2.0] - unreleased" in changelog
        assert "T-0001: Do the thing" in changelog
        # The old entry must survive underneath the new one, unmodified.
        assert "## [0.1.0] - unreleased" in changelog

    def test_missing_version_line_fails(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestWriteReleaseBump.test_missing_version_line_fails  # noqa: E501
        (tmp_path / "pyproject.toml").write_text('[project]\nname = "x"\n')
        (tmp_path / "CHANGELOG.md").write_text("# Changelog\n")

        result = ticket_runner._write_release_bump(
            tmp_path, _FakeTicket(), "T-0001", "0.2.0"
        )
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed


class TestApplyReleaseBumpForLand:
    """T-1007: the bump baseline now comes from `_root_release_manifest`
    (a `git show HEAD:.frob-release.json` read), never
    `frob.release.load_manifest`'s on-disk read -- these tests monkeypatch
    `ticket_runner._root_release_manifest` directly rather than
    `frob.release.load_manifest`, matching that new seam."""

    def test_no_manifest_is_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.test_no_manifest_is_noop  # noqa: E501
        _write_repo_files(tmp_path)
        monkeypatch.setattr(ticket_runner, "_root_release_manifest", lambda root: None)
        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_ok
        assert result.danger_ok is None

    def test_bump_class_none_is_noop(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.test_bump_class_none_is_noop  # noqa: E501
        _write_repo_files(tmp_path)
        manifest = ReleaseManifest(version="0.1.0", api={})
        monkeypatch.setattr(
            ticket_runner, "_root_release_manifest", lambda root: manifest
        )
        monkeypatch.setattr(
            "frob.release.diff_class", lambda manifest, snapshot: BumpClass.NONE
        )
        monkeypatch.setattr(ticket_runner, "_graph_snapshot", lambda root: Ok(object()))

        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_ok
        assert result.danger_ok is None

    def test_bump_applies_writes_and_stamps(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.test_bump_applies_writes_and_stamps  # noqa: E501
        _write_repo_files(tmp_path)
        manifest = ReleaseManifest(version="0.1.0", api={})
        stamp_calls: list[str] = []
        monkeypatch.setattr(
            ticket_runner, "_root_release_manifest", lambda root: manifest
        )
        monkeypatch.setattr(
            "frob.release.diff_class", lambda manifest, snapshot: BumpClass.MINOR
        )
        monkeypatch.setattr(
            "frob.release.required_version",
            lambda previous, bump: Ok("0.2.0"),
        )

        def _fake_stamp(root: Path, snapshot: object, version: str):  # noqa: ANN202
            stamp_calls.append(version)
            (root / ".frob-release.json").write_text("{}")
            return Ok(version)

        monkeypatch.setattr("frob.release.stamp", _fake_stamp)
        monkeypatch.setattr(ticket_runner, "_graph_snapshot", lambda root: Ok(object()))
        monkeypatch.setattr(
            "frob.gitio.run_argv",
            lambda argv, **kw: Ok(_FakeProc(0)),
        )

        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_ok
        assert result.danger_ok == "0.2.0"
        assert stamp_calls == ["0.2.0"]
        assert 'version = "0.2.0"' in (tmp_path / "pyproject.toml").read_text()

    def test_unreadable_graph_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.test_unreadable_graph_fails  # noqa: E501
        _write_repo_files(tmp_path)
        manifest = ReleaseManifest(version="0.1.0", api={})
        monkeypatch.setattr(
            ticket_runner, "_root_release_manifest", lambda root: manifest
        )
        monkeypatch.setattr(ticket_runner, "_graph_snapshot", lambda root: Err("boom"))

        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed

    # frob:ticket T-1368
    def test_stamp_failure_propagates_instead_of_staging_stale_manifest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """T-1368: `stamp`'s Result used to be discarded -- a write
        failure fell through to `git add .frob-release.json` regardless,
        staging whatever (possibly stale) content already happened to be
        on disk. It must now propagate as `Err(ReleaseBumpFailed)` and
        never reach the `git add` staging step at all."""
        # frob:tests \
        # tests/unit/test_ticket_runner_land_release.py::TestApplyReleaseBumpForLand.te\
        # st_stamp_failure_propagates_instead_of_staging_stale_manifest
        _write_repo_files(tmp_path)
        manifest = ReleaseManifest(version="0.1.0", api={})
        staged_calls: list[list[str]] = []
        monkeypatch.setattr(
            ticket_runner, "_root_release_manifest", lambda root: manifest
        )
        monkeypatch.setattr(
            "frob.release.diff_class", lambda manifest, snapshot: BumpClass.MINOR
        )
        monkeypatch.setattr(
            "frob.release.required_version",
            lambda previous, bump: Ok("0.2.0"),
        )
        monkeypatch.setattr(
            "frob.release.stamp",
            lambda root, snapshot, version: Err(ReleaseError.WriteFailed),
        )
        monkeypatch.setattr(ticket_runner, "_graph_snapshot", lambda root: Ok(object()))

        def _fake_run_argv(argv, **kw):  # noqa: ANN001, ANN202
            staged_calls.append(argv)
            return Ok(_FakeProc(0))

        monkeypatch.setattr("frob.gitio.run_argv", _fake_run_argv)

        result = ticket_runner._apply_release_bump_for_land(
            tmp_path, _FakeTicket(), "T-0001"
        )
        assert result.is_err
        assert result.danger_err == LandError.ReleaseBumpFailed
        assert staged_calls == []


# frob:ticket T-1007
class TestRootReleaseManifestReadsRootHead:
    """T-1007: `_root_release_manifest` must read `.frob-release.json` as
    committed at `root`'s git HEAD, never the worktree-carried on-disk
    copy that a `git merge --squash` can leave stale in the working tree
    before this callback ever runs -- the exact class of bug T-1007 was
    filed against."""

    def test_reads_head_manifest_not_worktree_disk_copy(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead.test_reads_head_manifest_not_worktree_disk_copy  # noqa: E501
        from frob.gitio import run_argv

        root = tmp_path / "root"
        root.mkdir()
        run_argv(["git", "init"], cwd=root)
        run_argv(["git", "config", "user.email", "t@example.com"], cwd=root)
        run_argv(["git", "config", "user.name", "T"], cwd=root)
        (root / ".frob-release.json").write_text('{"version": "0.184.0", "api": {}}\n')
        run_argv(["git", "add", ".frob-release.json"], cwd=root)
        run_argv(["git", "commit", "-m", "init"], cwd=root)

        # Simulate a stale squash-apply having overwritten the WORKING TREE
        # copy on disk with an older, worktree-carried value -- HEAD (the
        # committed object) still names main's true pre-land state.
        (root / ".frob-release.json").write_text('{"version": "0.181.0", "api": {}}\n')

        manifest = ticket_runner._root_release_manifest(root)
        assert manifest is not None
        assert manifest.version == "0.184.0"

    def test_no_manifest_at_head_returns_none(self, tmp_path: Path) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestRootReleaseManifestReadsRootHead.test_no_manifest_at_head_returns_none  # noqa: E501
        from frob.gitio import run_argv

        root = tmp_path / "root"
        root.mkdir()
        run_argv(["git", "init"], cwd=root)
        run_argv(["git", "config", "user.email", "t@example.com"], cwd=root)
        run_argv(["git", "config", "user.name", "T"], cwd=root)
        (root / "README.md").write_text("hi\n")
        run_argv(["git", "add", "README.md"], cwd=root)
        run_argv(["git", "commit", "-m", "init"], cwd=root)

        assert ticket_runner._root_release_manifest(root) is None


class _FakeProc:
    def __init__(self, returncode: int, stdout: str = "", stderr: str = "") -> None:
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


# frob:ticket T-0803
class TestLandRebuildNativesFn:
    # frob:ticket T-0803
    def test_success_returns_true(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn.test_success_returns_true  # noqa: E501
        calls: list[list[str]] = []

        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            calls.append(argv)
            return _FakeProc(0)

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._land_rebuild_natives_fn()
        assert fn(tmp_path) is True
        assert calls == [["make", "core"]]

    # frob:ticket T-0803
    def test_failure_returns_false_and_logs(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn.test_failure_returns_false_and_logs  # noqa: E501
        def _fake_run(argv, **kwargs):  # noqa: ANN001, ANN202
            return _FakeProc(1, stderr="boom")

        monkeypatch.setattr(_guard.subprocess, "run", _fake_run)
        fn = ticket_runner._land_rebuild_natives_fn()
        with caplog.at_level("WARNING", logger="frob.app.ticket_runner"):
            assert fn(tmp_path) is False
        assert any("make core" in r.message for r in caplog.records)

    # frob:ticket T-0803
    def test_kill_switch_refuses_without_spawning(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestLandRebuildNativesFn.test_kill_switch_refuses_without_spawning  # noqa: E501
        # T-0803: FROB_DISABLE_EXEC=1 must make `_land_rebuild_natives_fn`'s
        # `make core` spawn refuse (via `guarded_subprocess_run`) instead
        # of bypassing the T-0200/T-0778 exec guard -- proven with a spy on
        # the real `subprocess.run` so a spawn attempt would be observed.
        monkeypatch.setenv("FROB_DISABLE_EXEC", "1")
        spawned = False
        real_run = _guard.subprocess.run

        def _spy(*args, **kwargs):  # noqa: ANN001, ANN202
            nonlocal spawned
            spawned = True
            return real_run(*args, **kwargs)

        monkeypatch.setattr(_guard.subprocess, "run", _spy)
        fn = ticket_runner._land_rebuild_natives_fn()
        assert fn(tmp_path) is False
        assert not spawned


class _FakeRunReport:
    """Minimal stand-in for `frob.testing.TestRunReport` -- the individual-
    rerun helpers under test only ever read `.ok`."""

    def __init__(self, ok: bool) -> None:
        self.ok = ok


def _fake_run_selected(failing_ids):  # noqa: ANN001, ANN202
    """A `run_selected` stand-in: `ok=True` unless the selection's single
    language bucket contains one of `failing_ids`, mirroring a real batch
    run's "any red id makes the whole batch not-ok" exit-code semantics
    without spawning anything."""

    def fn(selection, runners, root):  # noqa: ANN001, ANN202
        items = next(iter(selection.selected.values()))
        return Ok(_FakeRunReport(ok=not any(i in failing_ids for i in items)))

    return fn


class TestReverifyFailingBucketIndividually:
    """T-0856: one failing/flaky id in a batch must not misattribute
    failure to every other id sharing that batch (the T-0588 incident)."""

    def test_only_the_genuinely_failing_id_is_excluded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually.test_only_the_genuinely_failing_id_is_excluded  # noqa: E501
        import frob.testing as _testing_mod

        monkeypatch.setattr(
            _testing_mod, "run_selected", _fake_run_selected({"tests/x.py::b"})
        )
        items = ("tests/x.py::a", "tests/x.py::b", "tests/x.py::c")
        result = ticket_runner._reverify_failing_bucket_individually(
            tmp_path, "python", items, ()
        )
        assert result == frozenset({"tests/x.py::a", "tests/x.py::c"})

    def test_quarantined_failing_id_still_counts_as_passing(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually.test_quarantined_failing_id_still_counts_as_passing  # noqa: E501
        import frob.testing as _testing_mod
        from frob.testing._stability import StabilityEntry

        monkeypatch.setattr(
            _testing_mod, "run_selected", _fake_run_selected({"tests/x.py::b"})
        )
        monkeypatch.setattr(
            "frob.testing._stability.load_stability",
            lambda root: {
                "tests/x.py::b": StabilityEntry(
                    node_id="tests/x.py::b",
                    history=("fail",),
                    quarantine_ticket="T-0575",
                )
            },
        )
        items = ("tests/x.py::a", "tests/x.py::b")
        result = ticket_runner._reverify_failing_bucket_individually(
            tmp_path, "python", items, ()
        )
        assert result == frozenset({"tests/x.py::a", "tests/x.py::b"})

    def test_non_quarantined_failing_id_excluded(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestReverifyFailingBucketIndividually.test_non_quarantined_failing_id_excluded  # noqa: E501
        import frob.testing as _testing_mod

        monkeypatch.setattr(
            _testing_mod, "run_selected", _fake_run_selected({"tests/x.py::b"})
        )
        monkeypatch.setattr("frob.testing._stability.load_stability", lambda root: {})
        items = ("tests/x.py::a", "tests/x.py::b")
        result = ticket_runner._reverify_failing_bucket_individually(
            tmp_path, "python", items, ()
        )
        assert result == frozenset({"tests/x.py::a"})


class TestVerifyOneBucketPassingRoutesToIndividualReverify:
    """T-0856: `_verify_one_bucket_passing` must reach for the individual
    reverify path (not a blanket empty set) whenever the batched run
    executed but came back not-ok for a multi-id bucket."""

    def test_batch_not_ok_falls_back_to_per_id_attribution(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # frob:tests tests/unit/test_ticket_runner_land_release.py::TestVerifyOneBucketPassingRoutesToIndividualReverify.test_batch_not_ok_falls_back_to_per_id_attribution  # noqa: E501
        import frob.testing as _testing_mod

        monkeypatch.setattr(
            _testing_mod, "run_selected", _fake_run_selected({"tests/x.py::b"})
        )
        monkeypatch.setattr("frob.testing._stability.load_stability", lambda root: {})
        result = ticket_runner._verify_one_bucket_passing(
            tmp_path, "python", ("tests/x.py::a", "tests/x.py::b"), ()
        )
        assert result == frozenset({"tests/x.py::a"})
