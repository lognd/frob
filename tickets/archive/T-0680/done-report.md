## Done report

Routed the registry-YAML out_of_scope:<reason> disposition surface through the
same T-0382 caught_by token-resolution verification strata already runs for
its own OutOfScopeEntry/BenignCapability/OutOfScopeRegulation models
(THREAT006/COMPLIANCE004), closing the one named gap left after T-0382/T-0383.

New REG011 (WARN, matching REG008/REG009's first-turn-on precedent) fires on
an out_of_scope reason that either (a) names no rule-id-/CWE-id-shaped token
at all and is not a substantive "none -- <explanation>" reasoned-none
disclosure, or (b) names a token that does not resolve against the live
gate-rule-id set / strata's CWE catalog. Implementation reuses
frob.strata._threat's existing token-extraction/resolution helpers
(_caught_by_referenced_tokens, _caught_by_unresolved_tokens, CAUGHT_BY_NONE_MARKER,
ALL_CATALOG) rather than duplicating the regex/logic -- imported lazily inside
the functions that need them, since frob.gates.__init__ imports this module
during frob.strata._threat's own initialization chain (frob.strata._threat ->
_effects -> frob.vet -> frob.vet._models -> frob.gates._models -> triggers
frob.gates.__init__ -> this module) and a module-scope import hit that
partially-initialized module.

Fixed one existing test fixture (test_fully_dispositioned_fixture_passes) whose
out_of_scope reason ("no code executes this concept") would now also earn a
REG011 WARN; reworded it to the substantive reasoned-none form
("none -- no code executes this concept") to keep asserting violations == ().

Out of scope, filed as a draft: REG011 is not yet registered in
frob.gates.__init__._KNOWN_GATE_RULES or docs/design/registry/check-coverage.yaml
-- another agent held gates/__init__.py for T-0680's duration per dispatch
instructions, so that wiring is a refiled follow-up ticket instead (REG011 registration).

Mutation-evidence self-check: every branch added
(_is_reasoned_none's substantive-vs-bare-none split, _classify_out_of_scope_
caught_by's no-token / unresolved-token / resolved-token / reasoned-none
paths) has both a fire and a no-fire test exercising it through registry_gate's
public interface (TestOutOfScopeCaughtBy's 5 cases), so inverting any of those
conditionals flips at least one test's expected rule-presence assertion.

### Changed
```
 docs/design/registry/EXHAUSTIVENESS-GATE.md |  57 +++++---
 src/frob/gates/_registry_exhaustiveness.py  | 195 +++++++++++++++++++++++++---
 tests/test_registry_exhaustiveness.py       | 111 +++++++++++++++-
 3 files changed, 327 insertions(+), 36 deletions(-)
```

### Evidence
- `tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_no_control_warns` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_unresolved_rule_warns` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_reason_naming_resolved_rule_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_substantive_reasoned_none_is_silent` (pytest node id, verified passing when recorded)
- `tests/test_registry_exhaustiveness.py::TestOutOfScopeCaughtBy::test_bare_none_is_not_substantive` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
