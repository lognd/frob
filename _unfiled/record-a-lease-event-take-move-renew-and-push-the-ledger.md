+++
id = "01M5DBVSNP24G2WVGGSHP5YGDE"
title = "Record a lease event (take/move/renew) and push the ledger after the claim"
type = "task"
category = "todo"
priority = "medium"
points = 3
reporter = "lognd"
created = "2026-10-20T19:15:57Z"
updated = "2026-10-27T02:58:30Z"
+++

found while working ~46BECG2. Design 3.3: after the create-only branch push, append a lease event with op, actor, clone id, agent label, branch and observed oid, then push the ledger. Needs a producible lease event kind in frob-ledger (EventBody::Other today).
