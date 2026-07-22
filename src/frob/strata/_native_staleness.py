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

**T-0513 (strata audit G9): mtime alone is defeated by a bare `touch`.**
A `touch`/`os.utime` on the built artifact (no rebuild) advances its mtime
past a genuinely newer source edit with no content change at all -- the
mtime-only check above would report clean against genuinely stale compiled
code, since it compares TIMESTAMPS, never bytes. `stale_natives` now ALSO
maintains a small persisted content-digest stamp
(`.frob/native-content-stamps.json`, `_load_stamps`/`_save_stamps`) per
native: whenever the mtime check reports "not stale," it additionally
computes a source-tree content digest (`_source_content_digest`, over
every non-pruned file's path+bytes, deterministic and order-stable) and
reuses `frob.testing._collect._native_artifact_digest` (T-0333's own
built-artifact-bytes hash, the SAME "friend" cross-module reuse
`_compiled_artifacts` already establishes -- charter: no duplication) for
the artifact side. If the STORED artifact digest from the last observation
still matches (the compiled bytes have not changed since last time) but
the STORED source digest no longer matches CURRENT source content, the
source changed with NO corresponding rebuild -- exactly the touch-without-
rebuild signature -- and this now reports `StaleNative` via
`reason="content-digest"` even though mtime alone said "fresh." A real
rebuild (which changes the compiled artifact's bytes) is distinguished
correctly: the artifact digest changes too, so the stamp is simply
refreshed, no false positive. First observation of a given native (no
stamp on disk yet) trusts mtime and records a baseline -- there is no
prior content to compare against, the same "nothing to compare against
yet" posture `_newest_mtime`'s `None`-for-missing-directory case already
takes.

Two call sites (T-0248's plan):
- `frob.tickets._land.land` warns (does not block) when a just-landed source
  tree outpaces its own built native, so the coordinator sees it immediately
  after landing a grammar/native change instead of discovering it via a
  confusing SYS004 on the next unrelated `frob check`.
- `make check` (Makefile) calls `check_native_staleness_or_exit` first, so a
  stale native fails the read-only gate loudly instead of silently checking
  against old parser/grammar logic.
"""
# frob:waive INV006 reason="T-0585 INV006 first-turn-on pool: \
# src/frob/strata/_native_staleness.py's exclusivity-vocabulary hit is source-level \
# design-rationale/scope-cut prose (a docstring or comment describing \
# already-implemented internal behavior, verifiable by reading the code it annotates) \
# rather than a separate cross-module contract needing its own tracked invariant; \
# disposed as a calibration batch, not claim-by-claim"

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from frob.excludes import walk_pruned
from frob.logging import get_logger
from frob.testing._collect import _compiled_artifacts, _native_artifact_digest
from frob.testing._models import NativeSpec
from frob.testing._runners import load_natives

_log = get_logger(__name__)

#: T-0513: where the per-native content-digest stamp (source digest +
#: artifact digest at the last "not stale by mtime" observation) is
#: persisted -- `.frob/` is this repo's own local-state directory
#: convention (mirrors `.frob/pytest-collect.json`'s cache, `_collect.py`).
_STAMP_REL = Path(".frob") / "native-content-stamps.json"

#: Native-crate source roots this repo builds via `make core` (mirrors
#: T-0333's `[[native]]` entries in frob.toml). A native whose `name`
#: (underscores) does not correspond to one of these directories (hyphens)
#: is skipped -- this module only speaks to natives it can locate source for.
# frob:doc docs/modules/testing.md#public-api
NATIVE_SOURCE_DIRS: tuple[str, ...] = ("strata-core", "frob-core")


# frob:doc docs/modules/testing.md#public-api
@dataclass(frozen=True)
class StaleNative:
    """One declared `[[native]]` whose built artifact is OLDER than its own
    source tree -- the exact `make core` reminder T-0248 automates.
    `reason` (T-0513): `"mtime"` for the original timestamp-only detection,
    `"content-digest"` when mtime alone said "fresh" but the artifact-bytes
    digest was unchanged while the source-tree digest was NOT (a touch
    without a rebuild) -- distinguishing the two matters for the warning
    text (T-0166's genuine "you forgot to rebuild" vs the touch-attack
    class this ticket closes)."""

    spec: NativeSpec
    source_dir: str
    artifact_mtime: float
    source_mtime: float
    reason: str = "mtime"


def _newest_mtime(directory: Path) -> float | None:
    """Latest mtime among every regular file under `directory` (pruning
    `frob.excludes.BUILTIN_SKIP_DIRS` via `walk_pruned`), or `None` if
    `directory` does not exist -- an absent source dir can never be "stale"
    against anything."""
    if not directory.is_dir():
        return None
    newest: float | None = None
    for path in walk_pruned(directory):
        try:
            mtime = path.stat().st_mtime
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


def _source_content_digest(directory: Path) -> str:
    """T-0513: an order-stable sha256 over every non-pruned file's
    (relative path, content bytes) under `directory` -- the source-tree
    digest `stale_natives` compares against the persisted stamp so a bare
    mtime touch (no byte change) can never look like a genuine edit.
    Deliberately hashes ALL files under the crate dir (not only `*.rs` +
    `Cargo.toml`/`Cargo.lock` as the ticket's own suggestion names) --
    narrowing to specific extensions would silently miss a real source
    change in a file the narrower list forgot (a build script, a vendored
    grammar asset); recall-over-precision is the same posture
    `frob.vet._capability`'s needle philosophy already takes for exactly
    this reason. An unreadable file is skipped (mirrors `_newest_mtime`'s
    own `except OSError: continue`), not fatal -- one unreadable file
    should degrade the digest's precision, not crash the whole check."""
    hasher = hashlib.sha256()
    for path in sorted(walk_pruned(directory), key=lambda p: p.as_posix()):
        try:
            content = path.read_bytes()
        except OSError:
            continue
        hasher.update(path.relative_to(directory).as_posix().encode())
        hasher.update(b"\0")
        hasher.update(hashlib.sha256(content).digest())
        hasher.update(b"\n")
    return hasher.hexdigest()


def _stamp_path(root: Path) -> Path:
    """Where T-0513's per-native content-digest stamps live under `root`."""
    return root / _STAMP_REL


def _load_stamps(root: Path) -> dict[str, dict[str, str]]:
    """T-0513: the persisted `{name: {"source": ..., "artifact": ...}}`
    stamp map, or `{}` for a missing/malformed file -- a corrupt or absent
    stamp degrades to "no prior observation" (every native's next
    not-stale-by-mtime check re-bootstraps its baseline), never a crash."""
    path = _stamp_path(root)
    try:
        raw = path.read_text()
    except OSError:
        return {}
    try:
        loaded = json.loads(raw)
    except json.JSONDecodeError:
        _log.warning("native staleness: malformed stamp file %s, ignoring", path)
        return {}
    if not isinstance(loaded, dict):
        return {}
    return loaded


def _save_stamps(root: Path, stamps: dict[str, dict[str, str]]) -> None:
    """Persist T-0513's stamp map, creating `.frob/` if needed -- best
    effort: a write failure is logged, not raised (the stamp is an
    optimization/detection aid, never a correctness-load-bearing file the
    rest of `frob` depends on existing)."""
    path = _stamp_path(root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(stamps, sort_keys=True, indent=2) + "\n")
    except OSError as exc:
        _log.warning("native staleness: could not write stamp file %s: %s", path, exc)


# frob:doc docs/modules/testing.md#public-api
# frob:tests tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_reports_native_grammar_ahead_of_native  # noqa: E501
# frob:tests tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_fresh_native_reports_nothing  # noqa: E501
# frob:tests tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_unbuilt_native_is_not_reported_as_stale  # noqa: E501
# frob:tests tests/unit/strata/test_native_staleness.py::TestStaleNatives.test_no_matching_source_dir_is_not_reported  # noqa: E501
# frob:waive ARCH001 reason="T-0513's mtime-then-content-digest tiers are an intentionally ORDERED decision tree over one persisted stamps dict (first-observation baseline, touch-without-rebuild detection, genuine-rebuild refresh) with stamps/stamps_changed mutated across the loop; splitting a tier into a helper would require returning multiple mutations (stale entry, stamp update, changed flag) back out, adding indirection without reducing the ordered reasoning itself"  # noqa: E501
def stale_natives(root: Path) -> tuple[StaleNative, ...]:
    """Every declared `[[native]]` (T-0333's `frob.toml` `[[native]]` table)
    whose built artifact is older than its own source tree under `root`
    (T-0248) -- the class of incident that produced a spurious, hard-to-
    diagnose SYS004 during the T-0166 review: a grammar change landed on
    `main` (or was edited locally) without a following `make core` rebuild.

    Deliberately excludes natives that are not built at all (T-0333's
    `missing_natives` territory) and natives with no matching declared
    source directory (nothing to compare against).

    T-0513: when the mtime check alone says "not stale," a second,
    content-digest-based check runs (module docstring) -- a bare `touch`
    on the built artifact can advance its mtime past a genuine source edit
    with no byte change at all, which mtime comparison structurally cannot
    detect. That second check needs a persisted baseline (`_load_stamps`/
    `_save_stamps`) from the LAST such observation; the very first
    observation of a given native has nothing to compare against yet and
    trusts mtime, recording a baseline for next time."""
    root = Path(root)
    loaded = load_natives(root)
    if loaded.is_err:
        _log.warning(
            "stale_natives: could not load [[native]] entries (%s)",
            loaded.danger_err,
        )
        return ()
    stale: list[StaleNative] = []
    stamps = _load_stamps(root)
    stamps_changed = False
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
                    reason="mtime",
                )
            )
            continue
        # T-0513: mtime says fresh -- verify via content digest, which a
        # bare touch cannot fake.
        source_digest = _source_content_digest(root / source_dir)
        artifact_digest = _native_artifact_digest(spec)
        prior = stamps.get(spec.name)
        if prior is None:
            # first observation of this native -- nothing to compare
            # against, trust mtime and record the baseline.
            stamps[spec.name] = {"source": source_digest, "artifact": artifact_digest}
            stamps_changed = True
            continue
        if artifact_digest == prior.get("artifact") and source_digest != prior.get(
            "source"
        ):
            # the compiled artifact's bytes have NOT changed since the
            # last observation, yet the source tree HAS -- the exact
            # touch-without-rebuild signature this ticket exists to catch.
            stale.append(
                StaleNative(
                    spec=spec,
                    source_dir=source_dir,
                    artifact_mtime=artifact_mtime,
                    source_mtime=source_mtime,
                    reason="content-digest",
                )
            )
            # do NOT overwrite the stamp here -- the next run must keep
            # detecting the same unrebuilt edit until a real rebuild
            # actually changes the artifact bytes.
            continue
        if source_digest != prior.get("source") or artifact_digest != prior.get(
            "artifact"
        ):
            # a genuine rebuild happened (artifact bytes changed) -- or
            # this is the first digest-comparable run after a legitimate
            # edit+rebuild cycle. Refresh the baseline.
            stamps[spec.name] = {"source": source_digest, "artifact": artifact_digest}
            stamps_changed = True
    if stamps_changed:
        _save_stamps(root, stamps)
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
    (T-0248). T-0513: when ANY reported native was caught only via the
    content-digest check (mtime alone said fresh), the message says so
    explicitly -- a caller who trusts mtime output at a glance should not
    mistake this for the ordinary "you forgot to rebuild" case."""
    stale = stale_natives(root)
    if not stale:
        return None
    names = ", ".join(sorted({s.spec.name for s in stale}))
    dirs = ", ".join(sorted({s.source_dir for s in stale}))
    build_cmds = " && ".join(sorted({s.spec.build_cmd for s in stale}))
    digest_only = sorted({s.spec.name for s in stale if s.reason == "content-digest"})
    digest_note = (
        f" [{', '.join(digest_only)}] detected via content digest only "
        "(built artifact bytes unchanged since last check, but source "
        "tree content changed -- a bare touch cannot mask this);"
        if digest_only
        else ""
    )
    return (
        f"STALE NATIVE: built extension(s) [{names}] predate their own "
        f"source tree ({dirs});{digest_note} frob check/frob test will "
        f"silently run against the OLD native until you rebuild. "
        f"Run: {build_cmds}"
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
