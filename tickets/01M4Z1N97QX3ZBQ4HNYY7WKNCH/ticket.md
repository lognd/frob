+++
id = "01M4Z1N97QX3ZBQ4HNYY7WKNCH"
title = "Land train: design first - amend D25, foreground driver, invariants, cost model"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:15Z"
updated = "2026-10-15T12:48:01Z"
idempotency_key = "train-docs"
labels = ["area:land"]
scope = ["docs/design/build-test-ci.md", "docs/design/tickets.md", "docs/design/README.md", "docs/design/cli.md"]

[[acceptance]]
text = "Given the doc, then it describes verbs, state file and bisection rounds bound"
bound = true

[[acceptance]]
text = "Given gob-dev gen all --check, then it passes"
bound = true
+++

Add a Fast lands subsection (land train): candidate, union cone, group-testing bisection with citation (Uber SubmitQueue EuroSys 2019), adaptive batch size, state schema, verbs, interactions with land.lock, require_base_green, CI net. Update the land lock section in tickets.md; note relation to the done merge train ~DSD1QBK and enqueue ~3V4VKC9. Run gob-dev gen all if generated docs change.
