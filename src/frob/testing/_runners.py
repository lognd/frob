"""Runner registry loading and per-language spawn
(docs/modules/testing.md's Runner registry).

Spawns go through `frob.gitio.run_argv` -- the one process-with-timeout helper in
the package (documented in docs/modules/testing.md's Design decisions: `frob.gitio` must
not depend on `frob.testing`, so the shared primitive lives in `gitio` and this
module imports it, rather than a second timeout-handling copy living here).
"""

from __future__ import annotations

import os
import shutil
import time
import tomllib
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path

from typani import Err, ErrorSet, Ok
from typani.result import Result

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.testing._models import (
    RunnerOutcome,
    RunnerSpec,
    SelectionReport,
    TestRunReport,
)
from frob.testing._select import ALL_SENTINEL

_log = get_logger(__name__)

_PLACEHOLDERS = ("{ids}", "{files}", "{filters}", "{regex}")
_EXCERPT_LINES = 40

# pyo3's abi3-py311 feature (frob-core, strata-core) pins a floor: any
# interpreter frob offers `cargo test` as PYO3_PYTHON must be at least this,
# or the build fails deep inside pyo3-build-config with a cryptic message.
_PYO3_MIN_PYTHON = (3, 11)
_PYO3_PYTHON_CANDIDATES = ("python3.13", "python3.12", "python3.11")
_ENV_PROBE_TIMEOUT_S = 10.0


# frob:doc docs/modules/testing.md#error-types
class TestingError(ErrorSet):
    """Failure values `frob.testing`'s executing functions can return."""

    NoRunner = "A language has selected tests but no [[test.runner]]"
    BadRunnerSpec = "Runner entry failed validation or has no placeholder"
    SpawnFailed = "Runner process could not be started or timed out"
    CollectFailed = "pytest --collect-only failed"
    CargoEnvUnavailable = (
        "cargo test needs a Python>=3.11 dev environment (PYO3_PYTHON + a "
        "discoverable libpython) that frob could not find"
    )
    UnroutedItem = (
        "A selected item's file does not fall under exactly one same-language "
        "[[test.runner]] cwd (T-0128: multiple runners per language route by cwd)"
    )


def _excerpt(text: str, *, lines: int = _EXCERPT_LINES) -> str:
    """Bound a stdout/stderr blob to its last N lines."""
    parts = text.splitlines()
    if len(parts) <= lines:
        return text
    return "\n".join(["...(truncated)...", *parts[-lines:]])


def _validate_placeholder(command: tuple[str, ...]) -> str | None:
    """The single placeholder token present in `command`, or `None` if invalid."""
    found = [ph for ph in _PLACEHOLDERS if any(ph in part for part in command)]
    if len(found) != 1:
        return None
    return found[0]


def _parse_runner_entry(entry: dict) -> RunnerSpec | None:
    """One `[[test.runner]]` table as a `RunnerSpec`, or `None` if malformed."""
    try:
        command = tuple(entry["command"])
        all_command = tuple(entry["all_command"])
        language = entry["language"]
    except KeyError as exc:
        _log.error("load_runners: runner entry missing field %s", exc)
        return None
    if _validate_placeholder(command) is None:
        _log.error(
            "load_runners: runner for %r has zero or multiple placeholders: %s",
            language,
            command,
        )
        return None
    return RunnerSpec(
        language=language,
        command=command,
        all_command=all_command,
        cwd=entry.get("cwd", "."),
        timeout_s=entry.get("timeout_s", 900.0),
    )


