"""frob.gates._fix_engine_scope -- scope/lease enforcement for Tier-A
auto-fix output (T-2284).

Every `TIER_A_HANDLERS` entry (`frob.gates._fix_engine.apply_tier_a_fixes`)
writes to disk unconditionally, wherever its own scan finds a fixable
finding -- none of them consult the landing ticket's declared `scope` or
any other ticket's live lease before writing. During a land this is a real
defect, not just noise: `frob ticket land` auto-commits every Tier-A fix
alongside the landing ticket's own diff, so a handler that reformats a file
OUTSIDE the landing ticket's scope (T-2274's own land hit this against
`scripts/fleet_status.py`, which `scripts/check_summary.py`'s own T-2236
held a live lease on at the time) either ships as an undisclosed passenger
of the wrong ticket, or -- since `CrossTicketLeakage` (`frob.tickets.
_land._check_cross_ticket_leakage`) DOES catch it -- refuses the whole
land and forces a manual revert. Both outcomes are wrong: the first is the
exact silent-attribution hole T-2274 just closed for the bookkeeping-
commit staging path; the second is real friction (the guard IS supposed to
catch it, but the auto-fix should never have written there in the first
place).

`filter_fixes_by_scope_and_lease` is the fix: called once per handler,
right after it runs, on ITS OWN return value -- never inside a handler
(every handler keeps its existing signature and existing all-repo scan;
narrowing WHERE it writes belongs to the caller of dozens of otherwise-
identical handlers, not duplicated into each one). A fix whose file is
outside the landing ticket's scope, or under another ticket's live lease,
is reverted (`git checkout --`, the file's own last-committed content) and
reported as a `SkippedFix` -- never silently dropped (T-2255's own lesson:
a silent skip is worse than a loud one) and never left half-applied on
disk for `CrossTicketLeakage` to catch after the fact.

Outside a land (`ticket_id=None`, the bare `frob check --fix` CLI path):
every fix passes through unfiltered. There is no "landing ticket" to scope
against in that context, and `frob check --fix`'s existing unscoped
behavior (fix everything findable, repo-wide) is deliberate, not a gap
this ticket touches.

**Lease precedence (T-2284 acceptance[1]).** A file under another ticket's
live lease is skipped even when it is ALSO within the landing ticket's own
declared scope. The lease check runs, and can refuse, independently of
the scope check; scope alone can never override it. Reasoning: a live
lease (`frob.tickets._leases.is_effectively_in_progress`) is a real-time,
measured fact -- another agent is actively working that file right now,
in a DIFFERENT worktree, this exact instant. A declared `scope` is a
static intention recorded once at `frob ticket new`/`scope` time; two
tickets' scopes can legitimately overlap (a broad `src/frob/**` alongside
a narrow `src/frob/tickets/_land.py`, T-2225's own worked example) without
either agent being wrong to have written it that way. Overlapping
intentions are normal and harmless until one of them is actually being
acted on; a live lease is the signal that one now is. Deferring to
declared scope over a live lease would let a Tier-A handler barge into a
file mid-edit under a different ticket purely because that ticket's OWN
scope entry also happened to name it -- exactly the concurrent-write
hazard `CrossTicketLeakage`/lease enforcement exists to prevent elsewhere
in this same codebase.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel

from frob.gates._fix_engine_shared import FixApplied
from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets import TicketQueue, scope_matches
from frob.tickets._leases import is_effectively_in_progress

_log = get_logger(__name__)


# frob:ticket T-2284
#: Rule ids this filter never applies to -- a NAMED, disclosed exemption
#: (T-2284 acceptance[4]: "if one exists, say what it should do instead
#: rather than silently exempting it"), not a handler that happens to
#: pass every scope/lease check by coincidence. `REL002` is the one
#: member today: `fix_rel002_release_sync` writes `pyproject.toml`/
#: `CHANGELOG.md`/`uv.lock` -- files docs/guides/agent-playbook.md
#: section 4b already forbids declaring in ANY ticket's own scope (they
#: are land-owned, exclusively written by `frob ticket land` itself,
#: never a worktree's declared work); a scope check against them would
#: not catch a genuine leak, it would revert REL002's own correct,
#: load-bearing output on every single land. Genuinely repo-wide by
#: design, not merely broad -- the exemption belongs on the rule, named
#: and reasoned here, rather than reverting real release-sync state and
#: leaving REL001 to fail confusingly afterward.
_REPO_WIDE_EXEMPT_RULES = frozenset({"REL002"})


# frob:ticket T-2284
# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests \
# tests/test_gates.py::TestFixEngineScopeLease.test_out_of_scope_fix_is_reverted_and_re\
# ported kind="unit"
class SkippedFix(BaseModel):
    """One Tier-A fix a handler produced but `filter_fixes_by_scope_and_
    lease` refused to keep -- same identity a kept `FixApplied` carries
    (rule/file/line) plus WHY, so a skip is exactly as legible as an
    applied fix in the land's own output, never a bare drop."""

    model_config = {}

    rule: str
    file: str
    line: int
    reason: str


