+++
id = "01M35RZY836HKC7GDWBJGD6ERZ"
title = "test_every_may_is_load_bearing: 24 non-load-bearing 'may' mutation findings on live repo design"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
points = 2
reporter = "human"
created = "2026-09-23T00:00:00Z"
updated = "2026-09-23T00:00:02Z"
aliases = ["T-5379"]
labels = ["milestone:0.534.0"]
scope = ["tests/unit/strata/test_mutation_audit.py", "src/frob/strata/_mutation_audit.py"]
+++

CI run 35819358270 (ubuntu/macos/windows); re-verified failing on dev tip 39b89ed091: tests/unit/strata/test_mutation_audit.py::TestMayMutationAuditRealRepo::test_every_may_is_load_bearing fails -- run_may_mutation_audit(repo_root) reports 24 findings where deleting or substituting a design 'may' atom does not trip SYS100 (and where required, the SYS100+SYS101 pair), e.g. node='testsuite' atom='process-control' mode='substitute' sys100_fired=True sys101_fired=False. Each finding needs either a real enforcing check wired up for that atom or the design declaration corrected/removed. Not covered by any open ticket found by title/body search; needs per-atom triage, not a single fix.
