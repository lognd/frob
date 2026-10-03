+++
id = "01M410A4XR556D484CYYP2Y2R3"
title = "lease: exempt changelog.d fragments from scope overlap (shared_files)"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-03T13:47:29Z"
updated = "2026-10-03T13:48:02Z"
scope = ["frob.toml"]
+++

found while working ~3TXB8SR: another ticket leasing changelog.d/** blocks every other ticket from widening to its own <ULID>.<type>.md, so check --ticket reports SCOPE001 on the fragment the close guard requires. Fragments are one file per ticket, so add changelog.d/** to [lease] shared_files or have the scope check always allow the ticket's own fragment.
