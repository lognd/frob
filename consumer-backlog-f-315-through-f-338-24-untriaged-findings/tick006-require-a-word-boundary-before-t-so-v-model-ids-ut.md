+++
id = "01M1WJMD3HPBMEHE6Q2T3FTNHH"
title = "TICK006: require a word boundary before T- so V-model ids (UT-/SIT-/SUBT-/CT-nnnn) are not misread as phantom ticket filings"
type = "bug"
category = "done"
outcome = "duplicate"
priority = "medium"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:02:17Z"
aliases = ["T-4209"]
labels = ["milestone:1.1.0", "v1-cluster:B3d"]
scope = ["src/frob/tickets"]

[[links]]
kind = "duplicates"
target = "01M1T07NXF3MCHHKJ1R0G7VZJ5"
+++

Consumer F-322 (T-4135). The ticket-id regex matches inside UT-1516, so a done report naming spec rows (COMP-1514, UT-1516) is reported as claiming a phantom T-1516 filing. Require a word boundary before T-, and read 'filed' claims only from the Filed: line, not anywhere in the report. Fixture-testable: YES.
