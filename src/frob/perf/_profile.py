"""`profile_command`/`load_artifact`: spawn-under-cProfile and artifact
storage (docs/perf.md's Profile piece).

Reuses `frob.gitio.run_argv` -- the package's one subprocess-with-timeout
seam -- rather than a second `subprocess.run` call site; `frob.gitio`'s own
docstring names this exact reuse contract ("the small public wrapper
`frob.testing` reuses ... never a second copy").
"""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

from typani import Err, Ok
from typani.result import Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.perf._models import PerfError, ProfileArtifact

_log = get_logger(__name__)

__all__ = ["load_artifact", "profile_command"]

_PERF_DIR = Path(".frob") / "perf"
_PROFILE_TIMEOUT_S = 600.0


# frob:ticket T-0021
def _artifact_sha(argv: Sequence[str], created: datetime) -> str:
    """Content address: sha256 over argv plus creation timestamp -- two runs
    of the same command a second apart never collide on disk."""
    hasher = hashlib.sha256()
    hasher.update("\x1f".join(argv).encode())
    hasher.update(created.isoformat().encode())
    return hasher.hexdigest()[:16]


# frob:doc docs/perf.md#public-api
# frob:ticket T-0021
def profile_command(
    argv: Sequence[str], root: Path
) -> Result[ProfileArtifact, PerfError]:
    """Run `argv` under `python -m cProfile`, storing a content-addressed
    `.pstats` artifact plus a JSON meta sidecar under `.frob/perf/`."""
    perf_dir = root / _PERF_DIR
    perf_dir.mkdir(parents=True, exist_ok=True)

    created = datetime.now(UTC)
    sha = _artifact_sha(tuple(argv), created)
    pstats_path = perf_dir / f"{sha}.pstats"

    # `cProfile -o out <script> [args...]` already provides the interpreter;
    # a caller-supplied leading "python"/"python3" (the natural way to write
    # `frob perf profile -- python -c '...'`) would otherwise be handed to
    # cProfile as the "script" and immediately fail to parse as one.
    script_argv = list(argv)
    if script_argv and script_argv[0] in ("python", "python3"):
        script_argv = script_argv[1:]
    full_argv = ["python", "-m", "cProfile", "-o", str(pstats_path), *script_argv]
    _log.info("profile_command: spawning %s", full_argv)
    start = time.monotonic()
    spawned = run_argv(full_argv, cwd=root, timeout_s=_PROFILE_TIMEOUT_S)
    total_s = time.monotonic() - start

    if spawned.is_err:
        _log.error("profile_command: spawn failed for %s", full_argv)
        return Err(PerfError.SpawnFailed)
    result = spawned.danger_ok
    if result.returncode != 0 or not pstats_path.exists():
        _log.error(
            "profile_command: %s exited %d, artifact present=%s",
            full_argv,
            result.returncode,
            pstats_path.exists(),
        )
        return Err(PerfError.SpawnFailed)

    artifact = ProfileArtifact(
        sha=sha, argv=tuple(argv), created=created, total_s=total_s
    )
    meta_path = perf_dir / artifact.meta_name
    meta_path.write_text(artifact.model_dump_json(), encoding="utf-8")
    _log.info(
        "profile_command: artifact sha=%s total_s=%.3f at %s",
        sha,
        total_s,
        pstats_path,
    )
    return Ok(artifact)


# frob:doc docs/perf.md#public-api
# frob:ticket T-0021
def load_artifact(
    root: Path, ref: str | None = None
) -> Result[ProfileArtifact, PerfError]:
    """Load a `ProfileArtifact`'s meta sidecar by sha (`ref`), or the most
    recently created one when `ref` is `None`."""
    perf_dir = root / _PERF_DIR
    if not perf_dir.is_dir():
        _log.warning("load_artifact: no perf dir at %s", perf_dir)
        return Err(PerfError.NoArtifact)

    meta_paths = sorted(perf_dir.glob("*.json"))
    if not meta_paths:
        _log.warning("load_artifact: no artifacts under %s", perf_dir)
        return Err(PerfError.NoArtifact)

    if ref is not None:
        candidate = perf_dir / f"{ref}.json"
        if not candidate.exists():
            _log.warning("load_artifact: no artifact for ref=%s", ref)
            return Err(PerfError.NoArtifact)
        chosen = candidate
    else:
        chosen = max(meta_paths, key=lambda p: p.stat().st_mtime)

    try:
        data = json.loads(chosen.read_text(encoding="utf-8"))
        artifact = ProfileArtifact.model_validate(data)
    except (OSError, ValueError) as exc:
        _log.error("load_artifact: could not read/parse %s: %s", chosen, exc)
        return Err(PerfError.BadArtifact)

    pstats_path = perf_dir / artifact.pstats_name
    if not pstats_path.exists():
        _log.error("load_artifact: pstats file missing for sha=%s", artifact.sha)
        return Err(PerfError.BadArtifact)

    _log.info("load_artifact: loaded sha=%s (%s)", artifact.sha, chosen)
    return Ok(artifact)
