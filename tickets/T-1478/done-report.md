## Done report

Changed:
strata-core/src/parse/grammar_node.rs (may "ATOM" of "GLOB"[, "GLOB"...] trailer)
src/frob/strata/_ast.py::MayGrantDecl.of
src/frob/strata/_models.py::MayGrant.of
src/frob/strata/_elaborate.py::_elaborate_node (threads of= through)
src/frob/strata/_effects.py::ObservedEffect.argument, _first_string_literal,
  _of_matches_effect, _declared_kinds_for_effect (of-aware), _needle_matches
tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping (4 tests)
docs/strata/surface.md (documents the of trailer, replaces the "still unbuilt"
  section, drops the frob:until T-1478 marker)
design/frob.strata (testsuite node's env via-list gains the new test fixture
  file, self-conformance precedent matching T-1589's comment for net)

Evidence:
tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping::test_argument_matching_of_glob_is_clean
tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping::test_argument_outside_of_glob_is_a_violation
tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping::test_of_less_grant_still_covers_every_argument
tests/unit/strata/test_effects.py::TestArgumentLevelMayScoping::test_via_and_of_compose_as_independent_axes

Filed: none

Gates: frob check --ticket T-1478 clean except pre-existing/unrelated findings
already present before this ticket's own work (gate:ARCH 3 errors in
_doable.py/_query.py, gate:COV _doable.py COV001 + COV006/COV007 noise,
gate:SCOPE the pre-existing tickets/T-1478/ticket.md self-file SCOPE001
tracked by T-1827) -- confirmed via full unscoped `uv run frob check` (8
errors total, same set). Full strata unit suite green: `uv run pytest
tests/unit/strata/ -q` (1387 collected, 0 failed, deselecting the two
test_export_golden.py goldens that are independently red on main with zero
worktree changes -- confirmed by running the identical pytest invocation in
the root checkout /home/logan/projects/frob at main tip, same 2 failures).

### Changed
```
 design/frob.strata                    |   7 ++-
 docs/strata/surface.md                |  28 ++++++---
 src/frob/strata/_ast.py               |  19 +++++-
 src/frob/strata/_effects.py           | 113 ++++++++++++++++++++++++++++------
 src/frob/strata/_elaborate.py         |   2 +-
 src/frob/strata/_models.py            |  17 ++++-
 strata-core/src/parse/grammar_node.rs |  31 +++++++++-
 tests/unit/strata/test_effects.py     |  86 ++++++++++++++++++++++++++
 tickets/T-1478/ticket.md              |  99 ++++++++++++++++++++++++++++-
 9 files changed, 367 insertions(+), 35 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: 4 error(s), 1003 warning(s), 740 waived
- error-findings: ARCH001@src/frob/app/ticket_runner/_query.py, ARCH001@src/frob/tickets/_doable.py, ARCH103@src/frob/app/ticket_runner/_query.py, COV001@src/frob/tickets/_doable.py
