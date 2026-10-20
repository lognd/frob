+++
id = "01M336K74Y9H977T3QJJC6T938"
title = "Automatic per-session token mining for tickets (T-5132 amendment follow-up)"
type = "task"
category = "done"
outcome = "wont-fix"
priority = "medium"
reporter = "human"
created = "2026-09-22T00:00:00Z"
updated = "2026-09-22T00:00:02Z"
aliases = ["T-5278"]
scope = ["src/frob/app/ticket_runner/_lifecycle.py", "src/frob/app/ticket_runner/_close_cmd.py", "src/frob/tickets/_setters.py"]
+++

found while working T-5132: the owner's amendment asked for automatic token-spend recording (session id captured on the lease at start, transcript jsonl summed at close/land) alongside the manual frob ticket tokens path that DID ship this ticket. Left out of T-5132's scope for time -- only the manual setter shipped.

## Drop reason
- 2026-09-22: filed twice; T-5279 is the promoted copy (absorbed by T-5279)
