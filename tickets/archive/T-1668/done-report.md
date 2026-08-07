## Done report

Deleted 38 frob:waive OPAQUE001 directives that matched zero findings under
T-1659's semantic OPAQUE001 rewrite (37 originally identified from the
grep sweep, plus tests/test_vet.py:4 found during the deletion pass itself
-- it had been miscounted into the fixture-string set on first read).

Verification method: ran `frob check --only opaque` once before any
deletion and once after all 38 deletions. Both runs report identical
"gate:OPAQUE 0 errors, 0 warnings, 25 waived" -- the same 24 waiver sites
(one directive at src/frob/serve/__init__.py:44 covers two findings) still
match a real finding, byte-for-byte the same reasons, before and after.
Each of the 38 deleted directives was individually cross-checked against
the opaque gate's full findings list and confirmed to NOT appear in it
either before or after deletion -- i.e. each one genuinely waived nothing,
not inferred from the WAIVE004 report alone. A full unscoped `frob check`
run after deletion additionally shows 0 WAIVE004 findings for OPAQUE001
(the one remaining WAIVE004 finding in that run is COV006-related,
pre-existing, unrelated to this ticket).

No FALSE NEGATIVE found: every deleted reason described the exact false-
positive class T-1659 fixed (pytest monkeypatch.setattr, z3 Model.eval,
_mutation_for_eval named after a shell verb, sys.modules reads, fixture
string literals scanned as text) -- none described a genuine indirection
concern the new semantic check might now miss.

Deletions (file path + rule id, one per line, per land's deletion-filter
scope-declaration requirement):

tests/test_gates.py OPAQUE001
tests/test_graph_lock.py OPAQUE001
tests/test_ticket_land.py OPAQUE001
tests/test_gates_suppress.py OPAQUE001
tests/test_app.py OPAQUE001
tests/test_ticket_work_and_land_finish.py OPAQUE001
tests/test_tickets_collision.py OPAQUE001
tests/test_tickets_evidence_cli.py OPAQUE001
tests/unit/test_check_tool_unavailable.py OPAQUE001
tests/unit/strata/test_conform_eval_needle.py OPAQUE001
tests/unit/test_main_entry.py OPAQUE001
tests/unit/strata/test_facts.py OPAQUE001
tests/unit/test_ticket_close_bug002_t1438.py OPAQUE001
tests/unit/strata/test_parse.py OPAQUE001
tests/unit/test_ticket_list_summary.py OPAQUE001
tests/unit/test_fleet_runner.py OPAQUE001
tests/unit/test_app_runners_batch7.py OPAQUE001
tests/unit/test_ticket_runner_land_release.py OPAQUE001
tests/unit/test_check.py OPAQUE001
tests/unit/strata/test_export.py OPAQUE001
tests/unit/strata/test_native_staleness.py OPAQUE001
tests/test_coverage_wait_shared.py OPAQUE001
tests/unit/test_lang_strata.py OPAQUE001
tests/test_capability_registry.py OPAQUE001
tests/test_tickets_review.py OPAQUE001
tests/unit/test_parse_runner_direct.py OPAQUE001
tests/unit/test_ticket_close_bug002_t1427.py OPAQUE001
tests/test_graph.py OPAQUE001
tests/unit/test_app_runners_t0976_mutation_evidence.py OPAQUE001
tests/test_dup.py OPAQUE001
tests/unit/test_dup_core.py OPAQUE001
tests/test_vet.py OPAQUE001
src/frob/vet/_capability_scan.py OPAQUE001
src/frob/vet/_capability_scan.py OPAQUE001
src/frob/deploy/_conform.py OPAQUE001
src/frob/deploy/_conform.py OPAQUE001
src/frob/dup/_pipeline/_smt.py OPAQUE001

Kept (still fire, genuinely bound to a real OPAQUE001 finding, unchanged):
src/frob/app/__init__.py:190, src/frob/app/_config_external.py:381/399/
433/457/471/502 (6), src/frob/app/check_runner.py:71,
src/frob/app/parse_runner.py:64, src/frob/doctor.py:532/776 (2),
src/frob/dup/_pipeline/_probe.py:69, src/frob/fuzz/_signatures.py:45/148
(2), src/frob/gates/_docblocks_refs.py:156/163 (2),
src/frob/graph/lock.py:137/241 (2), src/frob/logging/filter.py:21,
src/frob/mutate/__init__.py:159/176 (2), src/frob/serve/__init__.py:44
(covers 2 findings), src/frob/strata/_native_staleness.py:396,
tests/unit/test_dup_core.py (the T-1659 kernel-name-loop waiver) = 24
directives / 25 findings total.

Not touched: tickets.md/tickets-archive.md/docs/modules/gates.md mentions
of "frob:waive OPAQUE001" are prose/history references, not live
directives; src/frob/gates/_opaque.py's two occurrences are the gate's own
docstring and error-message text, not directives; tests/test_vet.py's 4
remaining occurrences (lines ~6120-6174) are fixture STRING LITERAL test
data the gate's own regression tests feed in, not real directives.

gate:WAIVE (unscoped, OPAQUE001-specific): 38 -> 0 after this change
(computed: 38 stale directives individually confirmed to match nothing;
post-deletion unscoped `frob check` shows 0 WAIVE004 findings tied to
OPAQUE001, only the pre-existing unrelated COV006 one).

### Changed
```
 tickets.md | 275 +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
 1 file changed, 275 insertions(+)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)
- `tests/unit/test_dup_core.py::test_core_unavailable_path_is_err_not_exception` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 0 error(s), 1845 warning(s), 711 waived
- error-findings: none (measured, zero errors)
