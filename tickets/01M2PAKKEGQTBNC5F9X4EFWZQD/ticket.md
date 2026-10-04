+++
id = "01M2PAKKEGQTBNC5F9X4EFWZQD"
title = "callgraph resolves callers only for PRIVATE callees (T-0841 rule): the rapid --files dependents miss every caller of a changed PUBLIC symbol"
type = "task"
category = "done"
outcome = "done"
priority = "high"
reporter = "agent"
created = "2026-09-17T00:00:00Z"
updated = "2026-09-17T00:00:02Z"
aliases = ["T-4560"]
labels = ["milestone:0.532.0"]
scope = ["src/frob/graph/callgraph.py", "src/frob/graph/affects.py", "tests/unit/test_check_scoped_files.py"]

[[acceptance]]
text = "GIVEN a public function changed in module A and imported by modules B and C WHEN the rapid land computes caller dependents THEN B and C are included, resolved through their import bindings (from A import f / import A; A.f), never by bare short name repo-wide"
bound = false

[[acceptance]]
text = "GIVEN two modules each defining a same-named private helper WHEN callers are resolved THEN no cross-module false edge is produced (the T-0841 safety stays)"
bound = false
+++

Disclosed by the T-4553 implementer 2026-09-17: build_call_graph resolves callees by bare short name and, for safety (T-0841, the shared-graph-wrong-for-second-consumer lesson), only links PRIVATE callees; so caller_dependent_files finds callers of changed private symbols only, and the scoped land check still omits every caller of a changed public API. Add import-binding-aware resolution for public symbols (the alias table frob.vet._capability_python already builds per file) so dependents are found without the repo-wide short-name hazard.
