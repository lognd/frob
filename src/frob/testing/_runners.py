"""Runner registry loading and per-language spawn (docs/testing.md's Runner registry).

Spawns go through `frob.gitio.run_argv` -- the one process-with-timeout helper in
the package (documented in docs/testing.md's Design decisions: `frob.gitio` must
not depend on `frob.testing`, so the shared primitive lives in `gitio` and this
module imports it, rather than a second timeout-handling copy living here).
"""

from __future__ import annotations

import time
import tomllib
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


# frob:doc docs/testing.md#error-types
class TestingError(ErrorSet):
    """Failure values `frob.testing`'s executing functions can return."""

    NoRunner = "A language has selected tests but no [[test.runner]]"
    BadRunnerSpec = "Runner entry failed validation or has no placeholder"
    SpawnFailed = "Runner process could not be started or timed out"
    CollectFailed = "pytest --collect-only failed"


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


# frob:doc docs/testing.md#public-api
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
        try:
            command = tuple(entry["command"])
            all_command = tuple(entry["all_command"])
            language = entry["language"]
        except KeyError as exc:
            _log.error("load_runners: runner entry missing field %s", exc)
            return Err(TestingError.BadRunnerSpec)
        if _validate_placeholder(command) is None:
            _log.error(
                "load_runners: runner for %r has zero or multiple placeholders: %s",
                language,
                command,
            )
            return Err(TestingError.BadRunnerSpec)
        specs.append(
            RunnerSpec(
                language=language,
                command=command,
                all_command=all_command,
                cwd=entry.get("cwd", "."),
                timeout_s=entry.get("timeout_s", 900.0),
            )
        )
    _log.info("load_runners: %d runner(s) loaded from %s", len(specs), toml_path)
    return Ok(tuple(specs))


def _to_node_id(item: str) -> str:
    """A selected symref as a pytest node id: `path::A.b` -> `path::A::b`."""
    path, sep, qualname = item.partition("::")
    if not sep:
        return item
    return f"{path}::{qualname.replace('.', '::')}"


def _expand_placeholder(placeholder: str, items: tuple[str, ...]) -> list[str]:
    """The argv fragment a single placeholder expands to for `items`."""
    if placeholder == "{ids}":
        return [_to_node_id(item) for item in items]
    if placeholder == "{files}":
        return list(items)
    if placeholder == "{filters}":
        return [" ".join(items)]
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
            argv.extend(_expand_placeholder(placeholder, items))
        else:
            argv.append(part)
    return tuple(argv)


# frob:doc docs/testing.md#public-api
def run_selected(
    selection: SelectionReport, runners: tuple[RunnerSpec, ...], root: Path
) -> Result[TestRunReport, TestingError]:
    """Spawn every runner whose language has a selection; nonzero exit is data."""
    runners_by_lang = {spec.language: spec for spec in runners}
    outcomes: list[RunnerOutcome] = []
    ok = True

    for language, items in selection.selected.items():
        if not items:
            continue
        spec = runners_by_lang.get(language)
        if spec is None:
            _log.error(
                "run_selected: language %r has selected tests but no runner -- "
                "add a [[test.runner]] entry with language = %r to frob.toml at "
                "the repo root (see docs/testing.md)",
                language,
                language,
            )
            return Err(TestingError.NoRunner)

        use_all = ALL_SENTINEL in items
        argv = (
            list(spec.all_command)
            if use_all
            else list(_render_command(spec, items) or ())
        )
        if not use_all and not argv:
            _log.error(
                "run_selected: runner for %r has no usable placeholder", language
            )
            return Err(TestingError.BadRunnerSpec)

        cwd = root / spec.cwd
        start = time.monotonic()
        spawned = run_argv(argv, cwd=cwd, timeout_s=spec.timeout_s)
        duration = time.monotonic() - start
        if spawned.is_err:
            _log.error("run_selected: %s runner failed to spawn/timeout", language)
            return Err(TestingError.SpawnFailed)
        result = spawned.danger_ok
        outcome = RunnerOutcome(
            language=language,
            argv=tuple(argv),
            exit_code=result.returncode,
            duration_s=duration,
            stdout_tail=_excerpt(result.stdout),
            stderr_tail=_excerpt(result.stderr),
        )
        outcomes.append(outcome)
        if result.returncode != 0:
            ok = False
        _log.info(
            "run_selected: %s exit=%d duration=%.2fs",
            language,
            result.returncode,
            duration,
        )

    return Ok(TestRunReport(selection=selection, outcomes=tuple(outcomes), ok=ok))


__all__ = ["TestingError", "load_runners", "run_selected"]
