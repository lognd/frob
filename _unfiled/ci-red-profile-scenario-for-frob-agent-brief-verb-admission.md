+++
id = "01M5P7R3CQB4M59P384SAYG120"
title = "CI red: profile scenario for frob agent brief, verb_admission table, flaky lease_widen wait test"
type = "bug"
category = "todo"
priority = "high"
points = 3
reporter = "lognd"
created = "2026-10-24T05:57:11Z"
updated = "2026-10-24T05:57:11Z"
scope = ["crates/gob-dev/profile.toml", "crates/frob-docgen/**", "crates/frob/tests/**", "docs/**"]

[[acceptance]]
text = "gob-dev profile passes: every leaf command including frob agent brief has a scenario or skip reason"
bound = false

[[acceptance]]
text = "frob-docgen verb_admission and profile_coverage tests pass"
bound = false

[[acceptance]]
text = "lease_widen add_scope_wait test is deterministic (no timing flake)"
bound = false
+++

CI run on f674a169c3: profile job failed 'leaf commands with no scenario ... frob agent brief'; frob-docgen verb_admission::the_shipped_verb_table_matches_the_registry and profile_coverage::every_leaf_command_has_a_scenario_or_a_skip_reason failed; frob-cli lease_widen::add_scope_wait_blocks_on_a_held_overlap_and_succeeds_when_it_releases failed (1.8s, likely timing). Check whether landed GNC7N38 (rule why) already fixed part of it.
