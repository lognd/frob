+++
id = "01M2Y1SS11G9KFME2MGJHBNG21"
title = "frob check: the sys stage takes 1268s of a 1900s root check and --files scoping does not skip it, so every sized agent check hangs past 10 minutes under fleet load"
type = "bug"
category = "todo"
priority = "medium"
reporter = "human"
created = "2026-09-20T00:00:00Z"
updated = "2026-10-04T22:22:23Z"
aliases = ["T-5153"]
labels = ["v1-cluster:G1", "triage:accepted"]
scope = ["src/frob/gates/_sys.py", "src/frob/check/_python.py"]
+++

Measured 2026-09-20 on the root check: gate-summary timings sys=1267.71s, affect_drift=337.77s, wire=260.50s, tickets=248.26s, archgate=54.46s; total wall time about 32 minutes. Five implementer agents in the same evening reported 'frob check --files <2-4 files>' (also with --only gates) hanging past a 10-minute cap on 2-3 consecutive attempts and gave up, so the pre-land sized check is unmeasurable under fleet load and lands are refused later by the unscoped pre-land sweep instead (T-4759 today: 9 self-conformance findings a clean dry run never showed). Fix: (1) --files must scope or skip the sys stage (the strata design-quality self-audit is not a per-file check; cache its result keyed on the strata files' digest and reuse when they are untouched); (2) profile the sys stage itself, 21 minutes for 614k rule fires is the N+1 shape T-5135 catalogues; (3) frob check prints per-stage elapsed time as it goes so a 20-minute stage is visible instead of read as a hang. Found while coordinating the warning drain.