# frob:doc docs/modules/testing.md#public-api
# frob:waive TEST005 reason="load_runners 76.2% branch cover, debt T-0160"
def load_runners(root: Path) -> Result[tuple[RunnerSpec, ...], TestingError]:
    """Parse `frob.toml`'s `[[test.runner]]` entries; missing file/table is `Ok(())`."""
    toml_path = root / "frob.toml"
    if not toml_path.exists():
        _log.info("load_runners: no frob.toml at %s", toml_path)
        return Ok(())
    try:
        with toml_path.open("rb") as f:
            doc = tomllib.load(f)
    except (OSError, ValueError) as exc:
        _log.error("load_runners: could not parse %s: %s", toml_path, exc)
        return Err(TestingError.BadRunnerSpec)

    entries = doc.get("test", {}).get("runner", [])
    if not entries:
        _log.info("load_runners: no [[test.runner]] entries in %s", toml_path)
        return Ok(())

    specs: list[RunnerSpec] = []
    for entry in entries:
        spec = _parse_runner_entry(entry)
        if spec is None:
            return Err(TestingError.BadRunnerSpec)
        specs.append(spec)
    _log.info("load_runners: %d runner(s) loaded from %s", len(specs), toml_path)
    return Ok(tuple(specs))


def _to_node_id(item: str) -> str:
    """A selected symref as a pytest node id: `path::A.b` -> `path::A::b`."""
    path, sep, qualname = item.partition("::")
    if not sep:
        return item
    return f"{path}::{qualname.replace('.', '::')}"


def _to_rust_filter(item: str) -> str:
    """A selected rust symref's qualname as a `cargo test` substring filter:
    `path::tests.foo` -> `tests::foo` (the path prefix cargo has no use for,
    dots rejoined with `::` to match the crate's real module path)."""
    _, sep, qualname = item.partition("::")
    if not sep:
        return item
    return qualname.replace(".", "::")


def _expand_placeholder(
    placeholder: str, items: tuple[str, ...], language: str
) -> list[str]:
    """The argv fragment a single placeholder expands to for `items`."""
    # frob:waive PERF003 reason="if-chain dispatch, one flat comprehension per branch"
    if placeholder == "{ids}":
        return [_to_node_id(item) for item in items]
    if placeholder == "{files}":
        return list(items)
    if placeholder == "{filters}":
        rendered = (
            [_to_rust_filter(i) for i in items] if language == "rust" else list(items)
        )
        return [" ".join(rendered)]
    if placeholder == "{regex}":
        return ["|".join(items)]
    return []


def _render_command(spec: RunnerSpec, items: tuple[str, ...]) -> tuple[str, ...] | None:
    """`spec.command` with its placeholder replaced by `items`, or `None` if invalid."""
    placeholder = _validate_placeholder(spec.command)
    if placeholder is None:
        return None
    argv: list[str] = []
    for part in spec.command:
        if part == placeholder:
            argv.extend(_expand_placeholder(placeholder, items, spec.language))
        else:
            argv.append(part)
    return tuple(argv)


def _build_runner_argv(
    spec: RunnerSpec, items: tuple[str, ...]
) -> Result[list[str], TestingError]:
    """The argv for `spec` given a selected item set, honoring the all-tests sentinel"""
    if ALL_SENTINEL in items:
        return Ok(list(spec.all_command))
    argv = list(_render_command(spec, items) or ())
    if not argv:
        _log.error(
            "run_selected: runner for %r has no usable placeholder", spec.language
        )
        return Err(TestingError.BadRunnerSpec)
    return Ok(argv)


# frob:doc docs/modules/testing.md#rust-runner
def _spec_owns_item(spec: RunnerSpec, item: str) -> bool:
    """True if `item`'s file path falls under `spec.cwd` (T-0128: lets several
    same-language runners -- e.g. frob-core and strata-core's cargo entries --
    coexist, each scoped to its own crate directory). `cwd = "."` owns
    everything, matching the pre-T-0128 single-runner-per-language behavior."""
    if spec.cwd in (".", ""):
        return True
    file_part = item.split("::", 1)[0]
    prefix = spec.cwd.rstrip("/") + "/"
    return file_part == spec.cwd or file_part.startswith(prefix)


# frob:doc docs/modules/testing.md#rust-runner
def _route_items(
    specs: list[RunnerSpec], items: tuple[str, ...]
) -> Result[dict[int, tuple[str, ...]], TestingError]:
    """Partition `items` across `specs` (same language) by owning `cwd`; `Err`
    -- never a silent drop -- when an item matches zero or more than one
    runner's `cwd` (T-0128)."""
    buckets: dict[int, list[str]] = {i: [] for i in range(len(specs))}
    for item in items:
        owners = [i for i, spec in enumerate(specs) if _spec_owns_item(spec, item)]
        if len(owners) != 1:
            _log.error(
                "run_selected: item %r matched %d [[test.runner]] cwd(s) for "
                "language %r (want exactly 1); refusing to guess",
                item,
                len(owners),
                specs[0].language if specs else "?",
            )
            return Err(TestingError.UnroutedItem)
        buckets[owners[0]].append(item)
    return Ok({i: tuple(v) for i, v in buckets.items()})


