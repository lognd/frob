"""Detect a stale-native landing hazard (T-0248).

Incident precedent: T-0166 landed a `strata-core/**` grammar change and
`design/frob.strata` began using the new construct, but main's *built*
`strata_core` predated the change -- `frob check` reported SYS004 (a design
file failing to load, which also suppresses SYS001 project-wide) until the
coordinator manually ran `make core` and reinstalled the tool. Nothing
compared the native SOURCE tree against the built artifact's own provenance
to say so directly.

This module is that comparison: for each declared `[[native]]` whose crate
lives under one of `NATIVE_SOURCE_DIRS`, compare the newest mtime under the
source tree against the newest mtime among the built compiled artifact(s)
(`.so`/`.pyd`/`.dylib`) backing the importable module. Artifact discovery is
NOT reimplemented here -- `frob.testing._collect._compiled_artifacts` (the
T-0333 precedent) is reused as-is, so there is exactly one place in the repo
that knows how to find the compiled output behind a native module name.

Two call sites (T-0248's plan):
- `frob.tickets._land.land` warns (does not block) when a just-landed source
  tree outpaces its own built native, so the coordinator sees it immediately
  after landing a grammar/native change instead of discovering it via a
  confusing SYS004 on the next unrelated `frob check`.
- `make check` (Makefile) calls `check_native_staleness_or_exit` first, so a
  stale native fails the read-only gate loudly instead of silently checking
  against old parser/grammar logic.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from frob.logging import get_logger
from frob.testing._collect import _compiled_artifacts
from frob.testing._models import NativeSpec
from frob.testing._runners import load_natives

_log = get_logger(__name__)

#: Native-crate source roots this repo builds via `make core` (mirrors
#: T-0333's `[[native]]` entries in frob.toml). A native whose `name`
#: (underscores) does not correspond to one of these directories (hyphens)
#: is skipped -- this module only speaks to natives it can locate source for.
# frob:doc docs/modules/testing.md#public-api
NATIVE_SOURCE_DIRS: tuple[str, ...] = ("strata-core", "frob-core")

#: Directory names never worth walking for a source-tree mtime: build
#: output (would make a native look "stale against itself" the moment it
#: is built) and VCS/cache dirs that touch on every checkout unrelated to
#: source content.
_PRUNED_DIR_NAMES = frozenset({"target", ".git", "__pycache__", "node_modules"})


# frob:doc docs/modules/testing.md#public-api
@dataclass(frozen=True)
class StaleNative:
    """One declared `[[native]]` whose built artifact is OLDER than its own
    source tree -- the exact `make core` reminder T-0248 automates."""

    spec: NativeSpec
    source_dir: str
    artifact_mtime: float
    source_mtime: float


def _newest_mtime(directory: Path) -> float | None:
    """Latest mtime among every regular file under `directory` (pruning
    `_PRUNED_DIR_NAMES`), or `None` if `directory` does not exist -- an
    absent source dir can never be "stale" against anything."""
    if not directory.is_dir():
        return None
    newest: float | None = None
    for dirpath, dirnames, filenames in os.walk(directory):
        dirnames[:] = [d for d in dirnames if d not in _PRUNED_DIR_NAMES]
        for name in filenames:
            try:
                mtime = (Path(dirpath) / name).stat().st_mtime
            except OSError:
                continue
            if newest is None or mtime > newest:
                newest = mtime
    return newest


def _artifact_mtime(spec: NativeSpec) -> float | None:
    """Newest mtime among `spec`'s built compiled artifacts (via
    `frob.testing._collect._compiled_artifacts`, T-0333's discovery), or
    `None` if the native is not built at all. An unbuilt native is a
    *missing*-native diagnostic (T-0333's `missing_natives`), a different
    remedy from "rebuild" -- this function deliberately does not conflate
    the two."""
    try:
        found = importlib.util.find_spec(spec.name)
    except (ImportError, ValueError) as exc:
        _log.debug("native staleness: find_spec(%r) raised %s", spec.name, exc)
        return None
    if found is None:
        return None
    artifacts = _compiled_artifacts(found)
    if not artifacts:
        return None
    mtimes: list[float] = []
    for artifact in artifacts:
        try:
            mtimes.append(artifact.stat().st_mtime)
        except OSError as exc:
            _log.debug("native staleness: could not stat %s: %s", artifact, exc)
    return max(mtimes) if mtimes else None


def _source_dir_for(root: Path, spec: NativeSpec) -> str | None:
    """Which of `NATIVE_SOURCE_DIRS` backs `spec`, matched via the
    underscore/hyphen convention every native crate here follows
    (`strata_core` module name <-> `strata-core` crate directory)."""
    candidate = spec.name.replace("_", "-")
    for source_dir in NATIVE_SOURCE_DIRS:
        if source_dir == candidate and (root / source_dir).is_dir():
            return source_dir
    return None


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_reports_native_grammar_ahead_of_native  # noqa: E501
# frob:tests tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_fresh_native_reports_nothing  # noqa: E501
# frob:tests tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_unbuilt_native_is_not_reported_as_stale  # noqa: E501
# frob:tests tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_no_matching_source_dir_is_not_reported  # noqa: E501
def stale_natives(root: Path) -> tuple[StaleNative, ...]:
    """Every declared `[[native]]` (T-0333's `frob.toml` `[[native]]` table)
    whose built artifact is older than its own source tree under `root`
    (T-0248) -- the class of incident that produced a spurious, hard-to-
    diagnose SYS004 during the T-0166 review: a grammar change landed on
    `main` (or was edited locally) without a following `make core` rebuild.

    Deliberately excludes natives that are not built at all (T-0333's
    `missing_natives` territory) and natives with no matching declared
    source directory (nothing to compare against)."""
    root = Path(root)
    loaded = load_natives(root)
    if loaded.is_err:
        _log.warning(
            "stale_natives: could not load [[native]] entries (%s)",
            loaded.danger_err,
        )
        return ()
    stale: list[StaleNative] = []
    for spec in loaded.danger_ok:
        source_dir = _source_dir_for(root, spec)
        if source_dir is None:
            continue
        source_mtime = _newest_mtime(root / source_dir)
        if source_mtime is None:
            continue
        artifact_mtime = _artifact_mtime(spec)
        if artifact_mtime is None:
            continue
        if source_mtime > artifact_mtime:
            stale.append(
                StaleNative(
                    spec=spec,
                    source_dir=source_dir,
                    artifact_mtime=artifact_mtime,
                    source_mtime=source_mtime,
                )
            )
    if stale:
        _log.warning(
            "stale_natives: %d native(s) stale vs their own source: %s",
            len(stale),
            [s.spec.name for s in stale],
        )
    else:
        _log.debug("stale_natives: none stale under %s", root)
    return tuple(stale)


# frob:doc docs/modules/testing.md#public-api
def stale_native_warning(root: Path) -> str | None:
    """One human-readable LOUD warning naming every stale native under
    `root` and the remedy (its `build_cmd`), or `None` if none are stale --
    the message `frob ticket land` logs before its final commit and `make
    check` prints (and fails on) via `check_native_staleness_or_exit`
    (T-0248)."""
    stale = stale_natives(root)
    if not stale:
        return None
    names = ", ".join(sorted({s.spec.name for s in stale}))
    dirs = ", ".join(sorted({s.source_dir for s in stale}))
    build_cmds = " && ".join(sorted({s.spec.build_cmd for s in stale}))
    return (
        f"STALE NATIVE: built extension(s) [{names}] predate their own "
        f"source tree ({dirs}); frob check/frob test will silently run "
        f"against the OLD native until you rebuild. Run: {build_cmds}"
    )


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/unit/strata/test_native_staleness.py::TestCheckNativeStalenessOrExit.test_exits_nonzero_and_prints_when_stale  # noqa: E501
# frob:tests tests/unit/strata/test_native_staleness.py::TestCheckNativeStalenessOrExit.test_returns_none_when_not_stale  # noqa: E501
def check_native_staleness_or_exit(root: Path) -> None:
    """`make check` entry point (T-0248): print `stale_native_warning` to
    stderr and `sys.exit(1)` if `root`'s natives are stale, else return
    normally. Kept as a standalone pre-step (not folded into `frob check`'s
    gate pipeline) so a native-crate rebuild reminder never depends on the
    full gate machinery being importable/healthy."""
    warning = stale_native_warning(root)
    if warning is not None:
        print(warning, file=sys.stderr)
        sys.exit(1)


__all__ = [
    "NATIVE_SOURCE_DIRS",
    "StaleNative",
    "check_native_staleness_or_exit",
    "stale_native_warning",
    "stale_natives",
]
