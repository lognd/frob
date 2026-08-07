---
id: T-1610
title: 'Docs completeness sweep: enumerate the repo''s real surface and document every
  gap'
state: done
kind: docs
origin: human
created: '2026-08-05'
priority: medium
parent: T-1609
tier: ticket
sprint: null
scope:
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches
- cmd:grep -q 'docs-completeness-2026-08-06' docs/index.md && test -s docs/audits/docs-completeness-2026-08-06.md
  exit=0 sha256=e3b0c44298fc
designated_repro_test: null
threat: null
component: null
---
Scan the entire repository for anything true about it that is not documented, and amend the docs to cover it.

Scope is the whole repo, not just docs/: every module, every gate rule, every CLI verb and flag, every config key in frob.toml, every environment variable, every file format frob reads or writes, and every workflow an agent or user is expected to follow.

Method matters more than volume. Enumerate the surface FIRST from the code (the CLI parser tree, the gate rule registry, the config model, the directive DSL grammar), then diff that enumeration against what docs/ actually covers. A prose read-through will miss exactly the things that have been missing all along; a mechanical enumeration will not.

Record every gap found in a durable list -- the audit child consumes it, and it is the input to that audit, not a byproduct. For each gap note what it is, where it should have been documented, and roughly how long it appears to have been missing (git blame on the undocumented symbol).

Do NOT fix detector gaps here. Finding out why frob failed to catch each of these is the next ticket's job, and mixing the two loses the evidence.