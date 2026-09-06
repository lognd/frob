---
id: T-3963
title: 'TAINT-IDENT001: store-read value used as identifier'
state: queued
kind: security
origin: agent
created: '2026-09-06'
priority: medium
parent: T-3942
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_taint.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
designated_repro_test: null
acceptance:
- text: given a value read from a store (DB row, cache) later interpolated into a
    table/column-name f-string or expanded via ** into column names, with no allowlist
    check between read and use, when frob check runs, then TAINT-IDENT001 fires
  evidence: []
- text: given the same flow passing through a recognized allowlist/validator call
    first, when frob check runs, then the rule stays quiet
  evidence: []
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
F-176 (T-3942 item 2). VERIFIED: src/frob/vet/_taint.py already implements SEC005, an intra-function/intra-module taint rule, but for a DIFFERENT shape -- a value from a repo-writable state file (.git/.frob) reaching a subprocess argv without validation. It does not track data read from a data STORE (a DB row, cache value) later used as an IDENTIFIER (a table name, column name, or a **values expansion key). No existing rule covers that shape; this is a genuinely new taint kind, not a duplicate of SEC005.

FINDING THIS WOULD HAVE CAUGHT: data read from a store and later used to build an identifier -- e.g. a value pulled from a row and interpolated into a table/column name or expanded via **kwargs into a query's column set -- without passing through an allowlist between the read and the use. This is the identifier-injection analog of classic SQL string-interpolation, but through IDENTIFIER positions rather than value positions, so ordinary parameterized-query safety does not cover it. Proposed rule: TAINT-IDENT001, an intra-function/intra-module flow (mirror SEC005's scope discipline: intra-module first, interprocedural later) from a store-read call to an identifier-construction site (f-string into a table/column name, or a **mapping expansion used as column/field names), flagging any such flow with no allowlist check in between.
