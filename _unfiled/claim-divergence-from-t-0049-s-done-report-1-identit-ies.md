+++
id = "01M1QDTV1Q2SZAD2XDA09V9QBJ"
title = "claim divergence from T-0049's Done report (1 identit(ies))"
type = "bug"
category = "done"
outcome = "done"
priority = "high"
reporter = "agent"
created = "2026-09-05T00:00:00Z"
updated = "2026-10-27T00:53:33Z"
aliases = ["crunk:T-0055"]
labels = ["component:crunk", "source:crunk", "imported:crunk"]
scope = ["tests/system/test_e2e_18_19_schema.py"]
+++

Deferred post-land claim-divergence check (T-2938) found that T-0049's Done report's captured gate-state claim (T-0754) no longer holds against the tree this sweep measured at 5ed891a57ea8 -- reusing this sweep's own unscoped `frob check` result as both the count and the per-finding identity source, no second spawn.

Diverging (rule, file) identit(ies):
- TEST006: tests/system/test_e2e_18_19_schema.py

This is a report-honesty finding, not necessarily bad content on main -- the land already published; the tree itself was already covered by this land's own pre-land check plus this sweep's unscoped post-land measurement. Determine whether the claim was a stale/incorrect capture or a real self-introduced regression, fix or refresh accordingly, then dispose the quarantine entry this ticket raised.
