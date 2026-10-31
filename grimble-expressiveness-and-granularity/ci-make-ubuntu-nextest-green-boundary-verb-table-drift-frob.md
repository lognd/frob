+++
id = "01M692F1C03YJZBPYFADWMMH0A"
title = "CI: make ubuntu nextest green (boundary, verb_table_drift, frob-land, gob-dev layering, gob-directives inline, equivalence, init_twice, ui_rule_attr, conformance_corpus)"
type = "bug"
category = "in-progress"
priority = "critical"
points = 8
parent = "01M5XNHDQCQBE228DR8FZ3G6WK"
reporter = "lognd"
created = "2026-10-31T13:30:26Z"
updated = "2026-10-31T13:31:59Z"
idempotency_key = "ci-ubuntu-nextest-1"
scope = ["crates/frob-cli/tests/**", "crates/frob-land/tests/**", "crates/gob-dev/tests/**", "crates/frob-check/tests/**", "crates/gob-term/**", "crates/frob-present/**", "crates/gob-cli/**"]

[[acceptance]]
text = "ubuntu-latest nextest passes with zero failures on experimental"
bound = false
+++

Failing in run 41201973240: crunk/grimble boundary (SF4719D), frob-check equivalence fixture_b, frob-cli init_twice + verb_table_drift x2, frob-docgen verb_admission, frob-land x4, gob-dev layering x2, gob-directives inline err_cases, grimble explain_cmd table, grimble-model conformance_corpus, gob-macros ui_rule_attr (70s). Triage each: fix or fix the test; no skips.
