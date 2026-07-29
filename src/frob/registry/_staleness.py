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
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

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

_log = get_logger(__name__)

_GATE_RULE_KEY = "gate_rule_entries"
_GATE_RULE_ID_PREFIX = "CHK-GATE-"


def _gate_rule_block(rule: str) -> str:
    """One `gate_rule_entries` item for `rule`, self-referentially
    `handled_by:<rule>` -- matches the hand-authored shape every existing
    `CHK-GATE-*` entry already uses."""
    entry_id = f"{_GATE_RULE_ID_PREFIX}{rule}"
    return (
        f"  - id: {_yaml_scalar(entry_id)}\n"
        f"    name: {_yaml_scalar(f'{rule} is a live, enforced gate rule')}\n"
        f"    disposition: {_yaml_scalar(f'handled_by:{rule}')}\n"
        f"    cross_refs: []\n"
    )


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#reg010-gate-rule-staleness-t-0560  # noqa: E501
# frob:ticket T-0560
# frob:tests tests/test_registry_staleness.py::TestMissingGateRuleIds.test_finds_rules_with_no_entry kind="unit"  # noqa: E501
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


# frob:doc docs/design/registry/EXHAUSTIVENESS-GATE.md#reg010-gate-rule-staleness-t-0560  # noqa: E501
# frob:ticket T-0560
# frob:tests tests/test_registry_staleness.py::TestSyncGateRuleEntries.test_appends_every_missing_rule kind="unit"  # noqa: E501
def sync_gate_rule_entries(
    registry_path: Path, known_rules: frozenset[str]
) -> Result[tuple[str, ...], CorpusError]:
    """Append one `CHK-GATE-<rule>` entry (`handled_by:<rule>`) for every
    rule `missing_gate_rule_ids` finds, in sorted order, bumping
    `gate_rule_total` once for the whole batch. Idempotent: a rule
    already covered is silently skipped, never duplicated. Returns the
    sorted tuple of rule ids actually added (`()` if nothing was
    missing -- not an error, the honest "already in sync" case)."""
    if not registry_path.is_file():
        _log.warning("sync_gate_rule_entries: %s does not exist", registry_path)
        return Err(CorpusError.FileNotFound)

    missing = sorted(missing_gate_rule_ids(registry_path, known_rules))
    if not missing:
        _log.info("sync_gate_rule_entries: %s already in sync", registry_path)
        return Ok(())

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

    blocks = [_gate_rule_block(rule) for rule in missing]
    lines[end:end] = blocks
    for _ in missing:
        lines = _bump_total(lines, _GATE_RULE_KEY)

    registry_path.write_text("".join(lines), encoding="utf-8")
    _log.info(
        "sync_gate_rule_entries: %s <- %d rule(s): %s",
        registry_path,
        len(missing),
        ", ".join(missing),
    )
    return Ok(tuple(missing))


__all__ = ["missing_gate_rule_ids", "sync_gate_rule_entries"]
