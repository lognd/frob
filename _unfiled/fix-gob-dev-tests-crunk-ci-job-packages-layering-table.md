+++
id = "01M5HBRM670YEGE2JES5A8WY0M"
title = "Fix gob-dev tests: crunk CI job packages, layering table, profile scenarios"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-22T08:31:11Z"
updated = "2026-10-22T23:45:34Z"
scope = ["crates/gob-dev/**"]

[[acceptance]]
text = "ci_plan::the_crunk_job_lists_every_crunk_package passes (crunk-layout and crunk-scene listed)"
bound = false

[[acceptance]]
text = "layering::workspace_layering_holds_and_every_crate_has_a_layer passes, with ALLOWED rows for gob-dev -> crunk and grimble"
bound = false

[[acceptance]]
text = "profile_coverage::every_leaf_command_has_a_scenario_or_a_skip_reason passes for crunk edit, export dtcg, extract-token, import dtcg, rename"
bound = false
+++

Found by the ARDPKKS implementer; the first fails without its changes, the others are new-crate or new-verb gaps.
