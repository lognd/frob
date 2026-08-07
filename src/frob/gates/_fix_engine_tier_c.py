"""frob.gates._fix_engine_tier_c -- Tier-C fix-it emission for agents (T-1263).

Third tier of the T-1137 `--fix` epic, per docs/design/check-fix-engine.md's
"Fix-it emission format" section: a Tier-C finding is one `--fix` can never
mechanically discharge -- the remedy needs judgment, or the candidate set is
ambiguous/empty -- so instead of touching a file, this module emits a
structured `FixIt` an agent (or a human) can act on: the original violation's
own message VERBATIM (never paraphrased), plus an optional machine-proposed
patch and a mandatory, non-empty `reason_unfixable`.

Wiring `--fix --json`'s output to include the resulting `fixits` array is a
later batch of the same epic (this ticket's scope is
`src/frob/gates/_fix_engine_tier_c.py`/`tests/test_gates.py`, not
`src/frob/app/**`/`src/frob/_cli_parsers/**` -- the same split T-1138/T-1262
drew for Tier A/B); `apply_tier_c_fixits`, this module's public entry point,
is ready for that CLI batch to call directly.

Real Tier-C emitter shipped here: `emit_todo001_fixit`, TODO001's own
"content-required, no mechanical rewrite" case (a bare untracked to-do
comment with no ticket to bind it to -- `_fix_engine.py`'s module
docstring already names this as the canonical Tier-C example). No
function in this module ever calls a filesystem write.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from pydantic import BaseModel

from frob.gates._models import Violation
from frob.graph import GraphSnapshot

_log = logging.getLogger(__name__)


# frob:doc docs/design/check-fix-engine.md#fix-it-emission-format-tier-c-for-agents
class FixIt(BaseModel):
    """One Tier-C finding an agent/human can act on: the ORIGINAL
    violation's own `message` verbatim (never paraphrased -- every gate
    message already embeds its own remedy, `_models.Violation`'s own
    docstring), an optional unified-diff `proposed_patch` (`None` when no
    mechanical proposal exists at all -- common, not a bug), and a
    mandatory, non-empty `reason_unfixable` -- the same "always disclose
    why" posture `WAIVE001` already enforces for waivers, applied here to
    "why didn't --fix touch this" instead."""

    model_config = {}

    rule: str
    file: str
    line: int
    message: str
    proposed_patch: str | None
    reason_unfixable: str


#: One rule id -> one Tier-C emitter, the Tier-C sibling of
#: `_fix_engine.TIER_A_HANDLERS`/`_fix_engine_tier_b.TIER_B_HANDLERS` --
#: same uniform-shape convention (a rule id keys exactly one of the three
#: tables, T-1264's `FixabilityConflict` will enforce this mechanically),
#: but this table's callable takes the single `Violation` it emits a
#: `FixIt` for (or `None`, when THIS particular violation instance has no
#: emission -- e.g. a TODO001 finding that already carries a ticket
#: reference and so is not really unfixable at all) rather than scanning
#: the whole tree itself; Tier C never mutates, so there is nothing to
#: apply repo-wide the way Tier A/B's handlers do.
TierCEmitter = Callable[[Path, GraphSnapshot, Violation], "FixIt | None"]


# ---------------------------------------------------------------------------
# TODO001: a bare todo/fixme comment with no ticket id bound to it -- the
# canonical Tier-C case named in _fix_engine.py's own module docstring.
# ---------------------------------------------------------------------------

#: `_todo_fmt.py`'s own TODO001 message shape: "TODO001: bare comment at
#: {file}:{lineno}; bind it: ..." -- matched narrowly (rather than emitting
#: for every rule this module might one day cover) so this emitter only
#: ever fires for the ONE rule id it is registered under.
_TODO001_PREFIX = "TODO001:"


# frob:doc docs/design/check-fix-engine.md#fix-it-emission-format-tier-c-for-agents
# frob:tests \
# tests/test_gates.py::TestFixEngineTierC.test_todo001_emits_a_fixit_with_no_proposed_p\
# atch kind="unit"
# frob:waive WIRE001 reason="only reachable via TIER_C_EMITTERS/ apply_tier_c_fixits, \
# both of which are themselves only called from this module's own tests until T-1481 \
# wires a real --fix caller -- the whole Tier-C engine is deliberately CLI-uncalled in \
# this ticket's own scope" follow_up="T-1481"
def emit_todo001_fixit(
    root: Path, snapshot: GraphSnapshot, violation: Violation
) -> FixIt | None:
    """Tier-C emitter (T-1263): a bare TODO001 finding (an untracked
    todo/fixme comment) has no mechanical rewrite -- binding it to a real
    ticket id is a human/agent judgment call `--fix` must never guess at
    (fabricating a ticket reference would be strictly worse than leaving
    the comment alone). Always returns a `FixIt` with `proposed_patch=
    None` for any `Violation` whose `rule` is `"TODO001"`; `None` for any
    other rule (this emitter's own registration key already guarantees
    only TODO001 findings are ever passed in via `TIER_C_EMITTERS`, but
    the guard keeps this function correct standalone too, e.g. under
    direct test)."""
    del root, snapshot  # signature uniformity only; this emitter is pure
    if violation.rule != "TODO001" or not violation.message.startswith(_TODO001_PREFIX):
        return None
    return FixIt(
        rule=violation.rule,
        file=violation.file,
        line=violation.line,
        message=violation.message,
        proposed_patch=None,
        reason_unfixable=(
            "binding a bare TODO/FIXME to a real ticket id is a judgment call "
            "--fix must never guess at"
        ),
    )


#: The Tier-C sibling of `_fix_engine.TIER_A_HANDLERS`/`_fix_engine_tier_b.
#: TIER_B_HANDLERS` -- a rule id present here must NEVER also appear in
#: either of those two tables (T-1264's `FixabilityConflict` enforces this
#: mechanically once it lands).
# frob:doc docs/design/check-fix-engine.md#fix-it-emission-format-tier-c-for-agents
TIER_C_EMITTERS: dict[str, TierCEmitter] = {
    "TODO001": emit_todo001_fixit,
}


# frob:doc docs/design/check-fix-engine.md#fix-it-emission-format-tier-c-for-agents
# frob:waive WIRE001 reason="apply_tier_c_fixits's own public entry point -- T-1263's \
# scope is the emitter table/model itself (src/frob/gates/_fix_engine_tier_c.py, \
# tests/test_gates.py only), not the CLI wiring; T-1481 is the open follow-up ticket \
# that wires --fix --json's fixits array to call this, mirroring \
# apply_tier_a_fixes/apply_tier_b_fixes's own T-1138/T-1260/T-1262 split" \
# follow_up="T-1481"
def apply_tier_c_fixits(
    root: Path, snapshot: GraphSnapshot, violations: tuple[Violation, ...]
) -> list[FixIt]:
    """Run every registered `TIER_C_EMITTERS` entry over `violations`,
    keyed by each violation's own `rule` -- a violation whose rule has no
    registered emitter is silently skipped (not every Tier-C-shaped rule
    has a real emitter yet; `manual`-tier rules are the honest majority,
    per docs/design/check-fix-engine.md's own fixability-registry
    section). Never mutates anything; the resulting list is exactly
    `--fix --json`'s future `fixits` array (T-1481 wires the CLI plumbing
    -- always additive to `frob check`'s existing `violations` array,
    never replacing it)."""
    fixits: list[FixIt] = []
    for violation in violations:
        emitter = TIER_C_EMITTERS.get(violation.rule)
        if emitter is None:
            continue
        fixit = emitter(root, snapshot, violation)
        if fixit is not None:
            fixits.append(fixit)
    return fixits
