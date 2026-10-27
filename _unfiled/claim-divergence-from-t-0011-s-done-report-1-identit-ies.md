+++
id = "01M1J91D0J0EYPQ0DY4AVEVZWS"
title = "claim divergence from T-0011's Done report (1 identit(ies))"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "agent"
created = "2026-09-03T00:00:00Z"
updated = "2026-10-27T00:53:28Z"
aliases = ["crunk:T-0018"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["tests/unit/test_scaffold.py", "frob-coverage.lock.json", "coverage.xml"]
+++

Deferred post-land claim-divergence check (T-2938) found that T-0011's Done report's captured gate-state claim (T-0754) no longer holds against the tree this sweep measured at 55a14f656c2f -- reusing this sweep's own unscoped `frob check` result as both the count and the per-finding identity source, no second spawn.

Diverging (rule, file) identit(ies):
- TEST006: tests/unit/test_scaffold.py

This is a report-honesty finding, not necessarily bad content on main -- the land already published; the tree itself was already covered by this land's own pre-land check plus this sweep's unscoped post-land measurement. Determine whether the claim was a stale/incorrect capture or a real self-introduced regression, fix or refresh accordingly, then dispose the quarantine entry this ticket raised.
