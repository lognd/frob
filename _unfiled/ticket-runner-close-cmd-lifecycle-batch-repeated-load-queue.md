+++
id = "01M30M6G2FG0TG3KCJWZ3Q2521"
title = "ticket_runner _close_cmd/_lifecycle: batch repeated load_queue calls (M4/M5)"
type = "bug"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5199"]
scope = ["src/frob/app/ticket_runner/_close_cmd.py", "src/frob/app/ticket_runner/_lifecycle.py"]
+++

found while working T-5135 perf audit (M4/M5, lower priority, not fixed there to stay in the H2-H5/M7 fix order the ticket specified): frob ticket work --cluster and frob ticket close each call load_queue multiple times (four loads measured) instead of loading once and threading the queue through. Batch to one load_queue per command invocation.

frob:no-behavior-change reason="batches redundant load_queue calls (M4/M5 perf follow-up); observable behavior of close/work --cluster is unchanged, only I/O count is reduced"