def _python_version(python: str) -> tuple[int, int] | None:
    """`(major, minor)` for `python`'s interpreter, or `None` if it cannot run."""
    spawned = run_argv(
        [python, "-c", "import sys; print(sys.version_info[0], sys.version_info[1])"],
        timeout_s=_ENV_PROBE_TIMEOUT_S,
    )
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    try:
        major, minor = spawned.danger_ok.stdout.split()
        return int(major), int(minor)
    except ValueError:
        return None


def _python_lib_dir(python: str) -> Path | None:
    """The directory holding `python`'s libpython, or `None` if undiscoverable."""
    probe = "import sysconfig; print(sysconfig.get_config_var('LIBDIR') or '')"
    spawned = run_argv([python, "-c", probe], timeout_s=_ENV_PROBE_TIMEOUT_S)
    if spawned.is_err or spawned.danger_ok.returncode != 0:
        return None
    libdir = spawned.danger_ok.stdout.strip()
    return Path(libdir) if libdir else None


def _find_pyo3_python() -> str | None:
    """The first interpreter meeting pyo3's abi3-py311 floor (env override first,
    then well-known `python3.NN` binaries, then plain `python3` as a last resort)."""
    override = os.environ.get("PYO3_PYTHON")
    candidates: list[str] = [override] if override else []
    candidates.extend(
        found for c in _PYO3_PYTHON_CANDIDATES if (found := shutil.which(c)) is not None
    )
    default = shutil.which("python3")
    if default is not None:
        candidates.append(default)
    for candidate in candidates:
        version = _python_version(candidate)
        if version is not None and version >= _PYO3_MIN_PYTHON:
            return candidate
    return None


# frob:doc docs/modules/testing.md#rust-runner
def _cargo_env() -> Result[dict[str, str], TestingError]:
    """The `PYO3_PYTHON` + `LD_LIBRARY_PATH` overlay a `cargo test` subprocess
    needs to link/run a PyO3 crate. `Err` -- never a fabricated pass -- when no
    Python>=3.11 interpreter with a discoverable libpython exists (T-0092: the
    known environment gap, degraded honestly instead of a cryptic linker
    failure or a silently-skipped rust run)."""
    python = _find_pyo3_python()
    if python is None:
        _log.error("cargo_env: no python>=3.11 interpreter found for PYO3_PYTHON")
        return Err(TestingError.CargoEnvUnavailable)
    lib_dir = _python_lib_dir(python)
    if lib_dir is None or not lib_dir.exists():
        _log.error("cargo_env: could not resolve a libpython dir for %s", python)
        return Err(TestingError.CargoEnvUnavailable)
    existing = os.environ.get("LD_LIBRARY_PATH", "")
    ld_path = f"{lib_dir}:{existing}" if existing else str(lib_dir)
    _log.info("cargo_env: PYO3_PYTHON=%s LD_LIBRARY_PATH+=%s", python, lib_dir)
    return Ok({"PYO3_PYTHON": python, "LD_LIBRARY_PATH": ld_path})


