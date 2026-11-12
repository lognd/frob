+++
id = "01M6VYQZ5FEEP4TN8ZHVBCK63N"
title = "CI check step fails on 120 errors: LOG001/LOG002 shell scripts, TESTQ001/TESTQ002 tests"
type = "bug"
category = "in-progress"
priority = "critical"
points = 3
reporter = "lognd"
created = "2026-11-07T21:30:58Z"
updated = "2026-11-12T13:31:28Z"
labels = ["ci"]
scope = [".github/scripts/**", "crates/crunk-tailwind/tests/runtime.rs", "crates/frob-check/src/concurrent.rs", "crates/frob-check/tests/it/sibling.rs", "crates/frob-land/src/git.rs", "crates/frob-ledger/src/refresh.rs", "crates/frob/tests/it/agent_heavy.rs", "crates/frob/tests/it/lease_heartbeat.rs", "crates/frob/tests/it/sync_policy.rs", "crates/gob-cache/src/lib.rs", "crates/gob-check/tests/ui_product.rs", "crates/gob-dev/src/profile/scenarios.rs", "crates/gob-dev/src/registry.rs", "crates/gob-ir/tests/it/deep.rs", "crates/gob-ir/tests/it/wire.rs", "crates/gob-macros/tests/ui.rs", "crates/gob-macros/tests/ui_rule_attr.rs", "crates/gob-packs/src/activation.rs", "crates/gob-plan/src/grl/parse/tests/props.rs", "crates/gob-plan/tests/grl_errors/main.rs", "crates/gob-time/tests/time.rs", "crates/grimble-ci/tests/rules.rs"]

[[acceptance]]
text = "given the CI rust ubuntu-latest job, when cargo dev ci --step check runs, then it exits 0"
bound = true
+++

Run 42412121808 rust (ubuntu-latest): cargo dev ci --step check exits 1 with 120 error findings: 42 LOG001 and 1 LOG002 in bash scripts, 30 TESTQ002 and 26 TESTQ001 in tests; plus 24 REF001/REL003 caused by the unpushed ledger. Fix the code (route shell output through the logging helper, give tests assertions, fake clocks) rather than baselining.
