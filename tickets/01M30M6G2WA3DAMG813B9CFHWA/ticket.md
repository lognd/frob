+++
id = "01M30M6G2WA3DAMG813B9CFHWA"
title = "Wire _rapid_caller_dependents to public_caller_dependent_files"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5212"]
scope = ["src/frob/app/ticket_runner/_land_cmd.py", "tests/unit/test_check_scoped_files.py"]
+++

found while working T-4560: build_call_graph gained an opt-in include_public_callees flag and frob.graph.affects gained public_caller_dependent_files, but _land_cmd.py's _rapid_caller_dependents (out of T-4560's declared/implicit scope) still only calls the private-only caller_dependent_files. Wire it to also call public_caller_dependent_files (or replace the call) so the rapid land's --files dependents scope actually picks up callers of a changed PUBLIC symbol end to end.
