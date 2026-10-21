+++
id = "01M5EKM08ZM45RZ1JBHC68F156"
title = "mirror: persist read-back and retained tracker event values in the map shard"
type = "task"
category = "todo"
priority = "medium"
parent = "01M5CVZND2H3YDDB67WZ7ANRQY"
reporter = "lognd"
created = "2026-10-21T06:50:44Z"
updated = "2026-10-21T06:50:44Z"
+++

found while working ~ACC0466: LedgerTickets::state returns an empty ReadBack and no event_values because the shard carries neither
