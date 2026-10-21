+++
id = "01M480C43A6BCH54NX8C5DQ4WJ"
title = "Rule coverage gaps: frob rules without an mdtest pair or fixture"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M47QTS14TAZQ67NN2M9NHDJP"
reporter = "lognd"
created = "2026-10-06T07:03:15Z"
updated = "2026-10-21T21:13:39Z"
scope = ["crates/*/tests/mdtest/**", "crates/gob-mdtest/coverage-allowlist.toml", "changelog.d/01M480C43A6BCH54NX8C5DQ4WJ.changed.md", "crates/gob-mdtest/FORMAT.md", "docs/design/testing.md", "crates/frob-pm/tests/corpus.rs", "crates/gob-config/tests/cfg001_corpus.rs", "crates/frob-check/tests/corpus.rs", "crates/frob-obligations/tests/corpus.rs", "crates/gob-directives/tests/*.rs"]

[[acceptance]]
text = "Every frob-pm Unresolved rule (PM003-PM012, PM031, PM032) has an unresolved mdtest case"
bound = false

[[acceptance]]
text = "The frob-obligations language matrix cells for TODO001, COV001 (binary), REF001, TICK006, DOC001 and DOC002 are filled"
bound = true

[[acceptance]]
text = "READ001, SIB001, TOOL001 and TICK007 each have an unresolved mdtest case"
bound = true

[[acceptance]]
text = "The allowlist shrank and every remaining frob entry is tracked by a ticket"
bound = false
+++

Umbrella for the frob allowlist in crates/gob-mdtest/coverage-allowlist.toml (~BGB8V55). Each rule needs an mdtest fire/clean pair or a fixture, then its allowlist entry is deleted. Rules: AFFECT001 CFG001 CI001 CI003 CI006 CI007 CI010 CI014 COV003 DRIFT001 DRIFT002 DRIFT003 DRIFT004 EXC005 PERF001 PROC001 READ001 SCOPE001 SIB001 TEST001 TICK001 TICK002 TICK003 TICK004 TICK005 TOOL001 TOOL002
