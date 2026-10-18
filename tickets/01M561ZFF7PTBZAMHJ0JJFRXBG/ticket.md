+++
id = "01M561ZFF7PTBZAMHJ0JJFRXBG"
title = "gob-dev tests fail: publish plan Cycle and profile_coverage serve/tokens scenarios"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-17T23:08:31Z"
updated = "2026-10-18T00:04:05Z"
scope = ["crates/gob-dev/**"]
+++

found while working P8VPKKP: publish::tests::this_workspace_reads_and_plans_without_a_cycle and profile_coverage every_leaf_command_has_a_scenario_or_a_skip_reason fail independent of that change
