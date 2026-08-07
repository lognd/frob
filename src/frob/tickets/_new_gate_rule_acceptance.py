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
scoped to `_KNOWN_GATE_RULES`, the one frozenset literal every gate rule id
must be listed in (`frob.gates` module comment: "Every rule id any
Violation-producing gate can emit") -- a rule introduced entirely outside
that frozenset (e.g. a bare `frob sys audit` SYS1xx/SYS2xx/REL2xx id that
never gets folded into `_KNOWN_GATE_RULES`) is not detected by this pass
alone. T-0756's own SELFAUDIT001 rule (`frob.gates.sys_gate`) folds exactly
those families INTO `_KNOWN_GATE_RULES` for this reason, closing that gap
for the families this ticket's own scope covers; a rule family added some
OTHER way in the future is a known residual gap, not silently assumed
covered.

T-1155: the literal's HOME FILE within `src/frob/gates/` used to be
hard-coded (`gates/__init__.py`) and went silently stale the moment T-1139
moved it to `gates/_waive.py` -- the preflight kept running, found nothing
at the stale path, and warned-and-skipped forever after, a detection check
silently disabling itself. Resolution is now dynamic across every direct
`*.py` child of `src/frob/gates/` (`_locate_known_rules_in_tree`), and a
registry that cannot be found in exactly one candidate raises
`GateRuleRegistryUnresolvable` rather than degrading to a silent skip."""

from __future__ import annotations

import re
from pathlib import Path

from frob.gitio import run_argv
from frob.logging import get_logger
from frob.tickets._models import Ticket

_log = get_logger(__name__)

#: The package every gate rule id must be registered somewhere inside
#: (`_KNOWN_GATE_RULES`'s frozenset literal) -- T-1155: this used to be a
#: single hard-coded file path (`src/frob/gates/__init__.py`) and went
#: silently stale the moment T-1139 moved the literal to `gates/_waive.py`
#: (the preflight warned-and-skipped forever after, a detection check
#: silently disabling itself). Resolution is now DYNAMIC: every direct
#: `*.py` child of this directory is a candidate, and whichever one
#: actually carries the literal (`_locate_known_rules_in_tree`) is used,
#: so a future move within the package needs no matching change here.
_GATES_DIR_REL = "src/frob/gates"

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


# frob:doc docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756
class GateRuleRegistryUnresolvable(RuntimeError):
    """Raised when `_KNOWN_GATE_RULES` cannot be located in exactly one
    `*.py` file directly under `src/frob/gates/` in the CURRENT working
    tree -- zero candidates (the registry vanished from the whole
    package) or more than one (an ambiguous duplicate literal). T-1155:
    this is a structural corruption of the gate-rule registry every rule
    id must be enumerable through, never a routine "cannot tell, skip"
    condition the way an unresolvable `base_ref` is -- callers must let
    it propagate as a loud failure, not catch it and silently disable
    new-rule detection the way the pre-T-1155 hard-coded-path version
    did (observed going dark for real after the T-1139 gates split,
    T-1155's own Description)."""


def _gates_candidate_files(root: Path) -> tuple[Path, ...]:
    """Every direct `*.py` child of `src/frob/gates/` under `root`,
    sorted for a deterministic scan order -- the full candidate set
    `_locate_known_rules_in_tree` searches for the `_KNOWN_GATE_RULES`
    literal; empty if the package directory itself does not exist
    (a non-frob-gates checkout, distinct from the literal missing from an
    existing package -- see `new_gate_rule_ids`)."""
    gates_dir = root / _GATES_DIR_REL
    if not gates_dir.is_dir():
        return ()
    return tuple(sorted(p for p in gates_dir.glob("*.py") if p.is_file()))


def _locate_known_rules_in_tree(root: Path) -> tuple[Path, frozenset[str]] | None:
    """The single `src/frob/gates/*.py` file (relative to `root`) whose
    text contains the `_KNOWN_GATE_RULES` literal, paired with the rule
    ids it resolves to -- `None` if zero or more than one candidate
    file matches (either is a structural resolution failure; see
    `GateRuleRegistryUnresolvable`'s docstring for why both collapse to
    the same "cannot resolve" outcome rather than picking one
    arbitrarily)."""
    matches: list[tuple[Path, frozenset[str]]] = []
    for candidate in _gates_candidate_files(root):
        try:
            text = candidate.read_text(encoding="utf-8")
        except OSError:
            continue
        try:
            rules = _extract_known_rules(text)
        except (KeyError, TypeError):
            # A "cannot resolve" outcome (this function's own docstring)
            # from one candidate's surprising text shape must not abort
            # the whole scan over every OTHER candidate (EXHAUST001/
            # EXHAUST002, T-1371) -- treat it the same as "no match in
            # this file".
            continue
        except Exception:
            continue
        if rules is not None:
            matches.append((candidate, rules))
    if len(matches) != 1:
        return None
    return matches[0]


def _known_rules_at_revision(root: Path, revision: str) -> frozenset[str] | None:
    """The `_KNOWN_GATE_RULES` frozenset as it read at `revision`, found
    by trying `git show <revision>:<candidate>` for EVERY current-tree
    `src/frob/gates/*.py` candidate name, not just the one file it
    currently lives in -- this is what lets a rename/move (T-1139:
    `__init__.py` -> `_waive.py`) resolve correctly across the boundary
    revision instead of reading "file did not exist yet" and treating
    every existing rule as spuriously new. `None` if zero or more than
    one candidate resolves --
    matches the pre-T-1155 single-file behavior exactly: an unresolvable
    `revision`, a path that did not exist there yet, and an ambiguous
    multi-file match all degrade to the same fail-open "cannot tell, skip
    the obligation" outcome (`new_gate_rule_ids`'s docstring), never a
    silently-assumed-empty registry."""
    matches: list[frozenset[str]] = []
    for candidate in _gates_candidate_files(root):
        rel = candidate.relative_to(root).as_posix()
        spawned = run_argv(
            ("git", "-C", str(root), "show", f"{revision}:{rel}"), timeout_s=15
        )
        if spawned.is_err:
            continue
        result = spawned.danger_ok
        if result.returncode != 0:
            continue
        rules = _extract_known_rules(result.stdout)
        if rules is not None:
            matches.append(rules)
    if len(matches) != 1:
        return None
    return matches[0]


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


# frob:doc docs/modules/gates.md#new-gate-rule-acceptance-policy-t-0756
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_detects_freshly_added_rule_id  # noqa: E501
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_no_new_rules_is_empty  # noqa: E501
# frob:tests tests/test_tickets_new_gate_rule_acceptance.py::TestNewGateRuleIds.test_unresolvable_base_ref_degrades_to_none  # noqa: E501
# frob:tests tests/test_gates.py::TestNewGateRuleDynamicResolution.test_resolves_when_literal_lives_in_a_different_file  # noqa: E501
# frob:tests tests/test_gates.py::TestNewGateRuleDynamicResolution.test_raises_when_literal_missing_from_every_candidate  # noqa: E501
def new_gate_rule_ids(root: Path, base_ref: str = "main") -> tuple[str, ...] | None:
    """Rule ids present in the CURRENT working tree's `_KNOWN_GATE_RULES`
    (dynamically located among `src/frob/gates/*.py` under `root`,
    T-1155 -- see `_locate_known_rules_in_tree`) that were NOT present in
    that same frozenset at `base_ref`'s tip -- the T-0756 new-rule
    detector.

    `None` (never an empty tuple) means "cannot tell, from `base_ref`'s
    side only" -- `base_ref` itself is unresolvable, or its own revision
    of the registry is ambiguous across candidates. Callers must treat
    `None` as fail-OPEN (skip the acceptance obligation entirely) rather
    than fail-closed: unlike `frob.tickets._live_tracker`'s citation scan
    (which only ever narrows an already-nonempty finding set), this
    function's result gates whether EVERY ticket close in the repo runs an
    extra obligation at all -- fail-closed here would mean a transient git
    hiccup silently blocks unrelated ticket closes repo-wide, which is a
    worse failure mode than occasionally missing a genuinely new rule id
    (T-0756's own Done report discloses this as a deliberate v1
    trade-off, not an oversight).

    T-1155: this is now the ONLY "cannot tell" outcome left -- a registry
    that cannot be found anywhere in the CURRENT tree is a different,
    structural failure mode (the whole package lost the literal, not a
    git-side ambiguity) and raises `GateRuleRegistryUnresolvable` instead
    of returning `None`, so the caller sees a loud failure rather than a
    silently-skipped check (the exact incident this ticket closes -- see
    the module docstring's T-1153 observation)."""
    located = _locate_known_rules_in_tree(root)
    if located is None:
        if not _gates_candidate_files(root):
            # No src/frob/gates/ package here at all -- not a frob-gates
            # checkout, nothing to detect (distinct from the package
            # existing but having lost the literal, which raises below).
            return ()
        _log.error(
            "new-gate-rule-acceptance: _KNOWN_GATE_RULES literal could not "
            "be resolved to exactly one file under %s/ -- registry is "
            "missing or ambiguous, refusing to silently skip detection",
            _GATES_DIR_REL,
        )
        raise GateRuleRegistryUnresolvable(
            f"_KNOWN_GATE_RULES not found in exactly one *.py file under "
            f"{root / _GATES_DIR_REL} -- fix the registry before closing "
            f"any ticket"
        )
    _, current = located
    base = _known_rules_at_revision(root, base_ref)
    if base is None:
        _log.warning(
            "new-gate-rule-acceptance: _KNOWN_GATE_RULES ambiguous across "
            "candidates at %s, skipping new-rule detection",
            base_ref,
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


__all__ = [
    "GateRuleRegistryUnresolvable",
    "missing_acceptance_for_new_rules",
    "new_gate_rule_ids",
]
