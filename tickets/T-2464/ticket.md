---
id: T-2464
title: Network dangerous-ops needles do not distinguish read vs write HTTP/DB verbs
state: queued
kind: security
origin: human
created: '2026-08-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/vet/_capability_registry/**
- docs/strata/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Found auditing the python dangerous-ops table for T-2457 ("audit the rest
of the table for the same any-needle-present imprecision").

The `net-connect` family's per-library needles (`requests.`, `httpx.`,
`aiohttp.`, `asyncpg.connect(`, `boto3.client(`/`resource(`, `smtplib.`,
`ftplib.`, `socket.`, `http.client`, etc.) fire on ANY call into that
library, with no distinction between a read-only outbound call (a GET,
a SELECT-style read) and a state-changing one (a POST/PUT/DELETE, an
INSERT/UPDATE). This is a real under-match in the network capability
model: a module making only GET requests is declared the identical
`net-connect` capability as one making POST/DELETE requests, so the
capability model cannot distinguish "reads a remote resource" from
"mutates a remote resource" for any of these libraries.

This is a DIFFERENT axis from T-2457's own fix (T-2457 was read-vs-write
MODE on a single call, `open(mode=...)`; this is read-vs-write HTTP/DB
VERB across a whole client library's call surface, which the
`_capability_modes.py` FAMILY_MODES vocabulary does not model at all --
`net`'s own mode split is connect-vs-listen, i.e. socket ROLE, not
read-vs-write). Filing separately rather than folding into T-2457 per
that ticket's own "file what you do not fix" instruction.

Scope note for whoever picks this up: this is more consequential to get
right than T-2457's fs.write fix, per T-2457's own framing -- a false
network-write declaration (or a missed one) has bigger security-
reasoning blast radius than a false fs-write. Needs its own design
decision on whether a verb-aware split is even tractable at the
needle-table level (a `requests.get(` vs `requests.post(` split is easy;
a `boto3.client("s3").put_object(...)` chained-call verb is not visible
to a flat needle) before committing to an implementation shape.
