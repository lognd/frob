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
updated = "2026-10-21T09:45:28Z"
scope = ["crates/frob-mirror/src/run.rs"]
+++

Found while working ~VR8VGH2. run_locked calls select(items, &Cursors::default(), ..) every run, so Update/Create/Reconcile use a fixed order and are never persisted round robin, and select re-sorts the sweep batch so with sweep_k greater than the budget capacity the lowest-sorted ticket is always served first and later ones starve.