# frob:ticket T-2284
def _other_ticket_holding_live_lease(
    root: Path, queue: TicketQueue, ticket_id: str, path: str
) -> str | None:
    """The id of the first OTHER ticket in `queue` whose declared scope
    covers `path` and is effectively in progress right now (state or a
    live cross-worktree lease, `is_effectively_in_progress`), or `None`.
    Deliberately ignores `ticket_id`'s own scope entirely -- lease
    precedence, see this module's own docstring."""
    for other_id, other in queue.tickets.items():
        if other_id == ticket_id:
            continue
        if not scope_matches(path, other.scope, kind=other.kind, ticket_id=other_id):
            continue
        if is_effectively_in_progress(root, other_id, other.state):
            return other_id
    return None


# frob:ticket T-2284
def _revert_fix_file(root: Path, fix: FixApplied) -> None:
    """Undo a single handler-made edit `filter_fixes_by_scope_and_lease`
    disqualified: `git checkout -- <file>` restores `fix.file` to its
    last-committed content. Safe unconditionally -- a file scope/lease
    disqualifies can never ALSO carry the landing ticket's own legitimate
    uncommitted work (that work would itself be inside the landing
    ticket's scope, which is exactly the case this function is never
    called for). Best-effort: a checkout failure is logged loudly and
    swallowed, never raised -- `CrossTicketLeakage` still refuses the
    land outright if leaked content somehow survives this, so this is a
    courtesy that narrows the common case, not the only line of defense."""
    result = run_argv(["git", "-C", str(root), "checkout", "--", fix.file])
    if result.is_err or result.danger_ok.returncode != 0:
        _log.warning(
            "tier-a fixes: could not revert disqualified %s (rule=%s): %s -- "
            "CrossTicketLeakage may still refuse this land if it survives",
            fix.file,
            fix.rule,
            result.danger_err if result.is_err else result.danger_ok.stderr,
        )


# frob:ticket T-2284
# frob:doc docs/modules/gates.md#--fix-tier-a-deterministic-auto-fix-handlers-t-1138
# frob:tests \
# tests/test_gates.py::TestFixEngineScopeLease.test_out_of_scope_fix_is_reverted_and_re\
# ported kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineScopeLease.test_live_leased_file_skipped_even_when_\
# in_landing_scope kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineScopeLease.test_in_scope_fix_is_kept_unchanged \
# kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineScopeLease.test_no_ticket_id_passes_every_fix_throu\
# gh_unfiltered kind="unit"
# frob:tests \
# tests/test_gates.py::TestFixEngineScopeLease.test_rel002_is_a_named_repo_wide_exempti\
# on_not_a_silent_pass kind="unit"
def filter_fixes_by_scope_and_lease(
    root: Path,
    queue: TicketQueue,
    ticket_id: str | None,
    fixes: list[FixApplied],
) -> tuple[list[FixApplied], list[SkippedFix]]:
    """Partition one handler's own `fixes` into `(kept, skipped)` -- see
    this module's own docstring for the full mechanism and the lease-
    over-scope precedence rule. `ticket_id=None` (no land in progress)
    is always a no-op: `(fixes, [])`, byte-identical to pre-T-2284
    behavior."""
    if ticket_id is None:
        return fixes, []
    ticket = queue.tickets.get(ticket_id)
    kept: list[FixApplied] = []
    skipped: list[SkippedFix] = []
    for fix in fixes:
        if fix.rule in _REPO_WIDE_EXEMPT_RULES:
            kept.append(fix)
            continue
        lease_holder = _other_ticket_holding_live_lease(
            root, queue, ticket_id, fix.file
        )
        if lease_holder is not None:
            _revert_fix_file(root, fix)
            skipped.append(
                SkippedFix(
                    rule=fix.rule,
                    file=fix.file,
                    line=fix.line,
                    reason=f"{fix.file} is under {lease_holder}'s live lease",
                )
            )
            continue
        in_scope = ticket is not None and scope_matches(
            fix.file, ticket.scope, kind=ticket.kind, ticket_id=ticket_id
        )
        if not in_scope:
            _revert_fix_file(root, fix)
            skipped.append(
                SkippedFix(
                    rule=fix.rule,
                    file=fix.file,
                    line=fix.line,
                    reason=(f"{fix.file} is outside {ticket_id}'s declared scope"),
                )
            )
            continue
        kept.append(fix)
    return kept, skipped


__all__ = ["SkippedFix", "filter_fixes_by_scope_and_lease"]
