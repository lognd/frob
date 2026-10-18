+++
id = "01M561J10PTM0B1X2BEZ908DQB"
title = "frob test --base main fails with E-INTERNAL Argument list too long"
type = "bug"
category = "in-progress"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T23:01:10Z"
updated = "2026-10-18T00:38:58Z"
idempotency_key = "frob-test-arg-max"
scope = ["crates/frob-tests/**"]

[[acceptance]]
text = "frob test splits a huge nextest selection into bounded invocations"
bound = false
+++

Observed while landing 2RPYTC8: frob test --base main errored E-INTERNAL 'Argument list too long' (touched set passed on the command line exceeds ARG_MAX). Pass the set via a file or stdin, or chunk it.
