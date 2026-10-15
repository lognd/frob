+++
id = "01M4Z1MYJSZJ8CMH8NEA8K30K4"
title = "Land train: adaptive batch size controller (grow on green, halve on red, train_max cap)"
type = "task"
category = "done"
outcome = "done"
priority = "high"
points = 2
parent = "01M4Z1KTKEVF53GWM6ZN7PFN4Q"
reporter = "lognd"
created = "2026-10-15T05:48:05Z"
updated = "2026-10-15T21:09:37Z"
idempotency_key = "train-batchsize"
labels = ["area:land", "creates:crates/frob-land/src/batch_size.rs"]
scope = ["crates/frob-land/src/batch_size.rs", "crates/frob-land/src/lib.rs", "docs/design/build-test-ci.md"]

[[links]]
kind = "blocked-by"
target = "01M4Z1MYSTFADV8FJM8SEXKGZ7"

[[links]]
kind = "blocked-by"
target = "01M4Z295FNVR7DY5A20K3YG11Q"

[[acceptance]]
text = "Given consecutive green trains, then the size grows by one up to the cap"
bound = true

[[acceptance]]
text = "Given a red train, then the size halves and never drops below 1"
bound = true

[[acceptance]]
text = "Given a RAM cap of 3, then the size never exceeds 3"
bound = true

[[acceptance]]
text = "Given train_max 3, then the size never exceeds 3 (the cap is the plain train_max parameter, not RAM-derived)"
bound = true
+++

Pure controller: next_size(prev_size, last_outcome, ram_cap). Grow additively after a green train, halve after a red one, clamp to [1, cap] where cap derives from available RAM and per-candidate build footprint. State is serializable for the train state file.
