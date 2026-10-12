+++
id = "01M4K8TMXWK93ZKAAFQE9W4M0D"
title = "Wire the E-STATE-TRACKED guard into frob, grimble and crunk check runs"
type = "task"
category = "todo"
priority = "high"
points = 2
reporter = "Claude"
created = "2026-10-10T16:02:38Z"
updated = "2026-10-10T16:02:38Z"
scope = ["crates/frob/src/**", "crates/grimble/src/**", "crates/crunk/src/**"]

[[links]]
kind = "blocked-by"
target = "01M3ZX7TR7HMSXPCQSHFSG8SMS"

[[acceptance]]
text = "Given a repo tracking .frob/cache.sqlite, when frob check runs, then exit code is 3 and the envelope code is E-STATE-TRACKED naming the file"
bound = false

[[acceptance]]
text = "Given the same repo for grimble check and crunk check, then both exit 3 with E-STATE-TRACKED"
bound = false
+++

~FSG8SMS added gob_trust::check_state_untracked and Refusal::state_tracked. Call them at the start of every frob/grimble/crunk run so a tracked .frob/.grimble/.crunk file exits 3 with E-STATE-TRACKED.
