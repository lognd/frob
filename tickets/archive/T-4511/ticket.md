---
id: T-4511
title: .NET BCL standard-library capability map
state: done
kind: feature
origin: agent
created: '2026-09-16'
priority: medium
parent: T-4513
tier: story
sprint: v0.533.0
runs_last: false
milestone: v0.533.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/_capability_registry/_dotnet_bcl.py
- src/frob/vet/_capability_registry/_matrix.py
- tests/vet_suite/test_capability_scan_dotnet_bcl.py
- tests/fixtures/lang/csharp/*.cs
- docs/modules/vet.md
- tests/test_capability_registry.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
scope_changes:
- op: add
  glob: src/frob/vet/_capability_registry/_matrix.py
  reason: wire _dotnet_bcl.py's table into DANGEROUS_OPERATIONS aggregation and add
    one test-per-family with static .cs fixtures asserting via the real scan entry
    point, per T-4511 acceptance criteria
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/vet_suite/test_capability_scan_dotnet_bcl.py
  reason: wire _dotnet_bcl.py's table into DANGEROUS_OPERATIONS aggregation and add
    one test-per-family with static .cs fixtures asserting via the real scan entry
    point, per T-4511 acceptance criteria
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/fixtures/lang/csharp/*.cs
  reason: wire _dotnet_bcl.py's table into DANGEROUS_OPERATIONS aggregation and add
    one test-per-family with static .cs fixtures asserting via the real scan entry
    point, per T-4511 acceptance criteria
  actor: logan
  at: '2026-09-16'
- op: add
  glob: docs/modules/vet.md
  reason: 'matrix.py scope-closure warnings: frob:doc/frob:tests edges on DANGEROUS_OPERATIONS/CAPABILITY_MATRIX_EXCUSES
    the new table''s concat touches'
  actor: logan
  at: '2026-09-16'
- op: add
  glob: tests/test_capability_registry.py
  reason: 'matrix.py scope-closure warnings: frob:doc/frob:tests edges on DANGEROUS_OPERATIONS/CAPABILITY_MATRIX_EXCUSES
    the new table''s concat touches'
  actor: logan
  at: '2026-09-16'
evidence:
- tests/vet_suite/test_capability_scan_dotnet_bcl.py::TestCapabilityScanDotnetBclFamilyMap::test_streamwriter_family_resolves_fs_write
- tests/vet_suite/test_capability_scan_csharp.py::TestCapabilityScanCsharpTaxonomyClosureResolution::test_var_local_type_carries_into_a_later_instance_call
- tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_capabilities[144-csharp-System.Runtime.InteropServices-DllImport
  / Marshal]
- tests/vet_suite/test_capability_scan_dotnet_bcl.py::TestCapabilityScanDotnetBclFamilyMap::test_assembly_load_family_resolves_eval_not_plain_call
designated_repro_test: null
acceptance:
- text: GIVEN a .cs call to File.Open or StreamWriter, WHEN scanned, THEN it maps
    to fs.read or fs.write per the registry, not a generic uncategorized finding.
  evidence:
  - tests/vet_suite/test_capability_scan_dotnet_bcl.py::TestCapabilityScanDotnetBclFamilyMap::test_streamwriter_family_resolves_fs_write
- text: GIVEN a .cs call to HttpClient.GetAsync or a raw Socket, WHEN scanned, THEN
    it maps to net/fetch_url.
  evidence:
  - tests/vet_suite/test_capability_scan_csharp.py::TestCapabilityScanCsharpTaxonomyClosureResolution::test_var_local_type_carries_into_a_later_instance_call
- text: GIVEN a [DllImport] attribute on an extern method, WHEN scanned, THEN it maps
    to ffi.
  evidence:
  - tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_capabilities[144-csharp-System.Runtime.InteropServices-DllImport
    / Marshal]
- text: GIVEN Assembly.Load or a call through System.Reflection, WHEN scanned, THEN
    it maps to eval/ffi, distinct from a plain method call finding.
  evidence:
  - tests/vet_suite/test_capability_scan_dotnet_bcl.py::TestCapabilityScanDotnetBclFamilyMap::test_assembly_load_family_resolves_eval_not_plain_call
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Story: a registry data file mapping .NET Base Class Library APIs to frob capabilities, consumed by the C# resolver from T-4505 (blocked_by it -- the resolver must exist before this map has anywhere to plug in). Modeled on the existing per-language _dangerous_ops_*.py registry files.

Families to cover (each gets its own test):
System.IO -> fs.read/fs.write; System.Net/HttpClient/Sockets -> net/fetch_url; System.Diagnostics.Process -> exec; System.Reflection/Assembly.Load/dynamic -> eval/ffi; DllImport -> ffi; System.Environment -> env; Microsoft.Win32.Registry -> fs.write.

GIVEN a .cs call to File.Open or StreamWriter, WHEN scanned, THEN it maps to fs.read or fs.write per the registry, not a generic uncategorized finding.
GIVEN a .cs call to HttpClient.GetAsync or a raw Socket, WHEN scanned, THEN it maps to net/fetch_url.
GIVEN a [DllImport] attribute on an extern method, WHEN scanned, THEN it maps to ffi.
GIVEN Assembly.Load or a call through System.Reflection, WHEN scanned, THEN it maps to eval/ffi, distinct from a plain method call finding.

## Unblock log
- 2026-09-16: unblocked by T-4505 -- blocker landed as T-4536 (duplicate id T-4505 dropped)