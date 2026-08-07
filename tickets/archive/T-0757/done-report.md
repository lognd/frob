## Done report

Grounded in T-0611 (a TypeScriptAdapter landed inside the deliberately
tree_sitter-free src/frob/arch/_normalized.py, caught only by a human
reviewer reading the diff) and T-0682 (frob.tickets._land._newer's
qualified richness ordering fixed wrong in the opposite direction from
the bug it was fixing, twice, because the property lived only in a
reviewer's head).

Grammar: frob:invariant gains two OPTIONAL obligation attrs (no new
verb) -- no_import="pkg[,pkg2,...]" (import-forbidding) and
establishes="<property text>" (establish-property), validated by a new
_attrs_verb_error_invariant in src/frob/graph/dsl.py, registered in
_VERB_ATTRS_VALIDATORS. _TESTS_KINDS widened to include "property".
Property-tested (Hypothesis, over the REAL parser) in
tests/unit/graph/test_dsl_invariant_property.py: a bare
frob:invariant INV-### (no obligation attrs -- every pre-T-0757 anchor)
proven to parse identically before/after across generated INV-### ids,
plus generated-input coverage for both new attrs' own shape rules.

Gate: new module src/frob/gates/_design_invariants.py registers INV007
(import-forbidding, checked against frob.lang.extract_imports's raw
import specifiers with a "." boundary prefix match) and INV008
(establish-property, checked against a bound frob:tests kind="property"
edge reaching the anchor). Both wired into the existing "invariant"
gate group in src/frob/gates/__init__.py, rule ids added to
_KNOWN_GATE_RULES. Both ERROR severity (explicitly-declared obligations
only, no bare-vocabulary heuristic, so no first-turn-on debt corpus).

Seeded: INV-042 (src/frob/arch/_normalized.py, no_import="tree_sitter",
the T-0611 class) and INV-043 (src/frob/tickets/_land.py's _newer,
establishes=..., the T-0682 class) with real evidence -- INV-043's
kind="property" evidence is a new Hypothesis property test
(TestNewerWinnerQualifiedPreferenceProperty, tests/test_ticket_land.py)
proving both the terminal-supremacy and qualified-richness tiers
exhaustively over the small state space _newer_winner discriminates on,
not just the existing hand-picked field-incident cases.

docs/modules/gates.md updated: INV007/INV008 table rows plus a full
"INV007 and INV008 (T-0757)" prose section. frob fmt --check verified
clean on every touched file after adding the new directive forms.

Scope was widened beyond the ticket's original declared globs (which
named no test files at all) via frob ticket scope --add, reason
recorded in the scope_changes audit trail: tests/unit/graph/test_dsl.py,
tests/unit/graph/test_dsl_invariant_property.py,
tests/unit/test_design_invariants.py, invariants/**,
tests/test_ticket_land.py -- all needed for the ticket's own mandated
property-test discipline and the two seeded invariants' evidence.

Mid-ticket: git merge main pulled 2 commits landed by other agents
(T-1019, T-0665) while this ticket was in flight; verified via
git diff main --diff-filter=D --stat (empty) and re-grepped
src/frob/gates/__init__.py's wiring survived the auto-merge intact.

Filed: none -- no out-of-scope work discovered.

### Changed
```
 docs/modules/gates.md                           |  63 +++++++
 invariants/INV-042.md                           |  24 +++
 invariants/INV-043.md                           |  32 ++++
 src/frob/arch/_normalized.py                    |  10 ++
 src/frob/gates/__init__.py                      |  13 ++
 src/frob/gates/_design_invariants.py            | 210 ++++++++++++++++++++++++
 src/frob/graph/dsl.py                           |  55 ++++++-
 src/frob/tickets/_land.py                       |   4 +
 tests/test_ticket_land.py                       | 169 ++++++++++++++++++-
 tests/unit/graph/test_dsl_invariant_property.py | 137 ++++++++++++++++
 tests/unit/test_design_invariants.py            | 163 ++++++++++++++++++
 11 files changed, 870 insertions(+), 10 deletions(-)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 18 passed (from 18 evidence id(s))
- gates: 9 error(s), 2804 warning(s), 344 waived
- error-findings: ARCH001@src/frob/arch/_cpp_mayraise.py, COV001@src/frob/arch/_models.py, COV001@src/frob/gitlog/__init__.py, COV001@src/frob/process/parsers/common.py, COV001@src/frob/render/_color.py, COV001@src/frob/render/_elements.py, PERF003@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/arch/_cpp_mayraise.py, PERF004@src/frob/gates/_design_invariants.py
