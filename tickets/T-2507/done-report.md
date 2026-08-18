## Done report

Changed:
src/frob/vet/_capability_core.py::_dotted_segments
src/frob/vet/_capability_core.py::_needle_matches_resolved

Evidence:
tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_module_prefix_matches_with_and_without_trailing_dot
tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_call_target_matches_with_and_without_trailing_paren
tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_bare_identifier_matches_with_and_without_trailing_paren
tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_family_prefix_still_reaches_sibling_family
tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_module_name_substring
tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_call_target_substring
tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_bare_identifier_substring
tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_module_prefix_does_not_match_unrelated_leading_segment
Full tests/test_vet.py (469 tests) plus tests/unit/test_capability_and_deploy_cycle_regression.py,
tests/unit/test_capability_native.py, tests/unit/gates/test_detector_scope.py re-run clean after the fix
(0 failures) -- covers every per-language binding-resolution caller of _needle_matches_resolved
(python/typescript/rust/c/kotlin), which caught a real regression during development: rust resolved
identities use "::" not "." as separator, fixed by _dotted_segments splitting on both.

Deliverable 1 (segment-boundary comparison replacing substring containment): DONE. Falsifiable check
performed as specified: the registry's own trailing punctuation ("subprocess.", "os.system(", "Popen(")
is now provably redundant -- test_module_prefix_matches_with_and_without_trailing_dot,
test_call_target_matches_with_and_without_trailing_paren, and
test_bare_identifier_matches_with_and_without_trailing_paren each assert the marked and unmarked forms
of the SAME needle produce identical verdicts against the SAME resolved targets from the registry's own
entries (subprocess.run/Popen, os.system). This is not modifying the out-of-scope registry files
(src/frob/vet/_capability_registry/*.py) -- the redundancy is proven at the comparator level via
parametrized needle pairs, since the registry directory itself is outside T-2507's declared scope
(src/frob/vet/_capability_core.py, src/frob/gates/_lexical_selfcheck.py).

The false-positive fix itself is also directly evidenced: needle "net" no longer substring-hits resolved
"netrc"/"network_helper" (the exact example named in the ticket body), and needle "os.system(" no longer
substring-hits an unrelated "myos.system".

Deliverable 2 (widening LEXCHECK001's trigger to the "in" operator): DEFERRED to the epic (T-2501), as
the ticket itself anticipated as an acceptable outcome. Verified T-2504 (path-confinement provenance
lattice on frob.graph.summary) is actively in-progress in its own worktree at time of this ticket --
its provenance notion is the prerequisite this deliverable needs to avoid a naive "in"-operator trigger
that would drown LEXCHECK001 with ordinary membership tests (x in some_set, key in dict). Shipping a
naive trigger now would be worse than shipping nothing, per the ticket's own instruction. No new ticket
filed since T-2501/T-2504 already track this.

Filed: none

Gates: frob check --ticket T-2507 clean on gate:SCOPE (0 errors, after adding tests/test_vet.py to scope
and refreshing the pre-work sweep) and gate:PREWORK; COV002/AFFECT001/DOC007/DRIFT002 on the touched set
resolved via corrected frob:tests directives (single "::" then dotted Class.method form, not pytest's
Class::method collect-only separator -- caught and fixed mid-ticket). All other gate families in the
unscoped run are repo-wide pre-existing findings unrelated to this diff (verified individually against
docs/ files and unrelated modules, per gate:scope-note).

### Changed
```
 src/frob/vet/_capability_core.py | 113 ++++++++++++++++++++++++++++++++++-----
 tests/test_vet.py                |  93 ++++++++++++++++++++++++++++++++
 tickets/T-2507/ticket.md         |  18 ++++++-
 3 files changed, 211 insertions(+), 13 deletions(-)
```

### Evidence
- `tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_module_prefix_matches_with_and_without_trailing_dot` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_call_target_matches_with_and_without_trailing_paren` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_bare_identifier_matches_with_and_without_trailing_paren` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_family_prefix_still_reaches_sibling_family` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_module_name_substring` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_call_target_substring` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_no_false_positive_on_bare_identifier_substring` (pytest node id, verified passing when recorded)
- `tests/test_vet.py::TestNeedleMatchesResolvedTokenBoundary::test_module_prefix_does_not_match_unrelated_leading_segment` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 8 passed (from 8 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
- error-findings: ARCH103@src/frob/release/_cli.py, COV001@src/frob/app/fmt_runner.py, COV001@src/frob/gates/_refs_schema.py, COV003@tickets/T-1205, COV003@tickets/T-1235, COV003@tickets/T-1397, COV003@tickets/T-1526, COV003@tickets/T-1688, COV003@tickets/T-2344, COV003@tickets/T-2348, COV003@tickets/T-2365, DOC001@docs/commands/release.md, DOC002@src/frob/gates/_refs_schema.py, DOC005@docs/modules/cli.md, DOC008@docs/modules/gates.md, DOC011@docs/design/gate-semantics-classification.md, E501@/home/logan/projects/frob/.claude/worktrees/t-2507/src/frob/testing/_collect_kotlin.py, F811@/home/logan/projects/frob/.claude/worktrees/t-2507/tests/unit/test_app_runners_json_guard_t2492.py, PERF002@tests/unit/test_main_entry.py, PERF003@src/frob/gates/_debt_deprecated.py, PERF003@src/frob/vet/_capability_core.py, PERF004@src/frob/app/ticket_runner/_new.py, PERF004@src/frob/scaffold/_skills_sync.py, PERF004@src/frob/testing/_collect_kotlin.py, RENDER001@src/frob/release/_cli.py, SEC110@src/frob/app/verify_runner.py, SEC110@tests/test_release.py, SELFAUDIT001@design, TICK003@tickets.md, TICK004@tickets.md, WIRE002@tests/unit/test_app_runners_batch6.py, WIRE003@docs/modules/cli.md
