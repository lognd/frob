## Done report

Fixed G1 (docs/audits/strata.md): `_mitigation_is_chokepoint`'s
`_matching_boundary_ids` treated an ENDORSE boundary's bare `predicate`
string (equal to the catalog's required mitigation name) as sufficient
proof of a real mitigation, with zero binding to code or any other
in-model fact -- an attacker (or careless author) could type any
plausible predicate and THREAT003 would PROVE the discharge.

Counterexample confirmed first (ad-hoc script, before any code change):
an ENDORSE boundary with `predicate="output_encoding"` and NO
`obligations` discharged CWE-79 cleanly (`check_discharge_completeness`
returned zero violations).

Fix: `_matching_boundary_ids` now also requires the boundary's
`obligations` (evidence refs, `_models.py`: "evidence refs discharged in
tier 3") to be non-empty AND resolve to a real `Claim.id` present in the
model (`_obligations_resolve`, new). A matching-predicate boundary with
no evidence ref, or a dangling one, no longer counts as the required
mitigation kind -- `_check_one_discharge` rejects the claim instead of
proving it. This does not yet bind the predicate to an OBSERVED sanitizer
site in code (the full SYS-family fix direction the audit finding also
names) -- that remains a real gap, noted below as a follow-up ticket,
since it is a substantially larger static-analysis feature (locating and
verifying a sanitizer call site per predicate name across languages) than
this ticket's budget covers. What IS closed: an ENDORSE boundary can no
longer discharge a weakness purely on the strength of a self-declared,
unverified string -- it must point at a real, independently-checkable
claim in the same model.

Updated existing fixtures that relied on the old vacuous behavior
(`tests/test_vet_containment.py::_model_with_discharged_sql`,
`test_threat.py::test_endorse_boundary_with_matching_predicate_discharges`)
to carry a resolving `obligations` ref, and added two new counterexample
tests proving the closed gap (no evidence ref; dangling evidence ref).

Not Filed a never-materialized draft (T-0595 is the real replacement) (never refiled): full SYS-family rule binding an ENDORSE boundary predicate
to an OBSERVED sanitizer call site in `code=`-bound files (the stronger
half of G1's fix direction, out of this ticket's scope/budget).

### Changed
(no changed files detected)

### Evidence
- `tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_endorse_boundary_with_no_evidence_ref_does_not_discharge_g1` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_endorse_boundary_with_dangling_obligation_does_not_discharge_g1` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestMitigationKindChokepoint::test_endorse_boundary_with_matching_predicate_discharges` (pytest node id, verified passing when recorded)
- `tests/test_vet_containment.py::TestBuildContainmentReport::test_contained_finding_when_obligation_discharged` (pytest node id, verified passing when recorded)
