+++
id = "01M5EKM0HMCYE834CN3J9NEK8B"
title = "frob: wire LedgerTickets into the mirror command with a facts provider"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T06:50:45Z"
updated = "2026-11-13T09:15:30Z"
scope = ["crates/frob/src/mirror_cmd.rs"]

[[acceptance]]
text = "LedgerTickets is constructible from the frob crate with a facts provider built on facts_of"
bound = true
+++

found while working ~ACC0466: LedgerTickets takes an injected FactsFn; mirror_cmd::facts_of in the frob crate should supply it
