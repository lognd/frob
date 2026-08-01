"""CLI wiring for `frob release stamp|check` (T-0003)."""

from __future__ import annotations

import sys
from pathlib import Path

from frob.app._snapshot import load_or_build_snapshot
from frob.app.config import AppConfig
from frob.logging import get_logger
from frob.render import Renderer

_log = get_logger(__name__)


# frob:ticket T-0003
# frob:doc docs/modules/app.md#runners
# frob:ticket T-0588
# frob:tests tests/unit/test_app_runners_batch5.py::TestReleaseRunner.test_stamp_success_writes_manifest  # noqa: E501
def run(cfg: AppConfig) -> None:
    """Dispatch to the release subcommand named by `cfg.release_command`."""
    root = (cfg.release_path or Path(".")).resolve()

    match cfg.release_command:
        case "stamp":
            _stamp(root, cfg)
        case "check":
            _check(root)
        case "sync":
            _sync(root)
        case _:
            _log.error("usage: frob release <stamp|check|sync>")
            sys.exit(1)


def _version(root: Path) -> str:
    import tomllib

    toml_path = root / "pyproject.toml"
    if not toml_path.exists():
        _log.error("release: no pyproject.toml at %s", root)
        sys.exit(1)
    with toml_path.open("rb") as fh:
        version = tomllib.load(fh).get("project", {}).get("version")
    if not isinstance(version, str):
        _log.error("release: no [project].version in pyproject.toml")
        sys.exit(1)
    return version


# frob:ticket T-0562
# frob:ticket T-1381
def _stamp(root: Path, cfg: AppConfig) -> None:
    from frob.release import stamp

    version = _version(root)
    if cfg.release_allow_unbumped:
        _log.warning(
            "release stamp: --allow-unbumped set -- stamping an API change at an "
            "un-bumped version rebaselines REL001 against the OLD version "
            "(justification required)"
        )
    result = stamp(
        root,
        load_or_build_snapshot(root, log_context="release"),
        version,
        allow_unbumped=cfg.release_allow_unbumped,
    )
    if result.is_err:
        _log.error("release stamp failed: %s", result.danger_err)
        sys.exit(1)
    Renderer.for_stream(sys.stdout).line(
        f"stamped public API at {version} -> .frob-release.json"
    )


# frob:ticket T-0562
def _check(root: Path) -> None:
    from frob.release import diff_class, load_manifest, required_version, satisfies

    manifest_result = load_manifest(root)
    if manifest_result.is_err:
        _log.error("release check: %s", manifest_result.danger_err)
        sys.exit(1)
    manifest = manifest_result.danger_ok
    version = _version(root)
    bump = diff_class(manifest, load_or_build_snapshot(root, log_context="release"))
    need = required_version(manifest.version, bump)
    ok = need.is_ok and satisfies(version, need.danger_ok)
    target = need.danger_ok if need.is_ok else "?"
    Renderer.for_stream(sys.stdout).line(
        f"since {manifest.version}: {bump.name.lower()} change -> "
        f"need >= {target} (current {version}): {'OK' if ok else 'BUMP REQUIRED'}"
    )
    if not ok:
        sys.exit(1)


# frob:ticket T-1009
def _sync(root: Path) -> None:
    """`frob release sync`: `.frob-release.json` is the ONE version
    authority (T-1009) -- regenerate `pyproject.toml`'s `version`, `uv.lock`
    (`uv lock`), and a CHANGELOG.md skeleton entry from it, so a hand-edit
    to any derived artifact is corrected rather than left to silently
    disagree until REL002 catches it at the next `frob check`."""
    from frob.gitio import run_argv
    from frob.release import (
        authoritative_version,
        changelog_skeleton_entry,
        rewrite_pyproject_version,
    )

    version_result = authoritative_version(root)
    if version_result.is_err:
        _log.error("release sync: %s", version_result.danger_err)
        sys.exit(1)
    version = version_result.danger_ok

    rewritten = rewrite_pyproject_version(root, version)
    if rewritten.is_err:
        _log.error("release sync: %s", rewritten.danger_err)
        sys.exit(1)
    if rewritten.danger_ok:
        Renderer.for_stream(sys.stdout).line(f"pyproject.toml: version -> {version}")

    if (root / "pyproject.toml").exists():
        locked = run_argv(["uv", "lock"], cwd=root, timeout_s=120.0)
        if locked.is_err or locked.danger_ok.returncode != 0:
            _log.error(
                "release sync: uv lock failed -- %s",
                locked.danger_err if locked.is_err else locked.danger_ok.stderr,
            )
            sys.exit(1)
        Renderer.for_stream(sys.stdout).line("uv.lock: synced")

    if changelog_skeleton_entry(root, version):
        Renderer.for_stream(sys.stdout).line(
            f"CHANGELOG.md: added skeleton entry for {version}"
        )

    Renderer.for_stream(sys.stdout).line(f"release sync complete at {version}")
