+++
id = "01M48Q2BWRT117K8E163MWHDN2"
title = "Activity inference: implementing, testing, waiting, landing, idle from observed signals"
type = "story"
category = "todo"
priority = "medium"
parent = "01M48Q294B33TB7C0GSATZRGJB"
reporter = "lognd"
created = "2026-10-06T13:39:52Z"
updated = "2026-10-06T13:39:52Z"
scope = ["crates/frob-metrics/**", "crates/frob-lease/**", "crates/frob-land/**", "crates/frob-tests/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX82YQ43A8SWS4F128J4NT"

[[acceptance]]
text = "a fixture timeline classifies into the expected segments"
bound = false

[[acceptance]]
text = "nothing is written to the code branch"
bound = false

[[acceptance]]
text = "the land summary carries per-activity totals"
bound = false
+++

Classify each in-progress ticket's time from signals frob already sees or records cheaply, never from a state an agent sets: lease events, worktree commit times, worktree file mtimes when frob looks, test and evidence runs, goway job reports when present, lease refusals (record E-LEASE-HELD as a local event), land start and end; sessionise with an idle gap threshold. Store in a local .frob activity journal (not committed), summarised onto the ticket at land on the ticket branch. Feeds board --brief and stats.
