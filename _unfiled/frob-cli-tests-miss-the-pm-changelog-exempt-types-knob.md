+++
id = "01M5GSQD9DV4G2SFP395JM2JJS"
title = "frob-cli tests miss the pm.changelog_exempt_types knob (config_sync, init_twice, pm_knob_order)"
type = "bug"
category = "in-progress"
priority = "high"
points = 2
reporter = "lognd"
created = "2026-10-22T03:15:56Z"
updated = "2026-10-22T03:32:15Z"
scope = ["crates/frob/**", "frob.toml", "docs/**", "changelog.d/**"]

[[acceptance]]
text = "the three named frob-cli tests pass"
bound = true
+++

After YYJGRFJ added [pm] changelog_exempt_types, three frob-cli tests fail: config_sync_adds_missing_knobs_once, init_twice_second_is_already_and_changes_nothing, pm_knob_order_is_one_across_init_the_sync_list_and_the_repo_frob_toml. Add the knob to the init template, sync list, repo frob.toml and snapshots.
