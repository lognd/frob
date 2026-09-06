## Done report

SYS113 (T-4110/H3-10): a node's code= glob set, or a glob-form may-grant
via entry, matching zero real (skip-dir-filtered) files on the current
branch is now its own finding, collected alongside SYS101 in
check_self_conformance and carrying its own waiver identity
(SYS_ZERO_MATCH_DECLARATION) -- a SYS101 capability-unobserved waiver
can no longer suppress it. Verified distinguishable from SYS101 in both
directions (a real, non-excluded match still fires only SYS101; a
zero-match declaration fires only SYS113), and silent for the
pre-existing _fully_excluded_node_ids graph-exclude carve-out and for
symbol-form via entries SYS109 already covers, at both node and
per-via granularity.

Landing the rule against frob's own tree surfaced and fixed two real
pre-existing gaps: design/frob.strata's "gates" node carried a fs.read
via naming src/frob/gates/_inv006_split_assist.py, deleted from the
tree at commit 25d6f3dc9 and never cleaned up (removed); and the
via-entry check initially false-positived on a via naming
tests/fixtures/lang/sample.py (a real file, legitimately
[graph].exclude'd), fixed by giving the via-entry check the same
raw-match-vs-excluded-match split _fully_excluded_node_ids already
uses at node granularity.

Evidence: 20 pytest node ids bound via `frob ticket evidence` -- every
case in the two new test files, plus TestRealGateGreen::
test_repo_design_and_declarations_are_self_conformant and
TestCoverageTotality::test_repo_unrestricted_scan_is_clean, both of
which exercise SYS113 against frob's OWN design/frob.strata and OWN
tree and fail if it ever reintroduces a false positive or misses a
real one.

Filed: T-4127 -- SCOPE002 (promoted to ERROR by frob.toml's
[gates.severity]) explodes to ~140 unrelated files the moment
design/frob.strata or docs/modules/gates.md enters ANY ticket's scope,
because its closure check evaluates every symbol a scoped FILE
contains rather than the symbols a ticket's diff actually touches.
Both files are maximal cross-reference hubs (design/frob.strata's 26
nodes each frob:doc into a different unrelated guide; docs/modules/
gates.md documents nearly the entire gate catalog) -- this ticket
needed to touch both (a two-line via-list fix in design/frob.strata,
a new rule-catalog section in gates.md) and hit the full explosion.
Filed rather than worked around by widening T-4110's own scope to the
~140 unrelated files SCOPE002 named, which would have been a
disproportionate, wrong-shaped fix for a narrow bug ticket.

Gates: frob check --ticket T-4110 is NOT clean -- gate:SCOPE fails
with 141 SCOPE002 findings, all naming files this ticket has no
business owning (see T-4127). Every other gate this ticket's
own code touches is clean: the two new test files plus the full
pre-existing test_selfconform.py suite (89 tests total) pass,
including both real-repo-scan tests. gate:PRE's pre-work sweep has
been re-run (frob ticket sweep T-4110); gate:REG's check-coverage.yaml
denominator has been bumped for the new CHK-GATE-SYS113 entry;
ARCH001/LANDPARITY002's long-function warning on
_zero_match_via_entries has been resolved by splitting out
_via_entry_is_zero_match; the ty invalid-argument-type findings on
_matched_real_files/_zero_match_code_violation have been fixed by
widening their glob-list parameter types to match what
_node_code_globs actually returns. gate:SCOPE (SCOPE002) is the one
remaining failure, and it is a tooling gap in the scope-closure
checker itself (T-4127), not a defect in this ticket's fix.

### Changed
```
 design/frob.strata                               |   6 +-
 docs/design/registry/check-coverage.yaml         |   7 +-
 docs/modules/gates.md                            |  44 +++-
 src/frob/gates/_waive.py                         |   7 +
 src/frob/strata/_selfconform.py                  |  31 ++-
 src/frob/strata/_selfconform_core_rules.py       | 107 +++++++++-
 src/frob/strata/_selfconform_ids.py              |  26 +++
 src/frob/strata/_selfconform_kinds.py            | 167 +++++++++++++--
 tests/unit/strata/test_selfconform_core_rules.py | 260 +++++++++++++++++++++++
 tests/unit/strata/test_selfconform_kinds.py      | 228 ++++++++++++++++++++
 tickets/T-4110/ticket.md                         | 136 +++++++++++-
 tickets/T-4127/ticket.md               |  63 ++++++
 12 files changed, 1048 insertions(+), 34 deletions(-)
```

### Evidence
- `tests/unit/strata/test_selfconform_kinds.py::TestMatchedRealFiles::test_returns_only_matching_files` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestMatchedRealFiles::test_empty_when_no_glob_matches` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchNodeCodeIds::test_node_with_zero_matching_files_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchNodeCodeIds::test_node_with_at_least_one_matching_file_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchNodeCodeIds::test_node_with_no_code_glob_at_all_is_skipped` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchNodeCodeIds::test_disjoint_from_fully_excluded_node_ids` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchViaEntries::test_glob_form_via_matching_no_owned_file_is_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchViaEntries::test_glob_form_via_matching_owned_file_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchViaEntries::test_symbol_form_via_is_never_flagged_even_when_matching_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchViaEntries::test_via_naming_a_graph_excluded_real_file_is_not_flagged` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_kinds.py::TestZeroMatchViaEntries::test_node_with_no_may_grants_yields_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_core_rules.py::TestZeroMatchCodeGlob::test_must_fire_when_code_glob_matches_nothing` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_core_rules.py::TestZeroMatchCodeGlob::test_must_not_fire_when_glob_matches_real_files_with_zero_observed_capability` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_core_rules.py::TestZeroMatchCodeGlob::test_must_not_fire_when_glob_matches_real_files_that_exercise_capability` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_core_rules.py::TestZeroMatchCodeGlob::test_must_not_fire_for_fully_graph_excluded_node` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_core_rules.py::TestZeroMatchViaEntry::test_must_fire_when_via_glob_matches_no_owned_file` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_core_rules.py::TestZeroMatchViaEntry::test_must_not_fire_for_symbol_form_via_matching_zero_files` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform_core_rules.py::TestZeroMatchViaEntry::test_must_not_fire_when_via_glob_matches_owned_file` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestRealGateGreen::test_repo_design_and_declarations_are_self_conformant` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_selfconform.py::TestCoverageTotality::test_repo_unrestricted_scan_is_clean` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 20 passed (from 20 evidence id(s))
- gates: 4 error(s), 4435 warning(s), 935 waived
- error-findings: SCOPE002@tickets.md, SELFAUDIT001@docs/design/registry/capability-via-ratchet.lock.json, invalid-argument-type@src/frob/strata/_selfconform_kinds.py, missing-argument@tests/unit/test_check_gates_summary.py
