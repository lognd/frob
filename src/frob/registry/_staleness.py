"""T-0560: auto-file `check-coverage.yaml`'s `gate_rule_entries` for every
LIVE `known_gate_rule_ids()` rule that does not yet have one.

T-0560 splits out of T-0424's charter: the registry MODEL + honest seed
landed (`check-coverage.yaml`, REG001-009), but the CONTINUOUS half of
T-0424's own acceptance -- "gaps are found and filed before the user
notices them" -- was still a manual, someone-remembers-to-run-it step. A
genuinely scheduled daemon was considered and rejected as dishonest scope
for this pass: this repo has no always-on process host, and a cron-style
daemon would need its own supervision, logging, and failure-alerting
infrastructure this ticket does not build. The honest design instead is
what this module provides: a CHEAP, DETERMINISTIC, IDEMPOTENT sync a
human or CI step can run on any schedule (a pre-commit hook, a nightly
CI job, or by hand) -- `frob registry audit --sync-gate-rules` -- plus
`registry_gate`'s own REG010 (below in `frob.gates.
_registry_exhaustiveness`) that fails loud the moment a rule/entry pair
drifts, so staleness is caught by the NEXT `frob check` even if nobody
ever runs the sync step at all. A gate that always fires beats a
scheduler that might not run.

Every `gate_rule_entries` id this module writes is self-referentially
`handled_by:<rule-id>` (not `pending` like T-0429's general researcher
path) -- unlike an arbitrary research finding, "this rule is live in
`known_gate_rule_ids()`" IS the verification `_classify_handled_by`
performs, so the disposition is knowable with certainty at write time,
not a claim requiring later human/code-aware review.
"""

from __future__ import annotations
import re
from pathlib import Path
from typani import Err, Ok
from typani.result import Result
from frob.logging import get_logger
from frob.registry._corpus import (
    CorpusError,
    _bump_total,
    _existing_ids,
    _key_block_bounds,
    _yaml_scalar,
)
from frob.tickets._store import atomic_write

_log = get_logger(__name__)
_GATE_RULE_KEY = "gate_rule_entries"
_GATE_RULE_ID_PREFIX = "CHK-GATE-"
_GATE_RULE_ID_LINE_RE = re.compile(
    '^(\\s*)-\\s*id:\\s*"' + re.escape(_GATE_RULE_ID_PREFIX) + '([A-Za-z0-9_-]+)"\\s*$'
)
_FIXABILITY_LINE_RE = re.compile("^\\s*fixability:\\s*")


def _gate_rule_block(rule: str, fixability: str) -> str:
    """One `gate_rule_entries` item for `rule`, self-referentially
    `handled_by:<rule>` -- matches the hand-authored shape every existing
    `CHK-GATE-*` entry already uses, plus T-1264's `fixability:` field
    (`generated_fixability`'s own generated-verified value for `rule`)."""
    entry_id = f"{_GATE_RULE_ID_PREFIX}{rule}"
    return f"  - id: {_yaml_scalar(entry_id)}\n    name: {_yaml_scalar(f'{rule} is a live, enforced gate rule')}\n    disposition: {_yaml_scalar(f'handled_by:{rule}')}\n    fixability: {_yaml_scalar(fixability)}\n    cross_refs: []\n"


def missing_gate_rule_ids(
    registry_path: Path, known_rules: frozenset[str]
) -> frozenset[str]:
    """Every rule in `known_rules` with no `CHK-GATE-<rule>` id anywhere
    in `registry_path` -- `frozenset()` if the file is unreadable (the
    caller, `registry_gate`, already handles a missing/invalid file via
    its own REG005 load-error path; this helper never raises)."""
    try:
        text = registry_path.read_text(encoding="utf-8")
    except OSError as exc:
        _log.warning("missing_gate_rule_ids: %s unreadable: %s", registry_path, exc)
        return frozenset()
    lines = text.splitlines(keepends=True)
    existing = _existing_ids(lines)
    covered = {
        entry_id.removeprefix(_GATE_RULE_ID_PREFIX)
        for entry_id in existing
        if entry_id.startswith(_GATE_RULE_ID_PREFIX)
    }
    return frozenset(known_rules - covered)


