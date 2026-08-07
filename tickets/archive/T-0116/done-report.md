## Done report

Changed:
- src/frob/strata/_compliance.py (new): `std.compliance` catalog +
  COMPLIANCE001 (catalog completeness) / COMPLIANCE002 (discharge) /
  COMPLIANCE003 (privacy-policy reverse audit).
  - `RegulationEntry`, `OutOfScopeRegulation` (owner+review mandatory,
    unlike `_threat.py::OutOfScopeEntry`), `COMPLIANCE_CATALOG` (6
    regulations, real citations: COPPA/FTC, GDPR art. 5/6/17, HIPAA/HHS
    BAA guidance), `REGULATION_VIEWS` (all-regulations/us-coppa/
    eu-gdpr/us-hipaa).
  - `check_regulation_catalog_completeness` (COMPLIANCE001, mirrors
    `_threat.py::check_catalog_completeness`).
  - `check_regulation_discharge` (COMPLIANCE002): `_check_coppa` (NoFlow
    closure: any Boundary on the child-tagged collection flow discharges,
    reusing `_facts.py::FactBase.reachable(through_barriers=False)`
    exactly as every other unendorsed-flow refusal); `_check_erasure`
    (revocation-edge presence, the same `attrs=("revocation",)`
    convention `_secrets.py::_secret_flows` established for T-0082);
    `_check_retention` (age-collapse via `_facts.py::worst_age` against
    a declared `retention=<bound>` attr, T-0065 machinery); `_check_
    lawful_basis` (`basis:<...>` attr presence on eu-resident
    collection); `_check_baa` (`covered-party` attr on the dst of a
    `subject:health`-tagged flow); `_check_minimization` (a `field:
    <name>`-tagged collection flow whose dst has no outbound flow).
    Every obligation auto-instantiates (no author-written claim
    required, mirroring `_secrets.py::elaborate_secret`'s auto-generated
    `SetEquality`) unless overridden by a `Claim` named `compliance:
    <reg-id>:<target-id>`, which -- if `assumed` -- MUST carry
    `owner`+`review` or is itself a violation (`_claim_override`).
  - `PrivacyPolicy` + `check_privacy_policy` (COMPLIANCE003): the
    verifiable core of the reverse audit -- every modeled collection
    flow's `field:<name>` attr must appear in `policy.collected_fields`;
    binding to the actual prose document is DOC002/T-0115's territory,
    not reimplemented here (module docstring notes the cut).
  - `evaluate_compliance`: the gate-agnostic entrypoint (COMPLIANCE001 +
    002 + optional 003), mirroring `_threat.py::evaluate_threats`.
- src/frob/strata/__init__.py: exports the 11 new public symbols.
- tests/unit/strata/test_compliance.py (new): 23 unit tests, one class
  per catalog check / regulation.

