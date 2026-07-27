"""T-0756: the NEW-GATE-RULE ACCEPTANCE POLICY -- a ticket that adds a new
gate/check rule id (a fresh `_KNOWN_GATE_RULES` entry in
`src/frob/gates/__init__.py`) must carry, as BOUND acceptance evidence, a
fixture that fails `frob check` before the change and passes after, proving
the rule actually fires through the PRODUCTION invocation -- not merely a
pure-function unit test of its computation. A new rule with only unit-level
evidence and no end-to-end fixture is a close/land-blocking finding
(docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756).

Root cause this closes: T-0630/T-0595/T-0616/T-0710 each shipped a rule that
was built but never actually wired into a production code path an operator
would ever hit -- "invoked-by-nothing". A rule's own unit tests routinely
pass in that state (they call the pure function directly), so evidence
quality alone (T-0755's TEST016 mutation obligation) cannot catch this
class -- TEST016 only asks whether recorded evidence is ADVERSARIAL against
the diff, never whether the diff is REACHABLE from a real invocation at
all. This module is the structural fix for that specific gap: a plain
text-based diff scan (mirroring `frob.tickets._live_tracker`'s "grep-shaped
scan, not a full parse" posture) detects a newly-added rule id, and a
close/land-time preflight (wired into `_done_transition_guard`, same site
`live_tracker_citations` runs from) refuses unless at least one bound
acceptance criterion reads as a before-fails/after-passes fixture proof.

Deliberately narrow in v1 (disclosed, not silently dropped): the check is
FILE-SCOPED to `src/frob/gates/__init__.py`'s `_KNOWN_GATE_RULES` frozenset
literal (the one registry every gate rule id must be listed in, `frob.gates`
module comment: "Every rule id any Violation-producing gate can emit") --
a rule introduced entirely outside that frozenset (e.g. a bare `frob sys
audit` SYS1xx/SYS2xx/REL2xx id that never gets folded into
`_KNOWN_GATE_RULES`) is not detected by this pass alone. T-0756's own
SELFAUDIT001 rule (`frob.gates.sys_gate`) folds exactly those families INTO
`_KNOWN_GATE_RULES` for this reason, closing that gap for the families this
ticket's own scope covers; a rule family added some OTHER way in the future
is a known residual gap, not silently assumed covered."""
# frob:waive INV006 reason="module-docstring exclusivity-vocabulary hit is \
# source-level design-rationale prose describing already-implemented entry-point \
# behavior, verifiable by reading the code it annotates and the T-0756 close/land \
# wiring in frob.tickets.__init__'s _done_transition_guard -- not a separate \
# cross-module contract needing its own tracked invariant, same calibration posture as \
# frob.tickets._live_tracker's own T-0854 INV006 waiver"

from __future__ import annotations

import re
from pathlib import Path

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._models import Ticket

_log = get_logger(__name__)

#: The one file every gate rule id must be registered in
#: (`src/frob/gates/__init__.py`'s `_KNOWN_GATE_RULES` frozenset) -- the
#: scan target this module's diff-aware detection is scoped to (module
#: docstring's v1 GAP STATEMENT).
_GATES_REL_PATH = "src/frob/gates/__init__.py"

#: Matches the `_KNOWN_GATE_RULES = frozenset({ ... })` literal block,
#: non-greedily up to its own closing `}` -- the block contains only
#: quoted rule-id string literals and `#`-prefixed comment lines, no
#: nested `{`/`}`, so a non-greedy `.*?` up to the first `}` after the
#: opening one is exact, not a heuristic approximation.
_KNOWN_RULES_BLOCK_RE = re.compile(
    r"_KNOWN_GATE_RULES\s*=\s*frozenset\(\s*\{(.*?)\}\s*\)", re.DOTALL
)

#: A double-quoted string literal -- every non-comment line inside the
#: `_KNOWN_GATE_RULES` block is exactly one of these (module docstring).
_QUOTED_RE = re.compile(r'"([^"]+)"')

#: A bound acceptance criterion's text must read as a before/after fixture
#: proof to discharge the T-0756 obligation: both a FAIL marker and a PASS
#: marker present (case-insensitive substring match), matching the ticket
#: prose convention this repo's own tickets already use ("fixture that
#: FAILS frob check before and PASSES after"). Intentionally loose (any
#: phrasing containing both words) rather than a rigid GIVEN/WHEN/THEN
#: template match -- the obligation is about the PROOF existing and being
#: bound to evidence, not about matching one exact sentence shape.
_FAIL_MARKER = "fail"
_PASS_MARKER = "pass"


def _extract_known_rules(text: str) -> frozenset[str] | None:
    """Every rule id quoted inside `text`'s `_KNOWN_GATE_RULES` frozenset
    literal, or `None` if the literal itself cannot be found (a malformed
    or renamed file -- distinct from "found, but the set happens to
    resolve empty", which cannot actually happen for a real gates module
    but is handled the same permissive way regardless)."""
    match = _KNOWN_RULES_BLOCK_RE.search(text)
    if match is None:
        return None
    lines = (
        line for line in match.group(1).splitlines() if not line.strip().startswith("#")
    )
    return frozenset(_QUOTED_RE.findall("\n".join(lines)))