@contextmanager
def _env_overlay(overlay: Mapping[str, str]) -> Iterator[None]:
    """Temporarily set `overlay` into `os.environ`, restoring prior values on exit
    (shared by the cargo runner here and `frob.testing._collect`'s cargo-list
    collector -- `frob.gitio.run_argv` has no `env=` parameter, so this is the
    one place process env gets patched for a subprocess call)."""
    restore = {k: os.environ.get(k) for k in overlay}
    os.environ.update(overlay)
    try:
        yield
    finally:
        for key, value in restore.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def _run_one_runner(
    spec: RunnerSpec, items: tuple[str, ...], root: Path
) -> Result[RunnerOutcome, TestingError]:
    """Render and spawn a single runner's argv, timed into a `RunnerOutcome`."""
    built = _build_runner_argv(spec, items)
    if built.is_err:
        return Err(built.danger_err)
    argv = built.danger_ok

    env_overlay: dict[str, str] = {}
    if spec.language == "rust":
        env_result = _cargo_env()
        if env_result.is_err:
            _log.error(
                "run_selected: rust env unavailable, refusing to spawn cargo "
                "rather than let it fail vacuously"
            )
            return Err(env_result.danger_err)
        env_overlay = env_result.danger_ok

    cwd = root / spec.cwd
    start = time.monotonic()
    with _env_overlay(env_overlay):
        spawned = run_argv(argv, cwd=cwd, timeout_s=spec.timeout_s)
    duration = time.monotonic() - start
    if spawned.is_err:
        _log.error("run_selected: %s runner failed to spawn/timeout", spec.language)
        return Err(TestingError.SpawnFailed)
    result = spawned.danger_ok
    _log.info(
        "run_selected: %s exit=%d duration=%.2fs",
        spec.language,
        result.returncode,
        duration,
    )
    return Ok(
        RunnerOutcome(
            language=spec.language,
            argv=tuple(argv),
            exit_code=result.returncode,
            duration_s=duration,
            stdout_tail=_excerpt(result.stdout),
            stderr_tail=_excerpt(result.stderr),
        )
    )


def _run_language(
    specs: list[RunnerSpec], items: tuple[str, ...], root: Path
) -> Result[list[RunnerOutcome], TestingError]:
    """Every outcome for one language's selected `items`, routed across its
    (possibly several, T-0128) runners; `ALL_SENTINEL` runs every spec's
    `all_command` since a suite-wide fallback names no specific crate."""
    if ALL_SENTINEL in items:
        outcomes: list[RunnerOutcome] = []
        for spec in specs:
            outcome = _run_one_runner(spec, items, root)
            if outcome.is_err:
                return Err(outcome.danger_err)
            outcomes.append(outcome.danger_ok)
        return Ok(outcomes)

    routed = _route_items(specs, items)
    if routed.is_err:
        return Err(routed.danger_err)
    outcomes = []
    for i, spec in enumerate(specs):
        bucket = routed.danger_ok[i]
        if not bucket:
            continue
        outcome = _run_one_runner(spec, bucket, root)
        if outcome.is_err:
            return Err(outcome.danger_err)
        outcomes.append(outcome.danger_ok)
    return Ok(outcomes)


# frob:doc docs/modules/testing.md#public-api
def run_selected(
    selection: SelectionReport, runners: tuple[RunnerSpec, ...], root: Path
) -> Result[TestRunReport, TestingError]:
    """Spawn every runner whose language has a selection; nonzero exit is data.
    A language may map to several `[[test.runner]]` entries (T-0128, e.g. two
    rust crates) -- each selected item is routed to the one runner whose `cwd`
    owns its file, and an item owned by none or several is a hard error, not
    a silently-dropped test."""
    runners_by_lang: dict[str, list[RunnerSpec]] = {}
    for spec in runners:
        runners_by_lang.setdefault(spec.language, []).append(spec)
    outcomes: list[RunnerOutcome] = []
    ok = True

    for language, items in selection.selected.items():
        if not items:
            continue
        specs = runners_by_lang.get(language)
        if not specs:
            _log.error(
                "run_selected: language %r has selected tests but no runner -- "
                "add a [[test.runner]] entry with language = %r to frob.toml at "
                "the repo root (see docs/modules/testing.md)",
                language,
                language,
            )
            return Err(TestingError.NoRunner)

        run = _run_language(specs, items, root)
        if run.is_err:
            return Err(run.danger_err)
        for outcome in run.danger_ok:
            outcomes.append(outcome)
            if outcome.exit_code != 0:
                ok = False

    return Ok(TestRunReport(selection=selection, outcomes=tuple(outcomes), ok=ok))


__all__ = ["TestingError", "load_runners", "run_selected"]
