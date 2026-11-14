+++
id = "01M7DA6EKC0R7A2F5CCAG2MXS9"
title = "grimble-websec ROUTE: adapter-based route tables, guards and Unresolved reporting (follow-up of DHW6K49)"
type = "task"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-11-14T15:18:12Z"
updated = "2026-11-14T17:22:17Z"
labels = ["no-story"]
scope = ["packs/grimble-websec/rules/route/ROUTE105.grl", "packs/grimble-websec/rules/route/ROUTE107.grl"]
+++

DHW6K49 landed text-based ROUTE105/ROUTE106 for Flask. Remaining: framework adapter route tables and guards, real Unresolved for unsupported frameworks, custom auth decorators, other handler-exposure shapes such as return str(e).
