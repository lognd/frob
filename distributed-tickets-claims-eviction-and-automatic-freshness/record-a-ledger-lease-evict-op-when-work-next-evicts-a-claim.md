+++
id = "01M5DXB29AMFPY3Y3BX8ST9CAT"
title = "Record a ledger lease evict op when work --next evicts a claim"
type = "task"
category = "in-progress"
priority = "medium"
points = 3
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T00:21:23Z"
updated = "2026-10-21T02:15:23Z"
+++

evict_one_idle_agent only transitions the ticket to todo with a note; add the lease evict ledger op (see 1N3HRWA). Also local UTC offset for evict_rate day count (currently UTC). Follow-up of 8DKB004.
