## Done report

Registry data module src/frob/vet/_capability_registry/_dotnet_bcl.py maps
.NET BCL families to frob capabilities: System.IO Directory (fs-read/
fs-write), FileStream/StreamReader/StreamWriter (fs-read/fs-write),
System.Net.Sockets.Dns (net-connect), System.Reflection Assembly.Load/
LoadFrom/LoadFile, Activator.CreateInstance(typeName), Type.GetType
(typeName) (all eval), Microsoft.Win32.Registry.SetValue/RegistryKey.
SetValue/Registry.CreateSubKey (fs-write), System.Data SqlCommand/
DbCommand.Execute* (sql), and DataContractSerializer.ReadObject/
JsonSerializer.Deserialize (deserialize) -- 12 needle entries across 9
_DangerousOperation rows.

Deliberately does NOT re-declare Process.Start/HttpClient/WebClient/
File.WriteAllText/ReadAllText/Environment.Get-SetEnvironmentVariable/
DllImport/Marshal/TcpClient/Socket/TcpListener/HttpListener/
BinaryFormatter -- those already pattern in
_dangerous_ops_bash_csharp.py from T-4536; a second table claiming the
same needle would be the exact duplication the "NO DUPLICATION"
principle forbids.

Wired into DANGEROUS_OPERATIONS via _matrix.py (scope-expanded: T-4511
was declared scope-only over _dotnet_bcl.py, but the aggregation edge and
the scope-closure frob:doc/frob:tests warnings on DANGEROUS_OPERATIONS/
CAPABILITY_MATRIX_EXCUSES required also touching _matrix.py,
tests/test_capability_registry.py, docs/modules/vet.md,
tests/vet_suite/test_capability_scan_dotnet_bcl.py, and
tests/fixtures/lang/csharp/*.cs -- all added via `frob ticket scope --add`
with reasons before editing). Removed the now-stale
CAPABILITY_MATRIX_EXCUSES(kind="sql", language="csharp") entry: the new
SqlCommand/DbCommand pattern makes that cell no longer excusable, and
TestMatrixExhaustiveness.test_no_cell_is_both_patterned_and_excused
caught it immediately when I left it in place. The Dns entry uses
"net-connect", not the ticket's literal "net" kind, for the same reason
(csharp's "net" cell carries a generated _STRUCTURAL_KIND_REASONS excuse
asserting no csharp pattern claims the bare kind any more; net-connect is
the TcpClient/Socket-sibling precise kind and does not collide).

Ten new tests in tests/vet_suite/test_capability_scan_dotnet_bcl.py, one
per family, each against a static checked-in .cs fixture under
tests/fixtures/lang/csharp/, asserting the resolved capability via the
real scan entry point frob.vet._capability.scan_file_capabilities (no
tmp_path fixtures). All 10 pass; the full registry+csharp-scoped
suite (tests/vet_suite/test_capability_scan_csharp.py +
tests/test_capability_registry.py + the new file) is 652 passed, 0
failed, including the 75 csharp cases of the pre-existing
TestPerOperationFireFixtures parametrization (which automatically covers
every DANGEROUS_OPERATIONS entry, my 12 new ones included -- confirmed by
filtering to "csharp and DllImport"/full csharp run).

ruff check and ruff format --check are clean on the 3 touched
non-fixture files (one file needed `ruff format` applied, now clean).

`frob check --only gates --skip-tests --files <touched>` did NOT
complete inside the 540-595s foreground budget across 4 attempts, always
stalling/timing out at a different late-stage gate each run (once during
T-0745 reachability, once during a temp-file (.json/.yml/.md/.toml/.lock)
parsing gate, once right after lexical_selfcheck_gate) -- `ps aux`
confirms heavy concurrent fleet load at the same time (a T-3613 land's own
`frob check --ticket` running >7 CPU-minutes, plus 3 forkserver workers,
plus a T-4512 agent's own scope call), consistent with this being fleet
contention rather than anything in my change: every partial run I
captured showed 0 violations naming _dotnet_bcl.py, the new test file, or
my _matrix.py edit, and the affects() index for
_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS shows 10 test(s)/0 dependent(s)/0
doc(s) (no COV/DRIFT flag raised against it in any partial run).
Acceptance criteria are free text; registered via `frob ticket accept`
before binding evidence per the brief amendment.

### Changed
```
 src/frob/vet/_capability_registry/_dotnet_bcl.py   | 214 +++++++++++++++++++++
 src/frob/vet/_capability_registry/_matrix.py       |  11 +-
 .../dotnet_bcl_activator_createinstance_eval.cs    |  12 ++
 .../lang/csharp/dotnet_bcl_assembly_load_eval.cs   |  12 ++
 .../lang/csharp/dotnet_bcl_directory_fs_write.cs   |  12 ++
 tests/fixtures/lang/csharp/dotnet_bcl_dns_net.cs   |  12 ++
 .../dotnet_bcl_jsonserializer_deserialize.cs       |  12 ++
 .../lang/csharp/dotnet_bcl_registry_fs_write.cs    |  12 ++
 .../lang/csharp/dotnet_bcl_sqlcommand_sql.cs       |  13 ++
 .../lang/csharp/dotnet_bcl_streamreader_fs_read.cs |  13 ++
 .../csharp/dotnet_bcl_streamwriter_fs_write.cs     |  13 ++
 .../lang/csharp/dotnet_bcl_type_gettype_eval.cs    |  12 ++
 tests/vet_suite/test_capability_scan_dotnet_bcl.py | 109 +++++++++++
 tickets/T-4511/ticket.md                           |  19 +-
 14 files changed, 467 insertions(+), 9 deletions(-)
```

### Evidence
- `tests/vet_suite/test_capability_scan_dotnet_bcl.py::TestCapabilityScanDotnetBclFamilyMap::test_streamwriter_family_resolves_fs_write` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_capability_scan_csharp.py::TestCapabilityScanCsharpTaxonomyClosureResolution::test_var_local_type_carries_into_a_later_instance_call` (pytest node id, verified passing when recorded)
- `tests/test_capability_registry.py::TestPerOperationFireFixtures::test_entry_fires_scan_file_capabilities[144-csharp-System.Runtime.InteropServices-DllImport / Marshal]` (pytest node id, verified passing when recorded)
- `tests/vet_suite/test_capability_scan_dotnet_bcl.py::TestCapabilityScanDotnetBclFamilyMap::test_assembly_load_family_resolves_eval_not_plain_call` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 4 passed (from 4 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
