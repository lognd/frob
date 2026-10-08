+++
id = "01M4DPJGWGB4HFQD5G3CF0E762"
title = "cycle velocity: done_facts reads events with events_many, not one call per ticket"
type = "task"
category = "todo"
priority = "medium"
points = 1
parent = "01M4D6NB00MBEV0PRHN15CXZP8"
reporter = "lognd"
created = "2026-10-08T12:07:25Z"
updated = "2026-10-08T12:07:25Z"
scope = ["changelog.d/**", "crates/frob-pm/**"]

[[acceptance]]
text = "Given cycle velocity, when traced, then events are read in one batch"
bound = false
+++

Follow-up from ~VXFAY3P (769 calls).
