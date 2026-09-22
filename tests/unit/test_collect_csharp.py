"""T-4561: direct unit coverage for `frob.testing._collect_csharp`'s
private helpers and for `frob.lang._support._capability_test_discovery_
status`'s csharp entry -- both landed with T-4517 but previously exercised
only indirectly through `collect_csharp_tests`'s own integration-style
tests (`tests/test_testing.py::TestCollectCsharpTests`) or the generic
all-languages capability sweep, never a test that pins the private helper
or the csharp-specific capability lookup itself as a first-class unit."""

from __future__ import annotations

import json
from pathlib import Path

from frob.testing._collect_csharp import (
    _collect_cs_file,
    _cs_attribute_names,
    _cs_node_id,
    _cs_test_methods,
    _csharp_content_key,
    _find_cs_files,
    _load_cache,
    _match_dir_excluded,
    _store_cache,
    parse_csharp,
)

_SAMPLE_SOURCE = b"""\
using NUnit.Framework;

namespace Frob.Fixtures.Csharp
{
    public class SampleNunitTests
    {
        [SetUp]
        public void Setup() { }

        [Test]
        public void AddsTwoNumbers()
        {
            Assert.AreEqual(4, 2 + 2);
        }

        [TestCase(1, 2)]
        [TestCase(3, 4)]
        public void AddsPair(int a, int b) { }
    }
}
"""


class TestMatchDirExcluded:
    """`_match_dir_excluded` -- a directory is pruned if its own relative
    path, or a `**`-style descendant of it, matches an exclude glob."""

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestMatchDirExcluded.test_exact_dir_match
    def test_exact_dir_match(self) -> None:
        assert _match_dir_excluded("build", "build") is True

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestMatchDirExcluded.test_descendant_match
    def test_descendant_match(self) -> None:
        assert _match_dir_excluded("build", "build/**") is True

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestMatchDirExcluded.test_unrelated_dir_is_not_excluded  # noqa: E501
    def test_unrelated_dir_is_not_excluded(self) -> None:
        assert _match_dir_excluded("src", "build/**") is False


class TestFindCsFiles:
    """`_find_cs_files` -- every `.cs` file under root, non-`.cs` files
    and excluded directories pruned."""

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestFindCsFiles.test_finds_nested_cs_files_only
    def test_finds_nested_cs_files_only(self, tmp_path: Path) -> None:
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "A.cs").write_text("// a\n")
        (tmp_path / "src" / "B.txt").write_text("not cs\n")
        (tmp_path / "src" / "nested").mkdir()
        (tmp_path / "src" / "nested" / "C.cs").write_text("// c\n")

        found = _find_cs_files(tmp_path)

        assert found == sorted(
            [tmp_path / "src" / "A.cs", tmp_path / "src" / "nested" / "C.cs"]
        )

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestFindCsFiles.test_no_cs_files_is_empty_list
    def test_no_cs_files_is_empty_list(self, tmp_path: Path) -> None:
        assert _find_cs_files(tmp_path) == []


class TestCsAttributeNamesAndTestMethods:
    """`_cs_attribute_names`/`_cs_test_methods` -- attribute extraction
    and qualname-tuple discovery directly against a parsed tree, one
    level below `collect_csharp_tests`'s own file-level integration
    tests."""

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods.test_test_attributed_method_is_found_with_its_qualname  # noqa: E501
    def test_test_attributed_method_is_found_with_its_qualname(self) -> None:
        tree = parse_csharp(_SAMPLE_SOURCE)

        found = _cs_test_methods(tree.root_node, ())

        assert ("Frob.Fixtures.Csharp", "SampleNunitTests", "AddsTwoNumbers") in found

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods.test_setup_method_is_excluded  # noqa: E501
    def test_setup_method_is_excluded(self) -> None:
        tree = parse_csharp(_SAMPLE_SOURCE)

        found = _cs_test_methods(tree.root_node, ())

        assert not any(qualname[-1] == "Setup" for qualname in found)

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods.test_parameterized_test_case_collapses_to_one_qualname  # noqa: E501
    def test_parameterized_test_case_collapses_to_one_qualname(self) -> None:
        tree = parse_csharp(_SAMPLE_SOURCE)

        found = _cs_test_methods(tree.root_node, ())

        add_pair = [q for q in found if q[-1] == "AddsPair"]
        assert len(add_pair) == 1

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestCsAttributeNamesAndTestMethods.test_attribute_names_reads_bare_names_off_a_method_node  # noqa: E501
    def test_attribute_names_reads_bare_names_off_a_method_node(self) -> None:
        tree = parse_csharp(_SAMPLE_SOURCE)
        # Walk down to the `AddsTwoNumbers` method_declaration node.
        method_node = None
        stack = [tree.root_node]
        while stack:
            node = stack.pop()
            if node.type == "method_declaration":
                name_node = node.child_by_field_name("name")
                if name_node is not None and name_node.text == b"AddsTwoNumbers":
                    method_node = node
                    break
            stack.extend(node.children)
        assert method_node is not None

        assert _cs_attribute_names(method_node) == {"Test"}


