+++
id = "01M4P1YV1XW7SSAX0RGESD8FAR"
title = "Archive the v1 import: move 44 MB of old done-report comments out of the live ledger tree"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-11T18:00:19Z"
updated = "2026-10-11T18:00:19Z"

[[acceptance]]
text = "Imported comments live in a compressed archive that frob ticket show can still read on demand"
bound = false

[[acceptance]]
text = "Ledger tree raw size drops by at least 40 MB with ticket doctor clean"
bound = false

[[acceptance]]
text = "Fold, list and check timings do not regress (telemetry before/after)"
bound = false
+++

v1-imported done-report comments are about 44 MB of the 63 MB ledger tree and are read by nothing on the hot path.