Label vocabulary extension (minimal, per the charter's "opaque-string
vocabulary on existing attrs tuples" convention, module docstring):
`Flow.attrs` gains `subject:child`, `subject:unknown-age`, `subject:
health`, `basis:<consent|contract|legitimate-interest>`, `field:<name>`;
`Node.attrs` gains `jurisdiction:eu-resident`/`jurisdiction:ca-resident`,
`retention=<value><unit>`, `covered-party`. No kernel primitive added
(charter law 1) -- `_models.py` untouched.

Acceptance criteria as tests (all REFUTE/pass exactly as specified):
- `TestCoppa::test_ungated_child_collection_flow_refutes_coppa`: a
  child-tagged collection flow with no consent boundary -> COPPA
  violation (COMPLIANCE002/COPPA).
- `TestGdprErasure::test_eu_resident_store_with_no_deletion_path_refutes_erasure`:
  eu-resident Pii with no deletion path -> GDPR-ERASURE violation.
- `TestPrivacyPolicy::test_field_the_policy_omits_refutes`: a flow
  collecting a field the privacy policy omits -> COMPLIANCE003
  violation.

Numbers: 23 new unit tests, all green. Full suite `tests/unit/strata
tests/system`: 655 passed (was 632 before this ticket's tests). `uv run
frob check --ticket T-0116`: gates PASS, 0 unwaived violations
attributable to `_compliance.py`/`test_compliance.py` (COV002 "covered
by open ticket scope" entries are expected/informational, not
failures); fixed one PERF003 (nested node/flow scan in `_check_erasure`,
rewritten as a single flow pass building a `revoked_nodes` set) and one
COV001 (missing `frob:doc` on `REGULATION_VIEWS`) found during
self-review, plus corrected all `frob:doc` anchors to the real
GitHub-style slug (`#compliance-regulatory-obligations-std-compliance`,
verified against `slugify()` in `src/frob/graph/dsl.py`) after DOC002
first caught the wrong slug. `uv run frob check` (repo-wide, no
--ticket): all tool-summary rows `pass`, ruff-check/ruff-format/ty
clean. A/B honest: no gate that was clean before this ticket regressed.

Filed: none (no out-of-scope work found; T-0134's surface-grammar
deferral and T-0115's DOC002 prose-binding note are inherited citations
of already-filed tickets, not new filings).

Gates: `frob check --ticket T-0116` clean (all PERF/COV items on
`_compliance.py` resolved or are expected COV002 in-scope notices; no
`frob:waive` needed on new code).

Not closed per instructions -- evidence + Done report recorded only.

## Review response (reviewer REJECT, one correctness gap)

Reviewer finding: `_check_coppa` collected `{b.flow_id for b in model.
boundaries}` with no `direction` filter, so ANY boundary on the
collection flow -- including an unrelated DECLASSIFY -- silently
discharged COPPA (the T-0113 any-boundary lesson, missed here even
though `_check_baa`'s attribute-based check got the equivalent
discrimination right).

Fix: `_check_coppa` now filters to `b.direction is BoundaryDirection.
ENDORSE` before building `boundary_flows` (src/frob/strata/
_compliance.py, `_check_coppa`). Docstring updated to name the T-0113
lesson explicitly and to flag, as an open phase-A/B question, whether
`predicate` text (not just direction) should additionally be checked
against a consent/age-gate vocabulary -- deferred the same way
`_threat.py`'s capability/sink-taxonomy predicate semantics are
deferred past phase A (noted, not silently dropped).

Regression test added: `TestCoppa::test_declassify_only_boundary_does_
not_discharge_coppa` -- a `subject:child` collection flow with only a
DECLASSIFY boundary attached still produces exactly one COPPA
violation (was 0 before the fix; verified failing against the
pre-fix code, then green after).

Sweep of the other five regulations for the same class of gap
(boundary-presence-without-direction): NONE found. Only COPPA's
discharge check inspects `model.boundaries` at all --
`_check_erasure`/`_check_retention`/`_check_lawful_basis`/`_check_baa`/
`_check_minimization` all key off `Flow.attrs`/`Node.attrs`/reachable-
age (`revocation` attr, `retention=` attr, `basis:` attr,
`covered-party` attr, outbound-flow presence respectively) -- none of
them consult `Boundary.direction` or `Boundary` presence at all, so
none had a direction-blind boundary check to get wrong. COPPA was the
only regulation using the boundary-blocks-closure pattern, and it is
now the only one that needed (and has) the ENDORSE-direction filter.

Re-verification: 24 unit tests in `tests/unit/strata/test_compliance.py`
green (23 + the new regression test); full `tests/unit/strata tests/
system` suite: 656 passed (was 655 before this fix, +1 for the new
test); `ruff check .` / `ruff format --check .` / `uv run ty check`:
all clean; `frob check --ticket T-0116` (after `frob ticket sweep
T-0116` to refresh the pre-work sweep): gates pass, same 84
violations/38 waived baseline as before the fix (no new unwaived
findings; `_check_coppa` grew to 55 lines, still under this session's
<60-line rule and still only a frob-arch soft `long-function` warning,
not a gate failure). Evidence updated: 24 test ids recorded (was 23).

Still not closed, not committed, per instructions.
