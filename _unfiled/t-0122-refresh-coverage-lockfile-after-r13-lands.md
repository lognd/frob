+++
id = "01M1T07J3TCN6FNPK10S5DWN08"
title = "Refresh coverage lockfile after r13 lands"
type = "docs"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-06T00:00:00Z"
updated = "2026-09-06T00:00:04Z"
aliases = ["crunk:T-0122"]
labels = ["component:crunk", "source:crunk"]
scope = ["frob-coverage.lock.json"]

[[acceptance]]
text = "given the refreshed lockfile, when frob check runs, then TEST006 is clear"
bound = true
+++

Post-land stamp refresh on the primary after T-0119/T-0120 landed; the lockfile change needs ticket attribution per the standing pattern.