def _read_gates_file_at_revision(root: Path, revision: str) -> str | None:
    """`git show <revision>:src/frob/gates/__init__.py` under `root`, or
    `None` on any git failure (not a git work tree, `revision` unresolvable,
    the path did not exist at that revision -- all collapsed to the same
    "cannot read" outcome; `new_gate_rule_ids` treats that as unknown, not
    as 'the file was empty there', so a brand-new gates module is not
    silently misread as having zero pre-existing rules by accident)."""
    spawned = run_argv(
        ("git", "-C", str(root), "show", f"{revision}:{_GATES_REL_PATH}"), timeout_s=15
    )
    if spawned.is_err:
        _log.warning(
            "new-gate-rule-acceptance: git show %s:%s failed to spawn, "
            "skipping new-rule detection",
            revision,
            _GATES_REL_PATH,
        )
        return None
    result = spawned.danger_ok
    if result.returncode != 0:
        _log.debug(
            "new-gate-rule-acceptance: %s did not exist at %s (exit %d) -- "
            "treating as a brand-new file with no prior rules",
            _GATES_REL_PATH,
            revision,
            result.returncode,
        )
        return ""
    return result.stdout


# frob:doc docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_detects_freshly_added_rule_id  # noqa: E501
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_no_new_rules_is_empty  # noqa: E501
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_unresolvable_base_ref_degrades_to_none  # noqa: E501
def new_gate_rule_ids(root: Path, base_ref: str = "main") -> tuple[str, ...] | None:
    """Rule ids present in the CURRENT working tree's `_KNOWN_GATE_RULES`
    (`src/frob/gates/__init__.py` under `root`) that were NOT present in
    that same frozenset at `base_ref`'s tip -- the T-0756 new-rule
    detector.

    `None` (never an empty tuple) means "cannot tell" -- either revision's
    frozenset literal could not be read/parsed at all (missing file,
    unresolvable `base_ref`, a malformed gates module). Callers must treat
    `None` as fail-OPEN (skip the acceptance obligation entirely) rather
    than fail-closed: unlike `frob.tickets._live_tracker`'s citation scan
    (which only ever narrows an already-nonempty finding set), this
    function's result gates whether EVERY ticket close in the repo runs an
    extra obligation at all -- fail-closed here would mean a transient git
    hiccup silently blocks unrelated ticket closes repo-wide, which is a
    worse failure mode than occasionally missing a genuinely new rule id
    (T-0756's own Done report discloses this as a deliberate v1
    trade-off, not an oversight)."""
    gates_path = root / _GATES_REL_PATH
    if not gates_path.is_file():
        return ()
    try:
        current_text = gates_path.read_text(encoding="utf-8")
    except OSError:
        _log.warning(
            "new-gate-rule-acceptance: could not read %s, skipping new-rule detection",
            gates_path,
        )
        return None
    current = _extract_known_rules(current_text)
    if current is None:
        _log.warning(
            "new-gate-rule-acceptance: _KNOWN_GATE_RULES literal not found "
            "in %s, skipping new-rule detection",
            gates_path,
        )
        return None
    base_text = _read_gates_file_at_revision(root, base_ref)
    if base_text is None:
        return None
    base = _extract_known_rules(base_text)
    if base is None:
        _log.warning(
            "new-gate-rule-acceptance: _KNOWN_GATE_RULES literal not found "
            "at %s:%s, skipping new-rule detection",
            base_ref,
            _GATES_REL_PATH,
        )
        return None
    return tuple(sorted(current - base))


def _is_fixture_acceptance(criterion) -> bool:  # noqa: ANN001
    """Whether one `AcceptanceCriterion` reads as a bound before-fails/
    after-passes fixture proof: it must carry resolving evidence (`bound`,
    not just declared) AND its own text must mention both a FAIL and a PASS
    marker -- the textual shape a genuine "fixture failed before, passes
    after, through the production invocation" claim takes, distinct from an
    ordinary feature-acceptance criterion that never claims a before/after
    contrast at all."""
    text = criterion.text.lower()
    return bool(criterion.evidence) and _FAIL_MARKER in text and _PASS_MARKER in text


# frob:doc docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules.test_flags_when_no_fixture_criterion_bound  # noqa: E501
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules.test_clear_when_a_bound_fixture_criterion_exists  # noqa: E501
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestMissingAcceptanceForNewRules.test_empty_new_rule_ids_is_always_clear  # noqa: E501
def missing_acceptance_for_new_rules(
    ticket: Ticket, new_rule_ids: tuple[str, ...]
) -> tuple[str, ...]:
    """`new_rule_ids` unchanged (the close/land-blocking finding) unless
    `ticket` carries at least one bound before-fails/after-passes fixture
    acceptance criterion (`_is_fixture_acceptance`) -- `()` (clear) either
    when `new_rule_ids` is empty (nothing to prove) or such a criterion
    already exists. v1 (disclosed): requires ONE qualifying criterion
    covering the ticket as a whole, not a 1:1 criterion-per-rule-id
    mapping -- a ticket introducing several rule ids in one change proves
    them with one fixture-shaped criterion, not N."""
    if not new_rule_ids:
        return ()
    if any(_is_fixture_acceptance(c) for c in ticket.acceptance):
        return ()
    return new_rule_ids


__all__ = ["missing_acceptance_for_new_rules", "new_gate_rule_ids"]
