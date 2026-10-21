+++
id = "01M5EWJDDGZS0G0346T3A6WZ0W"
title = "Run selection uses fixed order: sweep_k above budget capacity and non-sweep classes can starve (F8)"
type = "bug"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M3ZX77302X3HQF4Z4P7WC0WS"
reporter = "lognd"
created = "2026-10-21T09:27:09Z"
updated = "2026-10-21T09:48:52Z"
scope = ["crates/frob-mirror/src/run.rs", "docs/design/mirror.md", "changelog.d/01M5EWJDDGZS0G0346T3A6WZ0W.fixed.md"]

[[acceptance]]
text = "Update, Create and Reconcile rotate round robin across runs using cursors persisted in the mirror store"
bound = true

[[acceptance]]
text = "With sweep_k above the budget capacity every sweep ticket is still visited across runs"
bound = true

[[acceptance]]
text = "Stored cursors round trip; a missing record starts fresh, a corrupt one errors, a removed cursor ticket wraps, and an idle run writes no cursor record"
bound = true
+++

Found while working ~VR8VGH2. run_locked calls select(items, &Cursors::default(), ..) every run, so Update/Create/Reconcile use a fixed order and are never persisted round robin, and select re-sorts the sweep batch so with sweep_k greater than the budget capacity the lowest-sorted ticket is always served first and later ones starve.
