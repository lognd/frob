+++
id = "01M2VFD1FQYY88WZR8D0F9VTPX"
title = "instrument the silent ~111s land phase between rapid --files scoping and worktree auto-sync with phase-transition logging"
type = "task"
category = "done"
outcome = "done"
priority = "medium"
reporter = "human"
created = "2026-09-19T00:00:00Z"
updated = "2026-09-19T00:00:02Z"
aliases = ["T-4599"]
scope = ["src/frob/app/ticket_runner/_land_cmd.py", "tests/unit/test_land_phase_elapsed_logging.py", "tests/unit/test_land_auto_rebase.py", "tests/unit/test_land_cmd_drain_wiring.py"]
+++

T-4599 why-file finding: T-3233's successful land (08:38:51-08:42:02, /tmp/land-T-3233.log) shows NO phase-transition log at all between [+30.7s] (rapid --files scoped to 9 files) and [+141.6s] (auto-synced worktree onto dev) -- a single 110.9s silent block, 58% of the land's total ~191s wall time, covering commit assembly/claims-reverify/git-add-fallback/REL001-bump/rapid-sweep-dispatch with nothing to attribute it to a specific step. Add _LandPhaseElapsedFilter-covered phase-transition log lines through that span (mirroring T-4417's existing coverage of the earlier phases) so the dominant land-time cost is measurable, not just noticed after the fact.
