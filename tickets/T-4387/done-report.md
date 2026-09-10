## Done report

T-4139 (landed fa90c64cd) added the DOC014 gate rule in
src/frob/gates/_doclink_docanchor.py (a `frob:enforces CHK-GATE-DOC014`
directive at line 507/513) but never registered "DOC014" in
_KNOWN_GATE_RULES in src/frob/gates/_waive.py, so
tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
failed on every CI OS leg with: rule id(s) constructed in src/frob/gates
or src/frob/strata but missing from _KNOWN_GATE_RULES:
{'DOC014': 'src/frob/gates/_doclink_docanchor.py:513'}.

Fixed by mirroring exactly what DOC013 (T-2801/T-2843, the prior instance
of this same "rule fires but isn't registered" gap) has in each of the
three registries: added "DOC014" to the _KNOWN_GATE_RULES tuple in
src/frob/gates/_waive.py with a short docstring-comment pointing at the
emitting function; added a DOC014 row to the severity table and a
DOC014 entry to the frob:enumerates member list in docs/modules/gates.md;
and added a CHK-GATE-DOC014 entry to
docs/design/registry/check-coverage.yaml in the same shape as
CHK-GATE-DOC013.

Verified: tests/gates_suite/test_sys.py::TestKnownGateRuleIds::test_every_emitted_rule_literal_is_known
passes with the fix applied, and `frob ticket evidence --check-repro`
confirmed it genuinely fails at the pre-fix parent commit
(ed294c2f276b57146ed502f78d5eddb220944570).

### Changed
```
 docs/design/registry/check-coverage.yaml | 5 +++++
 docs/modules/gates.md                    | 3 ++-
 src/frob/gates/_waive.py                 | 9 +++++++++
 3 files changed, 16 insertions(+), 1 deletion(-)
```
