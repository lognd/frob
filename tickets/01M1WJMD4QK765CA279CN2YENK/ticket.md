+++
id = "01M1WJMD4QK765CA279CN2YENK"
title = "a test bound as evidence that SKIPPED in the measured run must be reported with its skip reason recorded in the ledger"
type = "bug"
category = "triage"
priority = "medium"
parent = "01M1WJMD174K541FJR85BEHX2T"
reporter = "agent"
created = "2026-09-07T00:00:00Z"
updated = "2026-10-04T21:09:48Z"
aliases = ["T-4247"]
labels = ["milestone:1.1.0", "v1-cluster:C2"]
scope = ["src/frob/gates"]

[[links]]
kind = "duplicates"
target = "01M1T07NW78MGWRF7HZQMPSRAV"
+++

Consumer F-326/M2-8: a round-1 rule (a test bound as evidence that SKIPPED in the measured run is reported, not silently counted) is still unimplemented; this is its second sighting, strengthened -- the skip reason itself (e.g. an env-var skip hatch) must be recorded WITH the evidence, so the skip condition is visible in the ledger rather than only in scrolled-past test output. Fixture-testable: YES, frob's own evidence/test-collection mechanism.
