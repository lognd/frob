+++
id = "01M480C43A6BCH54NX8C5DQ4WJ"
title = "Rule coverage gaps: frob rules without an mdtest pair or fixture"
type = "task"
category = "todo"
priority = "medium"
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T07:03:15Z"
updated = "2026-10-06T07:03:15Z"
scope = ["crates/*/tests/mdtest/**"]

[[acceptance]]
text = "every listed rule has an mdtest fire/clean pair or a fixture and no frob entry remains in the allowlist"
bound = false
+++

Umbrella for the frob allowlist in crates/gob-mdtest/coverage-allowlist.toml (~BGB8V55). Each rule needs an mdtest fire/clean pair or a fixture, then its allowlist entry is deleted. Rules: AFFECT001 CFG001 CI001 CI003 CI006 CI007 CI010 CI014 COV003 DRIFT001 DRIFT002 DRIFT003 DRIFT004 EXC005 PERF001 PROC001 READ001 SCOPE001 SIB001 TEST001 TICK001 TICK002 TICK003 TICK004 TICK005 TOOL001 TOOL002
