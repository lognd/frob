---
id: T-2479
title: boto3/aiohttp/asyncpg mutating-verb split not covered by T-2464's net-mutate
  scanner signal
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
- src/frob/vet/_capability_python.py
- tests/test_capability_registry.py
- docs/modules/vet.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: tests/test_capability_registry.py
  reason: T-2479 adds boto3 service-binding resolution tests to this file (TestBoto3ServiceBindingResolution)
  actor: logan
  at: '2026-08-18'
- op: add
  glob: docs/modules/vet.md
  reason: documenting the boto3 net-mutate binding-resolver extension in the net-mutate
    capability description
  actor: logan
  at: '2026-08-18'
evidence:
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_client_put_object_reports_net_mutate_and_net_connect
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_resource_delete_object_reports_net_mutate
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_get_object_does_not_report_net_mutate
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_dynamodb_put_item_reports_net_mutate
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_iam_create_user_reports_net_mutate
- tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_non_literal_service_name_does_not_resolve
designated_repro_test: tests/test_capability_registry.py::TestBoto3ServiceBindingResolution::test_s3_client_put_object_reports_net_mutate_and_net_connect
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 07085bf811a0a9342ee47fffaa3a2982902a30dd
---
T-2464 added a `net-mutate` scanner-only capability signal, split from
the coarse `net-connect` needle, for exactly TWO libraries' module-level
convenience calls: `requests.post/put/delete/patch(` and `httpx.post/
put/delete/patch(`. It deliberately did NOT cover several other
libraries already in the dangerous-ops table's `net-connect` family,
each with its own reason (T-2464's Done report):

  - `aiohttp` -- the real-world idiom is `session.post(url)` on a
    `ClientSession` instance, never a module-level `aiohttp.post(url)`
    call. A bare `.post(`/`.put(` method-name needle (no library prefix
    to anchor on) would false-positive on any object's unrelated method
    of the same name -- the same reason `requests.Session().post(...)`
    and `httpx.Client().post(...)` are ALSO not covered by T-2464 (a
    disclosed gap shared with requests/httpx, not aiohttp-specific).
  - `boto3` -- HIGHEST VALUE, HARDEST TO COVER. `boto3.client("s3").
    put_object(...)`/`.delete_object(...)`/`.create_bucket(...)` etc are
    genuinely mutating cloud-infrastructure operations (create/delete
    buckets, write objects, IAM changes) -- arguably the single most
    consequential class this whole audit chain (T-2457 -> T-2464) has
    touched, since a false negative here means a real cloud-mutation
    capability goes completely unmodeled. NOT tractable at the flat-
    needle level the way requests/httpx are: boto3's mutating method
    names are PER-SERVICE (S3's `put_object`/`delete_object` vs
    DynamoDB's `put_item`/`delete_item` vs IAM's `create_user`/
    `delete_user`, etc.) and always called on a `.client("service")`/
    `.resource("service")` object with no library-name prefix visible at
    the call site -- needs either a per-service verb table (large
    survey) or a binding-aware resolution pass (T-0328's existing
    import/binding resolver already tracks `boto3.client(...)` call
    sites; extending it to also record the service-name STRING argument
    and join against a per-service verb table is the realistic shape,
    not a flat needle).
  - `asyncpg` -- `.execute(`/`.fetch(`/`.fetchval(`/`.fetchrow(` do split
    cleanly by METHOD NAME (execute is the write-shaped one), but the
    actual read/write reality depends on the SQL STRING passed to
    `execute()` (which can itself be a SELECT wrapped in a transaction,
    or -- more commonly -- an INSERT/UPDATE/DELETE/DDL statement) --
    same inherent SQL-string ambiguity the existing `sql` capability
    kind (sqlite3/sqlalchemy string-formatted-SQL entries) already lives
    with; not attempted here.
  - `http.client`, `ftplib`, `smtplib`, `socket` -- no clean verb-shaped
    convenience-function idiom the way requests/httpx have; `smtplib` in
    particular is arguably ALWAYS mutating (sending mail has no read-only
    mode) and might deserve reclassifying its OWN net-connect entry to
    net-mutate directly rather than splitting it -- a judgment call left
    to whoever picks this up, not decided here.

RECOMMENDATION for whoever takes this: start with `boto3` (highest
value) via the binding-resolver extension shape above, not a flat
needle -- a flat `boto3.` needle survey would either miss the reads
(`get_object`) that also flow through `.client(...)` objects or produce
enough false positives on this repo's own `frob.vet._capability_python`-
style resolver work to need real design time. Do not attempt a
one-line needle-table fix for boto3; it will not hold up.