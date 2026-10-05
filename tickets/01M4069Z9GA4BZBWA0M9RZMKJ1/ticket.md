+++
id = "01M4069Z9GA4BZBWA0M9RZMKJ1"
title = "Exit: two outside repositories managed by frob for two cycles with no ledger data loss"
type = "task"
category = "todo"
priority = "medium"
points = 3
parent = "01M4065Y4N6DQG30TRSP2QNP8T"
reporter = "lognd"
created = "2026-10-03T06:13:00Z"
updated = "2026-10-05T05:14:50Z"
idempotency_key = "m2-rel-accept-outside"
labels = ["milestone:2", "area:release"]
scope = ["docs/guides/outside-repositories.md"]

[[links]]
kind = "blocked-by"
target = "01M4069RPPQE1ES1914K6V6Y0D"

[[links]]
kind = "blocked-by"
target = "01M4069Z0HH5RV8TNPFVA936C5"

[[acceptance]]
text = "Given both repositories after two cycles, when ticket doctor runs in each, then it reports no drift, dangling links or event-order problems"
bound = true

[[acceptance]]
text = "Given the event counts taken at each cycle close, when compared with the final fold, then none decreased"
bound = true
+++

Tracking ticket for exit criterion 2. BLOCKED ON THE OWNER creating the two repositories (the cloc-style tool and the mdcat fork); the owner attaches the two repository URLs as a comment when they exist. Then each repository runs frob init, two cycles of 7 days, tickets worked and landed; at the end, ledger refs are fold-checked (frob ticket doctor clean) and a count of events written equals the count read back. Gaps become tickets in this epic. Writes a short log of findings at docs/guides/outside-repositories.md.
