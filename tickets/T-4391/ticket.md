---
id: T-4391
title: DRIFT001 body digest is CRLF-sensitive, false-fires on Windows checkouts
state: in-progress
kind: bug
origin: human
created: '2026-09-10'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/graph/digest.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: set
  reason: restore body lost to a heredoc write race
  actor: logan
  at: '2026-09-10'
  old_length: 0
  new_length: 1340
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Windows-only CI (run 34415921529, head 7ad69b30f): `[gate:DRIFT] src/frob/tickets/_leases.py:3773  DRIFT001  DRIFT001: src/frob/tickets/_leases.py::read_all_leases (body) digest moved since ack (9 dependent(s)); run: frob ack src/frob/tickets/_leases.py::read_all_leases`

Ubuntu and macOS pass the same gate on the same commit. Mechanism: DRIFT001's body digest (`frob.graph.digest._digest_body`) hashes `symbol.body_tokens`, tree-sitter LEAF tokens whose text is captured verbatim from the source file's bytes. When a leaf token spans a multi-line string/docstring, its captured text includes the raw line-ending bytes between the quotes. Windows runners check the repo out with CRLF (`core.autocrlf`); Linux/macOS check out LF. If `read_all_leases`'s docstring/body contains an embedded multi-line string, its token text differs by embedded `\r` bytes ONLY on Windows, so the digest differs from the LF digest that was acked -- a false "digest moved since ack" that only Windows can ever see.

Fix the digest computation (or the token-text extraction it consumes) to normalize line endings (`\r\n`/`\r` -> `\n`) before hashing, so `sig`/`body`/`doc` digests are line-ending independent. Add a test that plants a CRLF-encoded copy of a symbol's source on Linux and asserts its digest equals the LF version's digest (no DRIFT001 finding).
