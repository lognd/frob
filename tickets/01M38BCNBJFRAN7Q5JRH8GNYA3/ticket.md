+++
id = "01M38BCNBJFRAN7Q5JRH8GNYA3"
title = "WEBSEC317 + T-5141 secret-pattern reuse for WEBSEC316"
type = "task"
category = "triage"
priority = "medium"
reporter = "human"
created = "2026-09-24T00:00:00Z"
updated = "2026-09-24T00:00:00Z"
aliases = ["T-5490"]
labels = ["v1-cluster:B2", "area:grimble"]
scope = ["src/frob/webapp/_websec_debug_config.py"]
+++

found while working T-5329: WEBSEC310-316 used 7 of the reserved WEBSEC310-317 8-id block; WEBSEC317 (default-creds cross-refs SEC001-003 per ticket body, no distinct check defined) is left unimplemented. Also, WEBSEC316's secret-literal pattern table is a small self-contained copy pending T-5141's own reusable secret-pattern table landing -- fold WEBSEC316 onto that table once it exists.
