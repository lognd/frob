---
id: T-draft-35c8d680
title: Wire a C# capability resolver into _capability_scan.py
state: in-progress
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-draft-37a6a15c
tier: ticket
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_csharp.py
- src/frob/vet/_capability_scan.py
- src/frob/vet/_capability.py
- src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
- tests/vet_suite/test_capability_scan_csharp.py
- tests/fixtures/lang/csharp/plain_using_fs_write.cs
- tests/fixtures/lang/csharp/alias_using_fs_write.cs
- tests/fixtures/lang/csharp/static_using_console.cs
- tests/fixtures/lang/csharp/var_local_httpclient.cs
- tests/fixtures/lang/csharp/no_dangerous_apis.cs
- tests/fixtures/lang/csharp/combined_static_and_namespace.cs
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability.py
  reason: extend the same per-language elif dispatch chain _capability_scan.py wires
    (mirrors kotlin's identical _extra_kt_binding_operations wiring already present
    there)
  actor: logan
  at: '2026-09-16'
- op: add
  glob: src/frob/vet/_capability_registry/_dangerous_ops_bash_csharp.py
  reason: extend the csharp needle table -- File.WriteAllText/AppendAllText/WriteAllBytes
    was missing from fs-write entirely, needed for the resolver's own acceptance criterion
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/vet_suite/test_capability_scan_csharp.py
  reason: new test file, mirrors tests/vet_suite/test_capability_scan_kotlin.py's
    shape, one per language
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/csharp/plain_using_fs_write.cs
  reason: static fixture file for the csharp resolver's own test suite -- checked-in,
    no fs.write inside the test itself, avoiding a design/frob.strata via-list edit
    (that file's ticket lease is held elsewhere right now)
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/csharp/alias_using_fs_write.cs
  reason: static fixture file for the csharp resolver's own test suite -- checked-in,
    no fs.write inside the test itself, avoiding a design/frob.strata via-list edit
    (that file's ticket lease is held elsewhere right now)
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/csharp/static_using_console.cs
  reason: static fixture file for the csharp resolver's own test suite -- checked-in,
    no fs.write inside the test itself, avoiding a design/frob.strata via-list edit
    (that file's ticket lease is held elsewhere right now)
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/csharp/var_local_httpclient.cs
  reason: static fixture file for the csharp resolver's own test suite -- checked-in,
    no fs.write inside the test itself, avoiding a design/frob.strata via-list edit
    (that file's ticket lease is held elsewhere right now)
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/csharp/no_dangerous_apis.cs
  reason: static fixture file for the csharp resolver's own test suite -- checked-in,
    no fs.write inside the test itself, avoiding a design/frob.strata via-list edit
    (that file's ticket lease is held elsewhere right now)
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/csharp/combined_static_and_namespace.cs
  reason: 'regression fixture: using static + using System.IO together must not let
    the static-using fallback hijack a member-access base'
  actor: logan
  at: '2026-09-16'
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Add src/frob/vet/_capability_csharp.py (binding-aware resolver, modeled on _capability_c.py/_capability_kotlin.py) that resolves 'using' directives (including aliases and 'using static'), fully-qualified calls, and namespace imports to capability findings, replacing raw-needle-only matching from _capability_registry/_dangerous_ops_bash_csharp.py. Wire it into src/frob/vet/_capability_scan.py's per-language import/dispatch table alongside the other five languages.

GIVEN a .cs file with 'using System.IO;' and a File.WriteAllText call, WHEN frob vet scans it, THEN it reports fs.write with the resolved binding, not just a raw needle match.
GIVEN 'using IO = System.IO;' (an alias) and a call through the alias, WHEN scanned, THEN the resolver follows the alias to the same capability.
GIVEN 'using static System.Console;' and a bare WriteLine call, WHEN scanned, THEN the static-using resolves to the correct fully-qualified symbol.
GIVEN a .cs file with no dangerous APIs, WHEN scanned, THEN zero findings (no false positives from the wired resolver).