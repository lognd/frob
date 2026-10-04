+++
id = "01M2Y1SS19APBW8245KVQJ1WPZ"
title = "land --dry-run skips the unscoped pre-land sweep, so a clean dry run is still refused by the real land on SELFAUDIT001/DOC004/REG findings"
type = "task"
flavour = "ux"
category = "done"
outcome = "done"
priority = "high"
points = 3
reporter = "human"
created = "2026-09-20T00:00:00Z"
updated = "2026-09-20T00:00:02Z"
aliases = ["T-5161"]
labels = ["milestone:0.534.0"]
scope = ["src/frob/tickets/_land.py", "src/frob/tickets/_land_verify.py", "tests/ticket_land_suite/test_land_dry_run_squash_preview.py"]
+++

Measured 2026-09-20: T-4759 dry run clean, real land refused with 9 self-conformance findings (PreLandUnscopedSweepFailed); T-4114 and T-4115 dry run clean, real land refused with SELFAUDIT001 undeclared capability on a new gate file. The agents' brief requires a clean dry run before READY, and the sized 'frob check --files' that would catch these hangs on the sys stage (T-draft-b2e2c562), so every such refusal costs a serial land slot of 5-10 minutes plus a repair round trip. Fix: --dry-run runs the same unscoped pre-land sweep the real land runs (against the staged merge preview, discarding it afterwards) and reports its findings; or, if that is too slow for a dry run, a --dry-run --sweep flag. Found while coordinating lands.
