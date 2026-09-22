"""CLI wiring for `frob run <name> [--dry-run]` and `frob build [--dry-run]`
(T-4759): one declared home (`frob.toml`'s `[commands]` table) for every
project workflow command, so a scaffolded project's Makefile can be a thin
derived shim over this instead of authoring its own recipe logic (audit
5.1's "make or frob" decision).

Wired the same way `frob bind`/`agent`/`worktree` are (see
`frob.app.bind_runner`'s module docstring): `run(argv)`/`run_build(argv)`
take raw sub-argv and own their own parser, bypassing the
`AppConfig`/`Subcommand` dispatch table entirely -- `frob run` has no
ticket/graph state to load, and wiring it through `frob.app.app`'s
`_SUBCOMMAND_RUNNER_NAMES` dict would mean touching `src/frob/app/app.py`,
which is leased by another in-progress ticket (T-4689) at the time this
ticket landed; a follow-up ticket (T-4759's own report) tracks moving
`--help` discoverability into `frob._cli_parsers._root._build_parser`
once its lease (T-4546) clears.

`[commands]` semantics (docs/commands/run.md is authoritative):

- a name maps to EITHER a single shell-free argv (`fmt = ["ruff",
  "format", "."]`) or an ordered array of steps run in sequence, where
  each step is a nested argv or the bare name of another entry
  (`check = ["fmt", "lint", "test"]`);
- a bare array of strings that ALL match declared entry names is treated
  as a composed sequence of references (`check` above); otherwise it is
  a single literal argv (an ordinary command generally does not happen
  to share every one of its tokens with the names of other declared
  entries);
- `test`/`lint`/`format`/`check` fall back to frob's own native verbs
  when a project declares no `[commands]` table entry for them at all,
  so a Python project need declare nothing (`_NATIVE_DEFAULTS` below);
  `build` has no native fallback -- a project with no `build` entry gets
  a clear error naming that, not a silent no-op.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import time
import tomllib
from pathlib import Path

from typani import Err, Ok
from typani.error_set import ErrorSet
from typani.result import Result

from frob.logging import get_logger
from frob.policy._models import CommandEntry, CommandsConfig, CommandsError

_log = get_logger(__name__)

__all__ = ["run", "run_build"]


# frob:ticket T-4759
_NATIVE_DEFAULTS: dict[str, tuple[str, ...]] = {
    "test": ("frob", "test"),
    "lint": ("frob", "check", "--only", "lint"),
    "format": ("frob", "format"),
    "check": ("frob", "check"),
}
"""The frob-native argv each of `test`/`lint`/`format`/`check` resolves to
when a project declares no `[commands]` entry of that name at all -- the
"a Python project declares nothing" half of the ticket. `build` has no
entry here on purpose: there is no frob-native build step to fall back to."""


# frob:doc docs/commands/run.md#error-types
# frob:ticket T-4759
class RunError(ErrorSet):
    """Failure values `frob run`/`frob build`'s resolution and execution
    paths can return."""

    UnknownCommand = "no [commands] entry (or frob-native default) by that name"
    StepFailed = "a resolved step exited non-zero"


def _frob_toml_path(root: Path) -> Path:
    """The `frob.toml` this project's `[commands]` table is read from."""
    return root / "frob.toml"


def _normalize_raw_entry(raw: object, *, known_names: frozenset[str]) -> tuple:
    """Normalize one raw TOML `[commands]` value into a `CommandEntry`-
    shaped tuple of steps.

    A flat array of strings whose elements ALL name a declared entry is
    treated as a composed sequence of references (`check = ["fmt",
    "lint", "test"]`); any other array of strings is one literal argv
    (`fmt = ["ruff", "format", "."]`); an array containing a nested array
    is unambiguous and always a sequence, one step per element."""
    if isinstance(raw, str):
        return (raw,)
    if not isinstance(raw, list):
        return (tuple(),)
    if all(isinstance(e, str) for e in raw):
        if raw and all(e in known_names for e in raw):
            return tuple(raw)
        return (tuple(raw),)
    steps: list[str | tuple[str, ...]] = []
    for element in raw:
        if isinstance(element, str):
            steps.append(element)
        elif isinstance(element, list):
            steps.append(tuple(str(token) for token in element))
        else:
            steps.append(())
    return tuple(steps)


def _detect_cycle(
    entries: dict[str, CommandEntry], name: str
) -> tuple[str, ...] | None:
    """Depth-first search for a reference cycle starting at `name`;
    returns the full reference path (`name` repeated at both ends) if one
    exists, else `None`."""

    def _walk(current: str, path: tuple[str, ...]) -> tuple[str, ...] | None:
        if current in path:
            return (*path, current)
        entry = entries.get(current)
        if entry is None:
            return None
        for step in entry.steps:
            if isinstance(step, str):
                found = _walk(step, (*path, current))
                if found is not None:
                    return found
        return None

    return _walk(name, ())


