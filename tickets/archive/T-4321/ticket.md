---
id: T-4321
title: SCOPE002 pre-existing closure debt on check/__init__.py's declared scope
state: dropped
kind: bug
origin: human
created: '2026-09-08'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/check/__init__.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found while working T-4309 (bugfix in as_text's tool-summary rendering). T-4309's own ticket scope is the entire src/frob/check/__init__.py file (declared at ticket creation, not something T-4309 chose). 'frob check --only gates-fast --ticket T-4309' reports 11 SCOPE002 findings totalling 130+ symbols across many unrelated files (docs/commands/check.md, docs/modules/gates.md, tests/unit/test_check.py, tests/unit/test_check_admission.py, src/frob/check/_native.py, src/frob/check/_python.py, src/frob/check/_ts.py, ...) whose frob:doc/frob:tests/private-helper edges point outside the declared scope -- pre-existing to any change T-4309 made (reproducible against untouched symbols like _admission_budget, run_check_ts). This makes any ticket scoped to the whole check/__init__.py file structurally unable to pass frob check --only gates-fast cleanly without a scope blowout across dozens of files. Separately, these SCOPE002 Violation objects are built with severity=Severity.WARN (per the gate's own docstring: 'a nudge, not a hard block'), but they render under frob check's ## Errors section and count toward total_errors/the FAIL verdict, not ## Warnings -- worth checking whether _diag_severity's WARN mapping is actually being hit for gate:SCOPE specifically. Recommend: either narrow check/__init__.py-scoped tickets going forward to smaller symbol-level scope, or fix the SCOPE002-to-error miscategorization, or both.

## Drop reason
- 2026-09-09: Superseded twice over: T-4310 (landed) made SCOPE002 respect ticket.scope_breadth_ack, giving a reasoned per-ticket ack for disproportionate closure breadth (mirroring TICK009); T-4331 (landed) demoted SCOPE002 back to WARN in frob.toml (its own code hardcodes Severity.WARN, docstring calls it 'a nudge, not a hard block'). Measured the actual closure gate:check --only gates-fast --ticket T-4321 now reports gate:SCOPE 0 errors/12 warnings (WARN, non-blocking). Inspected the 12 SCOPE002 findings against check/__init__.py's declared scope: doc edges point to docs/commands/check.md#public-api for CheckResult/as_json/as_text (correct: genuine public API doc) and to docs/modules/gates.md#rule-catalog for _abandoned_autofix_result/run_check (correct: gates.md's rule catalog is the authoritative doc for every CHK-GATE-* rule id these symbols enforce/implement, not a drifted anchor -- no frob:doc directive anywhere near-misses a nearer public caller). Test edges (test_check.py, test_check_admission.py, test_cli_check.py, test_app_runners_batch6.py, test_check_measurement.py, test_check_tool_unavailable.py, test_fix_engine_journal.py) are real frob:tests coverage of symbols actually defined in check/__init__.py, not artefacts. Private-helper closures into _native.py/_python.py/_ts.py are real function calls (_cpp_post_build_tasks -> _run_ctest etc.) reflecting check/__init__.py's genuine architectural role as the dispatch hub calling into per-language gate runners. No drifted/wrong edges found -- this is the 'big shared module legitimately documented in a big shared doc' case, not the 'doc anchor drifted onto nearest private symbol' pattern. The ack mechanism (frob ticket scope-ack) is the correct, already-shipped answer for any future ticket scoped to this file; no code fix is warranted, and driving this specific closure to zero would itself be the unbounded-scope-expansion failure mode the ticket warns against.
