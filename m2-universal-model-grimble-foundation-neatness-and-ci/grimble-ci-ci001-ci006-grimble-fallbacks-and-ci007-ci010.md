+++
id = "01M5F010QB00AR00D4HYVYYPWH"
title = "grimble-ci: CI001/CI006 grimble fallbacks and CI007, CI010"
type = "task"
category = "in-progress"
priority = "medium"
points = 5
parent = "01M3Z6XVPGS23NYVXDF0BTGRT5"
reporter = "lognd"
created = "2026-10-21T10:27:34Z"
updated = "2026-10-21T21:50:19Z"
scope = ["crates/grimble-ci/**", "docs/design/cicd.md", "changelog.d/01M5F010QB00AR00D4HYVYYPWH.added.md"]

[[acceptance]]
text = "CI001 flags external uses refs that are not a full commit SHA, skipping local, allowlisted and digest-pinned ones"
bound = true

[[acceptance]]
text = "CI006 flags checkout of the PR head under pull_request_target or workflow_run"
bound = true

[[acceptance]]
text = "CI007 flags attacker-influenced expressions in run scripts, narrow set as Error and others Advisory, env passthrough clean"
bound = true

[[acceptance]]
text = "CI010 flags checkout without persist-credentials false when artifacts or third-party actions are used"
bound = true

[[acceptance]]
text = "The supply rules tolerate empty, non-mapping and unterminated input without panicking"
bound = true
+++

Deferred from ~8886VJ4: native fallbacks for the zizmor-bound pinned-ref and prt-head-checkout rules, plus CI007 and CI010.