# frob:doc docs/commands/run.md#commands-table
# frob:ticket T-4759
def load_commands(root: Path) -> Result[CommandsConfig, CommandsError]:
    """Parse `frob.toml`'s `[commands]` table into a `CommandsConfig`,
    refusing (at load time, before anything runs) any entry that
    references itself directly or transitively -- the error names the
    full reference path."""
    toml_path = _frob_toml_path(root)
    if not toml_path.exists():
        _log.info("load_commands: no frob.toml at %s", toml_path)
        return Ok(CommandsConfig(entries={}))
    with toml_path.open("rb") as handle:
        doc = tomllib.load(handle)
    raw_table = doc.get("commands", {})
    if not isinstance(raw_table, dict):
        _log.warning("load_commands: %s: [commands] is not a table", toml_path)
        return Err(CommandsError.MalformedEntry)
    known_names = frozenset(str(k) for k in raw_table.keys())
    entries: dict[str, CommandEntry] = {}
    for name, raw_value in raw_table.items():
        try:
            entries[name] = CommandEntry(
                steps=_normalize_raw_entry(raw_value, known_names=known_names)
            )
        except Exception:
            _log.warning(
                "load_commands: %s: entry %r failed validation", toml_path, name
            )
            return Err(CommandsError.MalformedEntry)
    for name in entries:
        cycle_path = _detect_cycle(entries, name)
        if cycle_path is not None:
            _log.error(
                "load_commands: %s: cycle detected: %s",
                toml_path,
                " -> ".join(cycle_path),
            )
            return Err(CommandsError.CycleDetected)
    _log.info("load_commands: %s: %d entr(y/ies) loaded", toml_path, len(entries))
    return Ok(CommandsConfig(entries=entries))


def _resolve_sequence(
    config: CommandsConfig, name: str, *, seen: tuple[str, ...] = ()
) -> Result[tuple[tuple[str, ...], ...], RunError]:
    """Flatten `name` (a declared entry, or a frob-native default) into a
    concrete ordered tuple of argv tuples -- cycles are already refused
    at `load_commands` time, so this only expands references."""
    entry = config.entries.get(name)
    if entry is None:
        native = _NATIVE_DEFAULTS.get(name)
        if native is None:
            _log.error("resolve: %r is not a declared entry or native default", name)
            return Err(RunError.UnknownCommand)
        return Ok((native,))
    argvs: list[tuple[str, ...]] = []
    for step in entry.steps:
        if isinstance(step, str):
            sub = _resolve_sequence(config, step, seen=(*seen, name))
            if sub.is_err:
                return sub
            argvs.extend(sub.danger_ok)
        else:
            argvs.append(step)
    return Ok(tuple(argvs))


def _execute_sequence(
    steps: tuple[tuple[str, ...], ...], *, dry_run: bool
) -> Result[None, RunError]:
    """Run `steps` in order, shell-free, logging each one's index,
    command, and duration; stops at the first non-zero exit and names
    that step's index and command in the error log."""
    if dry_run:
        for index, argv in enumerate(steps):
            _log.info("run --dry-run: step %d: %s", index, " ".join(argv))
        return Ok(None)
    for index, argv in enumerate(steps):
        started = time.monotonic()
        _log.info("run: step %d starting: %s", index, " ".join(argv))
        proc = subprocess.run(argv)
        duration_s = time.monotonic() - started
        _log.info(
            "run: step %d finished: %s (exit=%d, %.2fs)",
            index,
            " ".join(argv),
            proc.returncode,
            duration_s,
        )
        if proc.returncode != 0:
            _log.error(
                "run: step %d failed (exit=%d): %s",
                index,
                proc.returncode,
                " ".join(argv),
            )
            return Err(RunError.StepFailed)
    return Ok(None)


def _run_entry(name: str, *, dry_run: bool) -> int:
    """Shared body of `run`/`run_build`: load, resolve, and execute `name`
    from the current working directory's `frob.toml`; returns the process
    exit code."""
    root = Path(".").resolve()
    loaded = load_commands(root)
    if loaded.is_err:
        _log.error("frob run: %s: %s", name, loaded.danger_err)
        return 1
    resolved = _resolve_sequence(loaded.danger_ok, name)
    if resolved.is_err:
        _log.error("frob run: %s: %s", name, resolved.danger_err)
        return 1
    executed = _execute_sequence(resolved.danger_ok, dry_run=dry_run)
    if executed.is_err:
        return 1
    return 0


def _build_run_parser() -> argparse.ArgumentParser:
    """Argument parser for `frob run <name> [--dry-run]`."""
    p = argparse.ArgumentParser(prog="frob run")
    p.add_argument("name", help="a [commands] entry name, or a native default")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the resolved sequence without running anything",
    )
    return p


def _build_build_parser() -> argparse.ArgumentParser:
    """Argument parser for `frob build [--dry-run]`."""
    p = argparse.ArgumentParser(prog="frob build")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="print the resolved sequence without running anything",
    )
    return p


# frob:doc docs/commands/run.md#public-api
# frob:ticket T-4759
def run(argv: list[str] | None = None) -> None:
    """`frob run <name> [--dry-run]`: execute one `[commands]` entry (or a
    frob-native default for `test`/`lint`/`format`/`check`) by name.
    Exits non-zero (matching every other direct-dispatch runner's
    convention) on any resolution or step failure."""
    args = _build_run_parser().parse_args(argv)
    sys.exit(_run_entry(args.name, dry_run=args.dry_run))


# frob:doc docs/commands/run.md#public-api
# frob:ticket T-4759
def run_build(argv: list[str] | None = None) -> None:
    """`frob build [--dry-run]`: delegate straight to the `build`
    `[commands]` entry -- carries no build logic of its own, per the
    ticket's "make a build verb delegate to the build entry rather than
    carrying its own logic" instruction."""
    args = _build_build_parser().parse_args(argv)
    sys.exit(_run_entry("build", dry_run=args.dry_run))
