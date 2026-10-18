+++
id = "01M561J10PTM0B1X2BEZ908DQB"
title = "frob test --base main fails with E-INTERNAL Argument list too long"
type = "bug"
category = "todo"
priority = "medium"
points = 2
reporter = "lognd"
created = "2026-10-17T23:01:10Z"
updated = "2026-10-18T00:34:01Z"
idempotency_key = "frob-test-arg-max"
scope = ["crates/frob-tests/**"]
+++

Observed while landing 2RPYTC8: frob test --base main errored E-INTERNAL 'Argument list too long' (touched set passed on the command line exceeds ARG_MAX). Pass the set via a file or stdin, or chunk it.
