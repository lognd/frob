+++
id = "01M30M6G4B4Z17ESRRRJXY5TCB"
title = "frob ticket land --drain crashes after each landed entry: _LandReportShim lacks the ticket_id that _print_land_proof reads"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "human"
created = "2026-09-21T00:00:00Z"
updated = "2026-09-21T00:00:02Z"
aliases = ["T-5259"]
scope = ["src/frob/app/ticket_runner/_land_cmd.py", "tests/unit/test_land_default_queue.py"]
+++

drain_next lands an entry then _print_land_proof reads report.ticket_id to look up _LAST_CLAIMS_OUTCOME / _LAST_ORPHAN_EVIDENCE_OUTCOME / _LAST_BUDGET_DEFERRALS, but _LandReportShim (constructed in _land_cmd.py to stand in for the real LandReport since QueueEntry only carries commit_sha and final_id) never sets ticket_id, so it raises AttributeError after every landed entry and a multi-entry drain lands one ticket per invocation instead of draining the whole queue.
