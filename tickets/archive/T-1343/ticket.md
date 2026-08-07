---
id: T-1343
title: COV006 WARN on test_app_lazy_dispatch.py subprocess-boundary test
state: done
kind: bug
origin: human
created: '2026-07-31'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- tests/unit/test_app_lazy_dispatch.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
- tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_unknown_subcommand_returns_none
designated_repro_test: null
threat: null
component: null
---
tests/unit/test_app_lazy_dispatch.py::TestResolveRunner::test_imports_only_the_requested_subcommands_module
drives its assertions through a subprocess.run([sys.executable, "-c", code])
call, so the actual `_resolve_runner(...)` invocation lives inside a string
literal executed in a child process -- structurally invisible to
frob.graph.callgraph's in-process, AST-based best-effort BFS, the same
"process boundary is structurally invisible" class already precedented by
tests/system/test_cli_ticket_land.py::TestLandCLI::test_dry_run_reports_clean's
own COV006 waiver.

T-1337 (OPAQUE001 lazy-dispatch fix in src/frob/app) made _resolve_runner's
module-name resolution statically visible (a closed if/elif chain of
literal imports replacing importlib.import_module), but this COV006 WARN
on the test->symbol binding is unrelated to that fix and pre-dates it --
it is a test-harness-shape gap, not a resolvability gap. Add a
`frob:waive COV006 reason="..."` on this specific frob:tests edge
(tests/unit/test_app_lazy_dispatch.py is out of T-1337's declared scope,
src/frob/app/** + docs/modules/app.md only) citing the subprocess-boundary
precedent above.