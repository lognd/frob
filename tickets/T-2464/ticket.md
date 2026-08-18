---
id: T-2464
title: Network dangerous-ops needles do not distinguish read vs write HTTP/DB verbs
state: done
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
- tests/test_capability_registry.py
- docs/modules/vet.md
- src/frob/strata/_selfconform.py
- src/frob/strata/_threat_catalog_benign.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_capability_registry.py
  reason: add fire/no-fire fixture tests for the new net-mutate kind, mirroring this
    file's own existing per-cell drift-lock convention
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/vet.md
  reason: CAPABILITY_KINDS' doc anchor lives here (not docs/strata/**); update the
    read/write-mode-split description for the new net-mutate kind
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_selfconform.py
  reason: net-mutate is a new CAPABILITY_KINDS entry with no _KIND_MAP tier-2 analog
    (by design, T-2464's own scanner-only decision); _EXTENDED_KINDS' own drift-lock
    test requires it be listed here or SYS100 loses coverage for it
  actor: logan
  at: '2026-08-18'
- op: add
  glob: src/frob/strata/_threat_catalog_benign.py
  reason: net-mutate (T-2464's new capability kind) needs a THREAT002 catalog disposition
    the same way fs-read/fs got one when they were introduced -- no CWE_CATALOG entry
    targets a network mutation as a sink on its own yet (that mapping is real follow-up
    work), so it needs the same disclosed benign excuse fs-read/fs already carry
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_capability_registry.py::TestNetMutateVerbSplit::test_requests_post_reports_net_mutate_and_net_connect
- tests/test_capability_registry.py::TestNetMutateVerbSplit::test_httpx_delete_reports_net_mutate
- tests/test_capability_registry.py::TestNetMutateVerbSplit::test_requests_get_only_does_not_report_net_mutate
- tests/test_capability_registry.py::TestNetMutateVerbSplit::test_httpx_get_only_does_not_report_net_mutate
- tests/test_capability_registry.py::TestNetMutateVerbSplit::test_session_instance_method_gap_is_unchanged
designated_repro_test: null
acceptance:
- text: Given a module calling requests.post(/put(/delete(/patch( or httpx.post(/put(/delete(/patch(,
    when the dangerous-ops scanner runs, then it reports a NEW net-mutate capability
    signal in addition to the existing net-connect signal, so a mutating HTTP call
    is distinguishable from a read-only one.
  evidence:
  - tests/test_capability_registry.py::TestNetMutateVerbSplit::test_requests_post_reports_net_mutate_and_net_connect
  - tests/test_capability_registry.py::TestNetMutateVerbSplit::test_httpx_delete_reports_net_mutate
- text: Given a module calling requests.get(/head(/options( or httpx.get(/head(/options(
    only (no mutating verb), when the scanner runs, then net-mutate is NOT reported
    for that module, proving the split does not over-fire on read-only usage.
  evidence:
  - tests/test_capability_registry.py::TestNetMutateVerbSplit::test_requests_get_only_does_not_report_net_mutate
  - tests/test_capability_registry.py::TestNetMutateVerbSplit::test_httpx_get_only_does_not_report_net_mutate
- text: Given the EXISTING coarse requests./httpx./aiohttp. needles, when this ticket
    lands, then they are UNCHANGED and still fire exactly as before -- this is an
    additive precision improvement, never a recall regression on the existing net-connect
    signal.
  evidence:
  - tests/test_capability_registry.py::TestNetMutateVerbSplit::test_session_instance_method_gap_is_unchanged
- text: Given the libraries this ticket does NOT split (aiohttp instance-method verbs,
    boto3's per-service verb methods, asyncpg/SQL execute-vs-fetch ambiguity, http.client,
    ftplib, smtplib), when the Done report is written, then each is named with a one-line
    reason it was out of scope, and a follow-up ticket is filed for the highest-value
    one rather than silently dropped.
  evidence:
  - tests/test_capability_registry.py::TestNetMutateVerbSplit::test_session_instance_method_gap_is_unchanged
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