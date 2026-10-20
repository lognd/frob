+++
id = "01M5DBVTJ0AFFN3BAWEVE5VTE3"
title = "Retry an unpublished claim branch or missing ledger push on sync"
type = "task"
category = "todo"
priority = "medium"
reporter = "lognd"
created = "2026-10-20T19:15:58Z"
updated = "2026-10-20T19:15:58Z"
+++

found while working ~46BECG2. W-CLAIM-UNPUBLISHED is emitted by work; sync (refresh) must retry the create-only push and ledger push.
