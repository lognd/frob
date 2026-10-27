+++
id = "01M1J91D0SVZQY0PFXD0SB55DP"
title = "claim divergence from T-0013's Done report (2 identit(ies))"
type = "bug"
category = "done"
outcome = "wont-fix"
priority = "high"
reporter = "agent"
created = "2026-09-03T00:00:00Z"
updated = "2026-10-27T00:53:30Z"
aliases = ["crunk:T-0025"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["tests/integration/test_int_05_fixes_pipeline.py", "tests/integration/test_int_06_report.py"]
+++

Deferred post-land claim-divergence check (T-2938) found that T-0013's Done report's captured gate-state claim (T-0754) no longer holds against the tree this sweep measured at d3b9a63d15cf -- reusing this sweep's own unscoped `frob check` result as both the count and the per-finding identity source, no second spawn.

Diverging (rule, file) identit(ies):
- TEST006: tests/integration/test_int_05_fixes_pipeline.py
- WIRE002: tests/integration/test_int_06_report.py

This is a report-honesty finding, not necessarily bad content on main -- the land already published; the tree itself was already covered by this land's own pre-land check plus this sweep's unscoped post-land measurement. Determine whether the claim was a stale/incorrect capture or a real self-introduced regression, fix or refresh accordingly, then dispose the quarantine entry this ticket raised.

## Drop reason
- 2026-09-03: duplicate: both findings (TEST006 int-05, WIRE002 int-06) were triaged, disposed, and fixed under T-0026