def sync_gate_rule_entries(
    registry_path: Path, known_rules: frozenset[str]
) -> Result[tuple[str, ...], CorpusError]:
    """Append one `CHK-GATE-<rule>` entry (`handled_by:<rule>`) for every
    rule `missing_gate_rule_ids` finds, in sorted order, bumping
    `gate_rule_total` once for the whole batch. Idempotent: a rule
    already covered is silently skipped, never duplicated. Returns the
    sorted tuple of rule ids actually added (`()` if nothing was
    missing -- not an error, the honest "already in sync" case).

    T-1359: writes via `frob.tickets._store.atomic_write` (temp file +
    fsync + `os.replace`) rather than a bare `Path.write_text`, so a
    process killed mid-write (REG010's own Tier-A auto-fix path, the same
    T-1338 hazard class T-1348 closed for `frob.gates._fix_engine`)
    leaves `check-coverage.yaml` intact instead of half-rewritten. On the
    (should-never-happen) `atomic_write` I/O failure path, the real
    OSError detail is logged here and this returns `Err(WriteFailed)`
    (T-1533): a dedicated member distinct from the file-absent case,
    since `sync_gate_rule_entries`'s other call sites
    (`frob.app.registry_runner._run_sync_gate_rules`,
    `frob.app.ticket_runner._land_cmd`) key a message dict on
    `CorpusError` and must not confuse "file never existed" with
    "write failed after the file was read"."""
    if not registry_path.is_file():
        _log.warning("sync_gate_rule_entries: %s does not exist", registry_path)
        return Err(CorpusError.FileNotFound)
    missing = sorted(missing_gate_rule_ids(registry_path, known_rules))
    if not missing:
        _log.info("sync_gate_rule_entries: %s already in sync", registry_path)
        fixability_synced = sync_gate_rule_fixability(registry_path, known_rules)
        if fixability_synced.is_err:
            return fixability_synced
        return Ok(())
    from frob.gates._fixability_scan import generated_fixability

    fixability = generated_fixability(known_rules)
    text = registry_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    bounds = _key_block_bounds(lines, _GATE_RULE_KEY)
    if bounds is None:
        _log.warning(
            "sync_gate_rule_entries: %s has no top-level key %r",
            registry_path,
            _GATE_RULE_KEY,
        )
        return Err(CorpusError.KeyNotFound)
    _, end = bounds
    blocks = [
        _gate_rule_block(rule, fixability.get(rule, "manual")) for rule in missing
    ]
    lines[end:end] = blocks
    for _ in missing:
        lines = _bump_total(lines, _GATE_RULE_KEY)
    written = atomic_write(registry_path, "".join(lines))
    if written.is_err:
        _log.error(
            "sync_gate_rule_entries: atomic write to %s failed: %s",
            registry_path,
            written.danger_err,
        )
        return Err(CorpusError.WriteFailed)
    _log.info(
        "sync_gate_rule_entries: %s <- %d rule(s): %s",
        registry_path,
        len(missing),
        ", ".join(missing),
    )
    return Ok(tuple(missing))


def _backfill_fixability_lines(
    lines: list[str], fixability: dict[str, str]
) -> list[str]:
    """One pass over `lines` (a `check-coverage.yaml`-shaped file already
    split via `splitlines(keepends=True)`) inserting a `fixability:` field
    (4-space indent, matching `_gate_rule_block`'s own hardcoded shape)
    right after any `CHK-GATE-<rule>` entry's `- id:` line that does not
    already carry one -- mutates `lines` in place and returns the sorted
    list of rule ids actually backfilled."""
    backfilled: list[str] = []
    i = 0
    while i < len(lines):
        match = _GATE_RULE_ID_LINE_RE.match(lines[i])
        if match is None:
            i += 1
            continue
        indent, rule = (match.group(1), match.group(2))
        block_end = i + 1
        has_field = False
        while block_end < len(lines):
            line = lines[block_end]
            if _GATE_RULE_ID_LINE_RE.match(line) or (
                line.strip() and (not line.startswith(indent + "  "))
            ):
                break
            if _FIXABILITY_LINE_RE.match(line):
                has_field = True
            block_end += 1
        if not has_field and rule in fixability:
            insertion = f"    fixability: {_yaml_scalar(fixability[rule])}\n"
            lines.insert(i + 1, insertion)
            backfilled.append(rule)
            block_end += 1
        i = block_end
    backfilled.sort()
    return backfilled


def sync_gate_rule_fixability(
    registry_path: Path, known_rules: frozenset[str]
) -> Result[tuple[str, ...], CorpusError]:
    """Backfill a `fixability:` field onto every EXISTING `CHK-GATE-<rule>`
    entry that does not carry one yet -- the same idempotent
    "already-covered ids are silently skipped, never duplicated" shape
    `sync_gate_rule_entries` uses for missing entries, applied to a field
    within an entry instead of a whole entry. `generated_fixability` is
    the sole source of truth for the value written, same as
    `sync_gate_rule_entries`'s own write path -- a hand-edited fixability
    field this function overwrites is expected: the checked-in registry
    value is a GENERATED artifact, not something a maintainer authors by
    hand (this is the concrete mechanism behind acceptance criterion 3:
    "each carries a fixability: field kept in sync the same idempotent way
    gate_rule_entries already is"). Returns the sorted tuple of rule ids
    actually backfilled (`()` if every existing entry already carries the
    field)."""
    if not registry_path.is_file():
        _log.warning("sync_gate_rule_fixability: %s does not exist", registry_path)
        return Err(CorpusError.FileNotFound)
    from frob.gates._fixability_scan import generated_fixability

    fixability = generated_fixability(known_rules)
    text = registry_path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    backfilled = _backfill_fixability_lines(lines, fixability)
    if not backfilled:
        _log.info("sync_gate_rule_fixability: %s already in sync", registry_path)
        return Ok(())
    written = atomic_write(registry_path, "".join(lines))
    if written.is_err:
        _log.error(
            "sync_gate_rule_fixability: atomic write to %s failed: %s",
            registry_path,
            written.danger_err,
        )
        return Err(CorpusError.WriteFailed)
    _log.info(
        "sync_gate_rule_fixability: %s <- %d field(s): %s",
        registry_path,
        len(backfilled),
        ", ".join(backfilled),
    )
    return Ok(tuple(backfilled))


__all__ = [
    "missing_gate_rule_ids",
    "sync_gate_rule_entries",
    "sync_gate_rule_fixability",
]
