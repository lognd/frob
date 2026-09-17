from pathlib import Path

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "lang" / "csharp"


class TestCapabilityScanDotnetBclFamilyMap:
    """T-4511: one test per `.NET` BCL family `_dotnet_bcl.py` adds to
    `DANGEROUS_OPERATIONS` -- each asserts the resolved capability kind
    via the real scan entry point (`scan_file_capabilities`), against a
    static checked-in `.cs` fixture, per the ticket's acceptance
    criteria. Families already covered by the T-4536 csharp resolver
    slice (`Process.Start`, `HttpClient`/`WebClient`, `File.WriteAllText`/
    `ReadAllText`, `Environment.Get/SetEnvironmentVariable`, `DllImport`/
    `Marshal`) are NOT re-tested here -- see
    `tests/vet_suite/test_capability_scan_csharp.py` for those."""

    def test_directory_family_resolves_fs_write(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: System.IO Directory.CreateDirectory -> fs-write.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_directory_fs_write.cs"
        assert "fs-write" in scan_file_capabilities(pkg)

    def test_streamwriter_family_resolves_fs_write(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: System.IO StreamWriter -> fs-write.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_streamwriter_fs_write.cs"
        assert "fs-write" in scan_file_capabilities(pkg)

    def test_streamreader_family_resolves_fs_read(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: System.IO StreamReader -> fs-read.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_streamreader_fs_read.cs"
        assert "fs-read" in scan_file_capabilities(pkg)

    def test_dns_family_resolves_net_connect(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: System.Net.Sockets.Dns.GetHostAddresses ->
        # net-connect (the precise kind, not the retired coarse "net").
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_dns_net.cs"
        assert "net-connect" in scan_file_capabilities(pkg)

    def test_assembly_load_family_resolves_eval_not_plain_call(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: System.Reflection Assembly.Load -> eval, distinct
        # from a plain uncategorized method-call finding.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_assembly_load_eval.cs"
        found = scan_file_capabilities(pkg)
        assert "eval" in found
        assert "exec" not in found

    def test_activator_createinstance_family_resolves_eval(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: Activator.CreateInstance(typeName) -> eval.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_activator_createinstance_eval.cs"
        assert "eval" in scan_file_capabilities(pkg)

    def test_type_gettype_family_resolves_eval(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: Type.GetType(typeName) -> eval.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_type_gettype_eval.cs"
        assert "eval" in scan_file_capabilities(pkg)

    def test_registry_family_resolves_fs_write(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: Microsoft.Win32.Registry.SetValue -> fs-write.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_registry_fs_write.cs"
        assert "fs-write" in scan_file_capabilities(pkg)

    def test_sqlcommand_family_resolves_sql(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: System.Data new SqlCommand(...) -> sql.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_sqlcommand_sql.cs"
        assert "sql" in scan_file_capabilities(pkg)

    def test_jsonserializer_deserialize_family_resolves_deserialize(self) -> None:
        # frob:tests \
        # src/frob/vet/_capability_registry/_dotnet_bcl.py::_DOTNET_BCL_OPERATIONS \
        # kind="unit"
        # Taxonomy row: System.Text.Json JsonSerializer.Deserialize -> deserialize.
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "dotnet_bcl_jsonserializer_deserialize.cs"
        assert "deserialize" in scan_file_capabilities(pkg)