class TestCsNodeIdAndCollectCsFile:
    """`_cs_node_id`/`_collect_cs_file` -- node id shape and per-file
    collection, including the never-hard-fail posture on an unreadable
    file."""

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile.test_node_id_shape  # noqa: E501
    def test_node_id_shape(self, tmp_path: Path) -> None:
        cs_path = tmp_path / "tests" / "Sample.cs"
        cs_path.parent.mkdir(parents=True)
        cs_path.write_text("// placeholder\n")

        node_id = _cs_node_id(
            tmp_path, cs_path, ("Frob", "Fixtures", "SampleTests", "DoesThing")
        )

        assert node_id == "tests/Sample.cs::Frob.Fixtures.SampleTests::DoesThing"

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile.test_collect_cs_file_returns_node_ids  # noqa: E501
    def test_collect_cs_file_returns_node_ids(self, tmp_path: Path) -> None:
        cs_path = tmp_path / "Sample.cs"
        cs_path.write_bytes(_SAMPLE_SOURCE)

        node_ids = _collect_cs_file(tmp_path, cs_path)

        assert "Sample.cs::Frob.Fixtures.Csharp.SampleNunitTests::AddsTwoNumbers" in (
            node_ids
        )

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestCsNodeIdAndCollectCsFile.test_unreadable_file_returns_empty_list_not_a_raise  # noqa: E501
    def test_unreadable_file_returns_empty_list_not_a_raise(
        self, tmp_path: Path
    ) -> None:
        missing = tmp_path / "does_not_exist.cs"

        assert _collect_cs_file(tmp_path, missing) == []


class TestContentKeyAndCache:
    """`_csharp_content_key`/`_load_cache`/`_store_cache` -- the cache
    round-trip's content-hash key and hit/miss behavior, local copies of
    `_collect_shared`'s but this module's own (module docstring's own
    T-4517 scope-boundary explanation)."""

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestContentKeyAndCache.test_content_key_changes_when_file_content_changes  # noqa: E501
    def test_content_key_changes_when_file_content_changes(
        self, tmp_path: Path
    ) -> None:
        cs_path = tmp_path / "Sample.cs"
        cs_path.write_text("// v1\n")
        key_one = _csharp_content_key(tmp_path, [cs_path])

        cs_path.write_text("// v2\n")
        key_two = _csharp_content_key(tmp_path, [cs_path])

        assert key_one != key_two

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestContentKeyAndCache.test_store_then_load_round_trips  # noqa: E501
    def test_store_then_load_round_trips(self, tmp_path: Path) -> None:
        cache_path = tmp_path / ".frob" / "csharp-nunit-collect.json"
        node_ids = frozenset({"a.cs::Ns.C::M"})

        _store_cache(cache_path, "key-1", node_ids)
        loaded = _load_cache(cache_path, "key-1")

        assert loaded == node_ids

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestContentKeyAndCache.test_load_cache_key_mismatch_is_a_miss  # noqa: E501
    def test_load_cache_key_mismatch_is_a_miss(self, tmp_path: Path) -> None:
        cache_path = tmp_path / ".frob" / "csharp-nunit-collect.json"
        _store_cache(cache_path, "key-1", frozenset({"a.cs::Ns.C::M"}))

        assert _load_cache(cache_path, "key-2") is None

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestContentKeyAndCache.test_load_cache_missing_file_is_a_miss  # noqa: E501
    def test_load_cache_missing_file_is_a_miss(self, tmp_path: Path) -> None:
        assert _load_cache(tmp_path / "absent.json", "key-1") is None

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestContentKeyAndCache.test_load_cache_unreadable_json_is_a_miss  # noqa: E501
    def test_load_cache_unreadable_json_is_a_miss(self, tmp_path: Path) -> None:
        cache_path = tmp_path / ".frob" / "csharp-nunit-collect.json"
        cache_path.parent.mkdir(parents=True)
        cache_path.write_text("not json", encoding="utf-8")

        assert _load_cache(cache_path, "key-1") is None

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestContentKeyAndCache.test_store_cache_writes_sorted_node_ids  # noqa: E501
    def test_store_cache_writes_sorted_node_ids(self, tmp_path: Path) -> None:
        cache_path = tmp_path / ".frob" / "csharp-nunit-collect.json"

        _store_cache(cache_path, "key-1", frozenset({"b.cs::N::M", "a.cs::N::M"}))

        doc = json.loads(cache_path.read_text(encoding="utf-8"))
        assert doc["node_ids"] == ["a.cs::N::M", "b.cs::N::M"]


class TestCapabilityTestDiscoveryStatusCsharp:
    """T-4517's `_TEST_DISCOVERY_COLLECTORS["csharp"]` entry --
    `_capability_test_discovery_status` resolves it live against
    `frob.testing.collect_csharp_tests`, mirroring the pre-existing
    kotlin coverage (`tests/test_lang_support.py::
    TestDeriveCapabilityRegistry.test_kotlin_test_discovery_is_
    implemented`) for the csharp entry specifically."""

    # frob:tests \
    # tests/unit/test_collect_csharp.py::TestCapabilityTestDiscoveryStatusCsharp.test_csharp_test_discovery_is_implemented  # noqa: E501
    def test_csharp_test_discovery_is_implemented(self) -> None:
        from frob.lang._support import (
            CapabilityRequirement,
            FacetState,
            _capability_test_discovery_status,
        )

        status = _capability_test_discovery_status("csharp")

        assert status.requirement == CapabilityRequirement.REQUIRED
        assert status.state == FacetState.IMPLEMENTED
