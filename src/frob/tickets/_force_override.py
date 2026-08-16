"""frob.tickets._force_override -- the shared `--force` audit-trail
primitive (T-1762): `ScopeChangeEntry`/`AcceptanceAmendmentEntry`/
`EvidenceChangeEntry`/`AckAuditEntry`'s append-only-audit-record
discipline (T-0455/T-1422/T-1733/T-1317) applied to `--force`.

T-1762's own finding: `frob ticket archive --force` and `frob ticket
land --finish --force` each bypass a real safety guard (T-0843's
live-lease refusal, T-1715's worktree-in-use refusal) with no
`--reason`, no log line, and no record -- the exact "discharge an
obligation more cheaply than the honest way" shape T-1733 named and
fixed for `evidence --replace`, reintroduced twice more since. This
module is the one shared fix: every `--force` bypass costs a required
reason, a WARNING naming the guard it skipped, and one append-only line
in `force-overrides.jsonl` (repo root, git-tracked -- the same
"root-level append-only JSONL audit log" shape `rapid-debt.jsonl`
already established in this repo) recording what was overridden, why,
by whom, and when.
"""

from __future__ import annotations

import getpass
import json
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict
from typani import Err, ErrorSet, Ok
from typani.result import Result
from typani.unit import Unit

from frob.logging import get_logger

_log = get_logger(__name__)

_FORCE_OVERRIDES_REL = "force-overrides.jsonl"


# frob:ticket T-1762
# frob:doc docs/modules/tickets-data-storage.md#data-models
class ForceOverrideEntry(BaseModel):
    """One append-only audit line for a `--force` bypass of a tracked
    safety guard (T-1762): which command, which guard, why, who, when,
    and what target it was applied to. Never edited or removed once
    written, only appended to `force-overrides.jsonl`."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    command: str
    guard: str
    target: str
    reason: str
    actor: str
    at: date


# frob:doc docs/modules/tickets-data-storage.md#data-models
class ForceOverrideError(ErrorSet):
    """Failure values `record_force_override` can return."""

    ReasonMissing = "a --force bypass requires --reason (T-1762)"
    WriteFailed = "could not append to force-overrides.jsonl"


def _current_actor() -> str:
    """Best-effort identity for a `ForceOverrideEntry.actor` field (T-1762)
    -- the OS login name, or `"unknown"` if the platform/sandbox refuses
    to report one (never raises). Duplicated one-liner from
    `frob.tickets._scope._current_actor` and siblings rather than
    imported -- same load-order-independence tradeoff those already
    accept relative to each other."""
    try:
        return getpass.getuser()
    except OSError:
        return "unknown"


# frob:ticket T-1762
# frob:doc docs/modules/tickets-data-storage.md#data-models
# frob:tests tests/test_tickets_organization.py::TestForceOverrideAudit.test_record_force_override_requires_reason  # noqa: E501
# frob:tests tests/test_tickets_organization.py::TestForceOverrideAudit.test_record_force_override_appends_a_line  # noqa: E501
# frob:waive SELFAUDIT001 reason="T-1762: an append-only audit-trail write into this \
# ticket-tracked repo's own root, the exact same shape node=tickets_ledger already \
# declares fs.write for elsewhere (tickets.md/tickets/**) -- force-overrides.jsonl is \
# the same ledger-adjacent audit surface, not a new capability class"
def record_force_override(
    root: Path,
    *,
    command: str,
    guard: str,
    target: str,
    reason: str,
    actor: str | None = None,
) -> Result[Unit, ForceOverrideError]:
    """Refuse (`Err(ReasonMissing)`) a blank `reason`; otherwise log a
    WARNING naming `guard` and append one `ForceOverrideEntry` line to
    `root/force-overrides.jsonl` -- the honest cost every `--force` bypass
    of a tracked safety guard must now pay (T-1762). Callers still perform
    the actual bypass themselves; this only makes it accountable, never
    silent."""
    if not reason.strip():
        _log.warning("force override: %s refused, --reason is blank", command)
        return Err(ForceOverrideError.ReasonMissing)
    resolved_actor = actor if actor is not None else _current_actor()
    entry = ForceOverrideEntry(
        command=command,
        guard=guard,
        target=target,
        reason=reason,
        actor=resolved_actor,
        at=date.today(),
    )
    _log.warning(
        "force override: %s bypassed guard=%s target=%s reason=%r",
        command,
        guard,
        target,
        reason,
    )
    path = root / _FORCE_OVERRIDES_REL
    try:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry.model_dump(mode="json"), sort_keys=True))
            handle.write("\n")
    except OSError as exc:
        _log.error("force override: could not append to %s: %s", path, exc)
        return Err(ForceOverrideError.WriteFailed)
    return Ok(Unit())


__all__ = [
    "ForceOverrideEntry",
    "ForceOverrideError",
    "record_force_override",
]
