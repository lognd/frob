from pathlib import Path

_FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "lang" / "csharp"


class TestCapabilityScanCsharpTaxonomyClosureResolution:
    """T-4536: csharp sibling of `TestCapabilityScanKotlinTaxonomy
    ClosureResolution` -- `using`/alias/`static`-using name-binding
    resolution wired into `_capability_scan.py`'s per-language dispatch,
    closing the gap where csharp files reached `frob.lang.parse_file`
    (T-1600) but `frob.vet._capability` had no import/alias-aware
    resolution pass for the language -- only the pre-existing raw-text
    needle scan."""

    def test_plain_using_namespace_resolves_fs_write(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `using System.IO; File.WriteAllText(...)`
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "plain_using_fs_write.cs"
        assert "fs-write" in scan_file_capabilities(pkg)

    def test_using_alias_follows_to_the_same_capability(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: `using IO = System.IO; IO.File.WriteAllText(...)`
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "alias_using_fs_write.cs"
        assert "fs-write" in scan_file_capabilities(pkg)

    def test_using_static_resolves_bare_call_to_fully_qualified_symbol(
        self,
    ) -> None:
        # frob:tests src/frob/vet/_capability_csharp.py::_cs_resolved_candidates \
        # kind="unit"
        # Taxonomy row: `using static System.Console; WriteLine(...)` --
        # asserted directly against the resolver's own resolved-candidate
        # text (WriteLine is not itself a registry-dangerous symbol, so
        # this checks resolution correctness, not a security finding).
        from frob.vet._capability_csharp import _cs_resolved_candidates

        pkg = _FIXTURES / "static_using_console.cs"
        resolved = [name for name, _start, _end in _cs_resolved_candidates(pkg)]
        assert "System.Console.WriteLine" in resolved

    def test_var_local_type_carries_into_a_later_instance_call(self) -> None:
        # frob:tests src/frob/vet/_capability_csharp.py::_cs_resolved_candidates \
        # kind="unit"
        # Taxonomy row: `var client = new System.Net.Http.HttpClient();
        # client.GetAsync(...)` -- the `var` local's type resolves into
        # the later member-access call site.
        from frob.vet._capability_csharp import _cs_resolved_candidates

        pkg = _FIXTURES / "var_local_httpclient.cs"
        resolved = [name for name, _start, _end in _cs_resolved_candidates(pkg)]
        assert "System.Net.Http.HttpClient.GetAsync" in resolved

    def test_no_dangerous_apis_reports_zero_findings(self) -> None:
        # frob:tests src/frob/vet/_capability_scan.py::scan_file_capabilities \
        # kind="unit"
        # Taxonomy row: a file with no dangerous APIs at all -- the wired
        # resolver must add nothing of its own (no false positives).
        from frob.vet._capability import scan_file_capabilities

        pkg = _FIXTURES / "no_dangerous_apis.cs"
        assert scan_file_capabilities(pkg) == frozenset()

    def test_static_using_does_not_hijack_a_member_access_base(self) -> None:
        # frob:tests src/frob/vet/_capability_csharp.py::_cs_resolved_candidates \
        # kind="unit"
        # Regression guard: a file with BOTH `using static System.Console;`
        # and `using System.IO;` must still resolve `File.WriteAllText`
        # against `System.IO`, never against the unrelated `using static`
        # class -- the static-using fallback is scoped to bare call
        # targets only, never a member-access base.
        from frob.vet._capability_csharp import _cs_resolved_candidates

        pkg = _FIXTURES / "combined_static_and_namespace.cs"
        resolved = [name for name, _start, _end in _cs_resolved_candidates(pkg)]
        assert "System.IO.File.WriteAllText" in resolved
        assert "System.Console.WriteLine" in resolved
        assert not any("Console.File" in r for r in resolved)
