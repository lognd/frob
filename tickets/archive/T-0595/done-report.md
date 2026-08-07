## Done report

Closes the remaining (stronger) half of docs/audits/strata.md G1: an
ENDORSE boundary's `predicate` used to discharge THREAT003 by resolving to
a real in-model `Claim.id` alone (T-0498's weaker half) -- nothing joined
the predicate against any real code. Added `observed_call_names`
(`_code_binding.py`): an AST walk over a node's own `code=`-bound files
collecting every distinct call-target name (`Name.id` or `Attribute.attr`).
Threaded optional `binding`/`root` through `check_discharge_completeness`
-> `_check_one_discharge` -> `_check_discharge_mitigation_kind` ->
`_mitigation_is_chokepoint` -> `_matching_boundary_ids`, mirroring the
existing optional-code-tree posture THREAT004/005 already use. A matching
ENDORSE boundary whose `obligations` resolve to a real claim is now ALSO
required to have its `predicate` observed as a call target in the guarded
flow's destination node's own bound code (`_predicate_is_code_bound`);
when it is not, `_code_unbound_boundary_ids` names the specific boundary
id(s) in a dedicated violation message rather than folding into the
generic mismatch text -- the acceptance-tested "fails closed with a
finding naming the unbound boundary" shape. `binding`/`root` default to
None so every existing caller (vet/_containment.py, _sysdoc.py, _audit.py,
_plan.py, _pii.py, _compliance.py) keeps its current design-level-only
behavior unchanged; wiring a real code tree into those production
entrypoints (none currently pass one to check_discharge_completeness) is
out of this ticket's declared scope and is filed separately.

### Changed
```
 src/frob/strata/_code_binding.py       |  55 +++++
 src/frob/strata/_threat.py             | 194 ++++++++++++++++--
 tests/unit/strata/test_code_binding.py |  71 +++++++
 tests/unit/strata/test_threat.py       | 169 ++++++++++++++++
 tickets.md                             | 354 ++++++++++++++++++++++++++++++++-
 5 files changed, 814 insertions(+), 29 deletions(-)
```

### Evidence
- `tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_no_observed_call_site_fails_closed_naming_the_boundary` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_observed_call_site_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_call_site_via_attribute_access_also_discharges` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_call_site_in_a_different_nodes_code_does_not_count` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_threat.py::TestCodeBoundMitigationPredicate::test_absent_binding_keeps_the_old_weaker_half_behavior` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_bare_call_name_is_observed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_attribute_call_name_is_observed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_mention_with_no_call_is_not_observed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_call_in_a_different_nodes_files_is_not_observed` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_code_binding.py::TestObservedCallNames::test_unparseable_file_contributes_no_call_names` (pytest node id, verified passing when recorded)
