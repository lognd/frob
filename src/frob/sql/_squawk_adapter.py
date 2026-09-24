"""squawk migration-safety adapter (docs/modules/sql.md#squawk-adapter,
T-5333): spawns squawk (https://github.com/sbdchd/squawk) with its JSON
reporter against tracked `.sql` migration files and parses its output
into frob findings.

squawk is `frob.doctor.ToolCategory.REQUIRED_FOR_FAMILY` (registered in
`src/frob/doctor.py`'s `_EXTERNAL_TOOLS`/`_FAMILY_TOOL_RELEVANCE`, T-5333
extending T-5335's own machinery rather than a new tool-gating shape) --
`frob.sql._extract.sql_relevance` is reused verbatim as its relevance
predicate: absence is a FAILING, unmeasured verdict only when the repo
actually has SQL surface, never a new never-fail flag. This module never
re-probes presence itself; `squawk_findings` short-circuits to `()` when
`shutil.which("squawk")` is `None`, the same "absence is measured
elsewhere, this module just does not crash on it" posture
`frob.sql._sqlfluff_plugin`'s own docstring describes for sqlfluff.

Three anti-pattern classes squawk's own rule corpus already names
(`adding-not-nullable-field`, `require-concurrent-index-creation`/
`disallowed-index-creation`, and squawk's lock-taking-rewrite rules like
`renaming-column`/`changing-column-type`/`adding-field-with-default`) are
surfaced verbatim as `SquawkFinding`s, keyed by squawk's own `rule_name`
-- this adapter does not re-derive or re-classify squawk's findings, it
transcribes them.

Parsing (`_parse_squawk_json`) is a pure function kept separate from the
subprocess spawn (`_run_squawk`) so it is testable with a canned JSON
fixture without the real `squawk` binary installed -- the same "spawn is
a thin I/O shell around a pure parse" split `frob.check._python`'s own
tool-output parsers (`parse_ruff_json`, `parse_pytest`) already use.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.process._guard import guarded_subprocess_run

_log = get_logger(__name__)

__all__ = ["SquawkFinding", "squawk_findings"]

#: squawk's own binary name -- the `shutil.which` presence probe here,
#: the same name `frob.doctor._EXTERNAL_TOOLS`'s squawk entry registers.
_SQUAWK_BINARY = "squawk"

#: squawk's `--reporter json` CLI flag: machine-readable output instead
#: of its default human-formatted terminal report.
_SQUAWK_REPORTER_ARGS = ("--reporter", "json")

#: squawk's own `--reporter json` timeout -- generous but bounded, the
#: same order of magnitude `_probe_binary_version`'s own `--version`
#: probe budget uses, scaled up for a real lint pass over one file.
_SQUAWK_TIMEOUT_SECONDS = 30


# frob:doc docs/modules/sql.md#squawk-adapter
@dataclass(frozen=True)
class SquawkFinding:
    """One squawk finding transcribed verbatim: `rule` is squawk's own
    `rule_name` (e.g. `adding-not-nullable-field`,
    `require-concurrent-index-creation`, `renaming-column`), `file`/
    `line` the migration file and 1-based line squawk reported, `message`
    the finding's own text (squawk's `messages[0].content`, falling back
    to its `help` field when `messages` is empty).

    frob:ticket T-5333
    """

    rule: str
    file: str
    line: int
    message: str


def _tracked_sql_files(root: Path) -> tuple[str, ...]:
    """`git ls-files -- '*.sql'` under `root`, root-relative POSIX paths,
    `()` on any git failure -- mirrors `frob.sql._extract._tracked_files`'s
    own copy of this shape, narrowed to `.sql` only (squawk lints
    migration SQL files directly, not host-language call sites).

    frob:ticket T-5333
    """
    spawned = run_argv(("git", "-C", str(root), "ls-files", "--", "*.sql"))
    if spawned.is_err:
        _log.warning("squawk_adapter: git ls-files failed: %s", spawned.danger_err)
        return ()
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.warning("squawk_adapter: git ls-files exited %d", result.returncode)
        return ()
    return tuple(line for line in result.stdout.splitlines() if line.strip())


def _message_text(entry: dict) -> str:  # noqa: ANN201 -- str, trivial helper
    """squawk's `messages[0].content` if present, else its own `help`
    text, else a generic fallback -- never raises on a malformed/partial
    JSON object (T-5333's own fail-soft posture for third-party tool
    output).

    frob:ticket T-5333
    """
    messages = entry.get("messages")
    if isinstance(messages, list) and messages:
        first = messages[0]
        if isinstance(first, dict):
            content = first.get("content")
            if isinstance(content, str) and content:
                return content
    help_text = entry.get("help")
    if isinstance(help_text, str) and help_text:
        return help_text
    return "squawk finding (no message text reported)"


def _line_number(entry: dict) -> int:  # noqa: ANN201 -- int, trivial helper
    """squawk's `line_number` field (its own JSON reporter's key), `0`
    when absent/unparseable rather than raising.

    frob:ticket T-5333
    """
    raw = entry.get("line_number")
    if isinstance(raw, int):
        return raw
    return 0


# frob:doc docs/modules/sql.md#squawk-adapter
# frob:ticket T-5333
def _parse_squawk_json(text: str, rel_path: str) -> tuple[SquawkFinding, ...]:
    """squawk's own `--reporter json` output (a JSON array of finding
    objects) parsed into `SquawkFinding`s for `rel_path`. `()` on empty
    output or any JSON decode failure (never raises -- a third-party
    tool's own malformed output is not this adapter's bug to crash on).

    frob:ticket T-5333
    """
    text = text.strip()
    if not text:
        return ()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError as exc:
        _log.warning("squawk_adapter: %s: unparseable squawk JSON: %s", rel_path, exc)
        return ()
    if not isinstance(parsed, list):
        _log.warning("squawk_adapter: %s: squawk JSON was not a list", rel_path)
        return ()
    findings: list[SquawkFinding] = []
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        rule = entry.get("rule_name")
        if not isinstance(rule, str) or not rule:
            continue
        findings.append(
            SquawkFinding(
                rule=rule,
                file=rel_path,
                line=_line_number(entry),
                message=_message_text(entry),
            )
        )
    return tuple(findings)


def _run_squawk(path: Path, rel_path: str) -> tuple[SquawkFinding, ...]:
    """Spawn `squawk <path> --reporter json` and parse its output for one
    migration file -- `()` on any spawn failure (exec disabled, squawk
    crashed, timeout), logged at WARNING and never raised, the same
    fail-soft posture every other doctor-gated tool adapter in this repo
    follows (`_probe_binary_version`'s own docstring).

    frob:ticket T-5333
    """
    result = guarded_subprocess_run(
        [_SQUAWK_BINARY, str(path), *_SQUAWK_REPORTER_ARGS],
        capture_output=True,
        text=True,
        timeout=_SQUAWK_TIMEOUT_SECONDS,
        check=False,
    )
    if result.is_err:
        _log.warning(
            "squawk_adapter: %s: squawk spawn refused: %s", rel_path, result.danger_err
        )
        return ()
    proc = result.danger_ok
    # squawk exits non-zero when it has findings (like ruff/eslint) --
    # its stdout is still the JSON report to parse, not a crash signal.
    return _parse_squawk_json(proc.stdout or "", rel_path)


# frob:doc docs/modules/sql.md#squawk-adapter
# frob:ticket T-5333
def squawk_findings(root: Path) -> tuple[SquawkFinding, ...]:
    """Every squawk finding across tracked `.sql` files under `root` --
    `()` immediately when `squawk` is not on PATH (its
    REQUIRED_FOR_FAMILY absence is `frob.doctor.family_required_tool_
    findings`'s own concern, not re-reported here) or when there are no
    tracked `.sql` files at all.

    frob:ticket T-5333
    """
    root = Path(root)
    if shutil.which(_SQUAWK_BINARY) is None:
        _log.debug("squawk_adapter: squawk not on PATH, skipping scan")
        return ()
    findings: list[SquawkFinding] = []
    for rel in _tracked_sql_files(root):
        findings.extend(_run_squawk(root / rel, rel))
    _log.info("squawk_adapter: %d finding(s) under %s", len(findings), root)
    return tuple(findings)
