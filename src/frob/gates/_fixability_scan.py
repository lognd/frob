"""T-1264: the generated-verified fixability registry field, mirroring
`_rule_id_scan.py`'s own generated-verified shape exactly -- a scanner is
the AUTHORITY, a checked-in literal (`frob.gates.__init__`'s
`_KNOWN_RULE_FIXABILITY`) is the GENERATED artifact, and a drift-lock test
(`tests/test_gates.py::TestRuleFixability`) re-verifies the literal
against a fresh scan every run.

Root cause this closes: a hand-maintained fixability table claiming a
rule is auto-fixable is a claim nothing checks -- this repo has shipped
registry rows read by zero code and presented them as implemented before
(T-0343's "catalogued is not enforced" class). `generated_fixability()`
derives each rule's tier from the ACTUAL fix-engine dispatch tables
(`TIER_A_HANDLERS`/`TIER_B_HANDLERS`/`TIER_C_EMITTERS`) rather than from a
hand-authored claim -- a rule with no handler in any table is `manual` by
construction, and a rule wired into more than one table is a hard scanner
error (`FixabilityConflict`), never a silent last-write-wins.
"""

from __future__ import annotations


# frob:doc docs/design/check-fix-engine.md#fixability-registry-field-generated-verified
# frob:tests tests/test_gates.py::TestRuleFixability.test_conflicting_registration_raises_fixabilityconflict kind="unit"  # noqa: E501
class FixabilityConflict(Exception):
    """A rule id appears in more than one of `TIER_A_HANDLERS`/
    `TIER_B_HANDLERS`/`TIER_C_EMITTERS` -- a scanner-detected wiring bug,
    never a silent last-write-wins pick. Programmer error, not a
    recoverable/user-facing condition, so this is a bare exception rather
    than a typani `Result` member (matching this repo's own convention:
    exceptions for unrecoverable bugs, `Result` for fallible operations a
    caller must handle)."""


# frob:doc docs/design/check-fix-engine.md#fixability-registry-field-generated-verified
# frob:tests \
# tests/test_gates.py::TestRuleFixability.test_checked_in_literal_matches_a_fresh_scan \
# kind="unit"
def generated_fixability(
    known_rule_ids: frozenset[str],
) -> dict[str, str]:
    """Map every id in `known_rule_ids` to exactly one of `"auto"`
    (has a `TIER_A_HANDLERS` entry), `"verified"` (has a `TIER_B_HANDLERS`
    entry), `"assisted"` (has a `TIER_C_EMITTERS` entry), or `"manual"`
    (the honest default -- none of the three). Raises `FixabilityConflict`
    if a rule id is registered in more than one table; that shape is a
    wiring bug, not a valid tier assignment, so it is never silently
    resolved by picking whichever table happened to be checked first."""
    from frob.gates._fix_engine import TIER_A_HANDLERS
    from frob.gates._fix_engine_tier_b import TIER_B_HANDLERS
    from frob.gates._fix_engine_tier_c import TIER_C_EMITTERS

    tier_a = set(TIER_A_HANDLERS) & known_rule_ids
    tier_b = set(TIER_B_HANDLERS) & known_rule_ids
    tier_c = set(TIER_C_EMITTERS) & known_rule_ids

    conflicts = (tier_a & tier_b) | (tier_a & tier_c) | (tier_b & tier_c)
    if conflicts:
        raise FixabilityConflict(
            f"rule id(s) {sorted(conflicts)!r} registered in more than one "
            "of TIER_A_HANDLERS/TIER_B_HANDLERS/TIER_C_EMITTERS"
        )

    result: dict[str, str] = {}
    for rule_id in sorted(known_rule_ids):
        if rule_id in tier_a:
            result[rule_id] = "auto"
        elif rule_id in tier_b:
            result[rule_id] = "verified"
        elif rule_id in tier_c:
            result[rule_id] = "assisted"
        else:
            result[rule_id] = "manual"
    return result


__all__ = [
    "FixabilityConflict",
    "generated_fixability",
]
