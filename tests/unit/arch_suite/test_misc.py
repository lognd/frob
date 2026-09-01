"""Split from tests/unit/test_arch.py (T-1201)."""

from __future__ import annotations

import pytest

from frob.graph.callgraph import CallGraph  # noqa: E402
from frob.graph.summary import (  # noqa: E402
    UNRESOLVED_CALLEE,
    compute_protocol_summaries,
)
from tests.unit.arch_suite.conftest import (
    HAS_ARCH,
    _acquire,
    _escapes,
    _release,
    _requires,
    _transition,
)

pytestmark = pytest.mark.skipif(not HAS_ARCH, reason="frob.arch not available")



class TestModuleDependencyCycles:
    """`check_module_dependency_cycles`
    (docs/modules/arch.md#module-dependency-cycles)."""

    def test_two_file_import_cycle_flagged(self, tmp_path) -> None:  # noqa: ANN001
        from frob.arch._smells import check_module_dependency_cycles

        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("import a\n")
        out = check_module_dependency_cycles(tmp_path)
        assert len(out) == 1
        assert out[0].category == "module-dependency-cycle"
        assert "a.py" in out[0].message
        assert "b.py" in out[0].message

    def test_acyclic_imports_not_flagged(self, tmp_path) -> None:  # noqa: ANN001
        from frob.arch._smells import check_module_dependency_cycles

        (tmp_path / "a.py").write_text("import b\n")
        (tmp_path / "b.py").write_text("x = 1\n")
        out = check_module_dependency_cycles(tmp_path)
        assert out == []


class TestProtocolSummaryEngine:
    """`frob.graph.summary.compute_protocol_summaries` -- bottom-up fixpoint
    over a fixture `CallGraph`, no repo-wide scan (docs/modules/graph.md
    #protocol-summary-engine)."""

    def test_leaf_function_summary_is_its_own_declarations(self):
        """A leaf with no callees summarizes to exactly its own
        `frob:transition`/`frob:requires` declarations."""
        graph = CallGraph(calls={})
        edges = [_transition("f.py::open_conn", "conn", "closed", "open")]
        result = compute_protocol_summaries(
            graph, edges, entrypoints=["f.py::open_conn"]
        )
        summary = result.summaries["f.py::open_conn"]
        assert summary.transitions == {"conn:closed->open"}
        assert summary.requires == frozenset()
        assert not summary.poisoned
        assert result.not_analyzed == ()
        assert result.timeouts == ()

    def test_caller_summary_includes_callee_transitions(self):
        """`caller` calls `helper`; `caller`'s summary must include
        `helper`'s transition even though `caller` declares nothing of its
        own -- the join propagates upward through one hop."""
        graph = CallGraph(calls={"f.py::caller": ("f.py::helper",)})
        edges = [_transition("f.py::helper", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::caller"])
        assert result.summaries["f.py::caller"].transitions == {"conn:closed->open"}
        assert result.summaries["f.py::helper"].transitions == {"conn:closed->open"}
        assert not result.summaries["f.py::caller"].poisoned

    def test_requires_and_transitions_join_across_two_hops(self):
        """`top -> mid -> leaf`: `top`'s summary is the union of all three
        levels' own declarations, hand-computed and compared exactly."""
        graph = CallGraph(
            calls={
                "f.py::top": ("f.py::mid",),
                "f.py::mid": ("f.py::leaf",),
            }
        )
        edges = [
            _requires("f.py::top", "lock", "held"),
            _transition("f.py::mid", "lock", "unheld", "held"),
            _transition("f.py::leaf", "conn", "closed", "open"),
        ]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::top"])
        top = result.summaries["f.py::top"]
        assert top.requires == {"lock:held"}
        assert top.transitions == {"lock:unheld->held", "conn:closed->open"}
        assert not top.poisoned

    def test_recursive_cluster_converges_to_hand_computed_fixpoint(self):
        """A mutually-recursive pair (`a` calls `b`, `b` calls `a`), each
        declaring a distinct transition -- the fixpoint must converge so
        BOTH functions' summaries include BOTH transitions (recursion via
        lattice join, T-0745's design sketch)."""
        graph = CallGraph(
            calls={
                "f.py::a": ("f.py::b",),
                "f.py::b": ("f.py::a",),
            }
        )
        edges = [
            _transition("f.py::a", "conn", "closed", "open"),
            _transition("f.py::b", "conn", "open", "closed"),
        ]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::a"])
        expected = {"conn:closed->open", "conn:open->closed"}
        assert result.summaries["f.py::a"].transitions == expected
        assert result.summaries["f.py::b"].transitions == expected
        assert not result.summaries["f.py::a"].poisoned
        assert not result.summaries["f.py::b"].poisoned
        assert result.timeouts == ()

    def test_self_recursive_function_converges(self):
        """A single function that calls itself is its own one-member SCC
        with a self-loop -- must go through the recursive-cluster branch,
        not the single-node fast path, and still converge to just its own
        declaration (nothing new to join from calling itself)."""
        graph = CallGraph(calls={"f.py::recur": ("f.py::recur",)})
        edges = [_transition("f.py::recur", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::recur"])
        summary = result.summaries["f.py::recur"]
        assert summary.transitions == {"conn:closed->open"}
        assert not summary.poisoned

    def test_unresolved_callee_poisons_the_summary(self):
        """A call to `UNRESOLVED_CALLEE` poisons the caller's summary --
        NO-FAIL-SILENT: the caller's own declarations are still populated,
        but `poisoned` is `True` with a reason naming the caller."""
        graph = CallGraph(calls={"f.py::caller": (UNRESOLVED_CALLEE,)})
        edges = [_transition("f.py::caller", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::caller"])
        summary = result.summaries["f.py::caller"]
        assert summary.poisoned
        assert summary.poison_reason is not None
        assert "unresolved" in summary.poison_reason
        assert summary.transitions == {"conn:closed->open"}

    def test_poisoning_propagates_transitively_through_a_clean_caller(self):
        """`top -> mid -> poisoned_leaf`: `mid` calls an unresolved callee,
        so `mid` is poisoned; `top` calls only `mid` (itself clean) but
        must ALSO end up poisoned -- poisoning propagates upward through
        every transitive caller, it never resets at a clean intermediate
        hop."""
        graph = CallGraph(
            calls={
                "f.py::top": ("f.py::mid",),
                "f.py::mid": (UNRESOLVED_CALLEE,),
            }
        )
        edges = [_transition("f.py::top", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::top"])
        assert result.summaries["f.py::mid"].poisoned
        assert result.summaries["f.py::top"].poisoned
        assert result.summaries["f.py::top"].poison_reason is not None

    def test_unreachable_function_is_reported_not_analyzed_never_silent(self):
        """A function with its own declarations that no entrypoint ever
        calls must show up in `not_analyzed`, and must NOT get a
        (falsely-clean) summary -- the NO-FAIL-SILENT mandate applied to
        reachability."""
        graph = CallGraph(calls={"f.py::entry": ()})
        edges = [_transition("f.py::orphan", "conn", "closed", "open")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::entry"])
        assert "f.py::orphan" in result.not_analyzed
        assert "f.py::orphan" not in result.summaries
        assert "f.py::entry" in result.summaries

    def test_non_converging_scc_is_reported_as_a_timeout_error_and_poisoned(self):
        """A three-member mutually-recursive cluster needs more than one
        join round to fully propagate; capping `max_iterations=1` must
        surface an `SCCTimeout` naming the cluster, and every member of
        the cluster must be poisoned -- an abort is a loud ERROR, never a
        silently-partial summary (T-0745 acceptance)."""
        graph = CallGraph(
            calls={
                "f.py::a": ("f.py::b",),
                "f.py::b": ("f.py::c",),
                "f.py::c": ("f.py::a",),
            }
        )
        edges = [_transition("f.py::a", "conn", "closed", "open")]
        result = compute_protocol_summaries(
            graph, edges, entrypoints=["f.py::a"], max_iterations=1
        )
        assert len(result.timeouts) == 1
        assert set(result.timeouts[0].members) == {"f.py::a", "f.py::b", "f.py::c"}
        assert result.timeouts[0].iterations == 1
        for member in ("f.py::a", "f.py::b", "f.py::c"):
            summary = result.summaries[member]
            assert summary.poisoned
            assert summary.poison_reason is not None
            assert "did not converge" in summary.poison_reason

    def test_diamond_shaped_calls_join_without_duplication_or_loss(self):
        """`top` calls both `left` and `right`, which both call `shared` --
        a diamond. `top`'s summary must include every distinct transition
        exactly once (set union is naturally idempotent) with nothing
        dropped from either branch."""
        graph = CallGraph(
            calls={
                "f.py::top": ("f.py::left", "f.py::right"),
                "f.py::left": ("f.py::shared",),
                "f.py::right": ("f.py::shared",),
            }
        )
        edges = [
            _transition("f.py::left", "a", "s0", "s1"),
            _transition("f.py::right", "b", "s0", "s1"),
            _transition("f.py::shared", "c", "s0", "s1"),
        ]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::top"])
        assert result.summaries["f.py::top"].transitions == {
            "a:s0->s1",
            "b:s0->s1",
            "c:s0->s1",
        }
        assert not result.summaries["f.py::top"].poisoned

    # frob:ticket T-0809
    def test_leaf_resource_declarations_populate_acquired_released_escaped(self):
        """A leaf declaring `frob:acquire`/`frob:release`/`frob:escapes`
        summarizes to exactly those resource-name sets, T-0809's
        resource-tracking DSL folded the same way `requires`/`transitions`
        already are."""
        graph = CallGraph(calls={})
        edges = [
            _acquire("f.py::open_fd", "fd"),
            _release("f.py::open_fd", "lock"),
            _escapes("f.py::open_fd", "conn"),
        ]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::open_fd"])
        summary = result.summaries["f.py::open_fd"]
        assert summary.acquired == {"fd"}
        assert summary.released == {"lock"}
        assert summary.escaped == {"conn"}
        assert not summary.poisoned

    # frob:ticket T-0809
    def test_resource_sets_join_transitively_through_a_caller(self):
        """`caller` calls `helper`, which acquires a resource -- `caller`'s
        summary must include it, matching `requires`/`transitions`'
        existing one-hop join behavior."""
        graph = CallGraph(calls={"f.py::caller": ("f.py::helper",)})
        edges = [_acquire("f.py::helper", "fd")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::caller"])
        assert result.summaries["f.py::caller"].acquired == {"fd"}
        assert result.summaries["f.py::helper"].acquired == {"fd"}

    # frob:ticket T-0809
    def test_resource_sets_join_across_a_recursive_cluster(self):
        """A mutually-recursive pair each declaring a distinct resource
        acquire must converge with BOTH resources in both summaries,
        mirroring `test_recursive_cluster_converges_to_hand_computed_fixpoint`."""
        graph = CallGraph(calls={"f.py::a": ("f.py::b",), "f.py::b": ("f.py::a",)})
        edges = [_acquire("f.py::a", "fd"), _acquire("f.py::b", "lock")]
        result = compute_protocol_summaries(graph, edges, entrypoints=["f.py::a"])
        expected = {"fd", "lock"}
        assert result.summaries["f.py::a"].acquired == expected
        assert result.summaries["f.py::b"].acquired == expected
        assert not result.summaries["f.py::a"].poisoned


# frob:ticket T-2470
class TestCppSymrefCanonicalization:
    """T-2470: the producer-side fix for T-2438's confirmed live symref
    mismatch -- `frob.lang._common._cpp_symref_qualname` separates a C++
    method's `symref=` identity (canonical `.`-joined, matching the DSL/
    graph symbol table's own `frob.lang._walk_c` convention) from its
    human-facing `message=` display (native `Class::method` spelling)."""

    # frob:ticket T-2470
    # frob:tests tests/unit/test_arch.py::TestCppSymrefCanonicalization.test_long_function_symref_is_dot_joined_message_keeps_native_spelling  # noqa: E501
    def test_long_function_symref_is_dot_joined_message_keeps_native_spelling(
        self, tmp_path
    ):
        """A long, complex C++ method's `symref=` uses `.` between class
        and method (matching the DSL's own qualname), while `message=`
        keeps the idiomatic `Class::method` spelling a C++ reader
        expects -- the exact identity/display split T-2470 introduces."""
        from frob.arch._cpp import _check_long_functions

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        ifs = "\n".join("    if (x) { x += 1; }" for _ in range(12))
        source = (
            "class Foo {\n"
            "public:\n"
            "    int bar() {\n"
            "        int x = 1;\n" + ifs + "\n"
            "        return x;\n"
            "    }\n"
            "};\n"
        )
        cpp_path = src_dir / "long.cpp"
        cpp_path.write_text(source)

        import tree_sitter_cpp as tscpp
        from tree_sitter import Language, Parser

        parser = Parser(Language(tscpp.language()))
        tree = parser.parse(cpp_path.read_bytes())
        out = []
        _check_long_functions(tree, "long.cpp", 2, out)
        hits = [s for s in out if s.category == "long-function"]
        assert hits
        assert any(s.symref == "long.cpp::Foo.bar" for s in hits)
        assert any("Foo::bar" in s.message for s in hits)
        assert not any(s.symref == "long.cpp::Foo::bar" for s in hits)

    # frob:ticket T-2470
    # frob:tests tests/unit/test_arch.py::TestCppSymrefCanonicalization.test_symref_matches_dsl_waiver_binding_exactly  # noqa: E501
    def test_symref_matches_dsl_waiver_binding_exactly(self, tmp_path):
        """T-2438's own confirmed repro, now closed at the producer: the
        `Violation.symref` this scanner emits for a class method is now
        BYTE-FOR-BYTE identical to the `Edge.src` the DSL binds a
        symbol-bound `frob:waive` comment to above that same method --
        `_match_waiver`'s T-2438 `_canonical_symref` normalization is
        provably unnecessary for this producer once this fix lands
        (though it still stands as defense in depth for any other
        producer with the same disease)."""
        from frob.arch._cpp import _check_long_functions
        from frob.graph.dsl import parse_directives
        from frob.lang import parse_file

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        ifs = "\n".join("    if (x) { x += 1; }" for _ in range(12))
        cpp_path = src_dir / "long.cpp"
        source = (
            "class Foo {\n"
            "public:\n"
            '    // frob:waive ARCH001 reason="test"\n'
            "    int bar() {\n"
            "        int x = 1;\n" + ifs + "\n"
            "        return x;\n"
            "    }\n"
            "};\n"
        )
        cpp_path.write_text(source)

        import tree_sitter_cpp as tscpp
        from tree_sitter import Language, Parser

        parser = Parser(Language(tscpp.language()))
        tree = parser.parse(cpp_path.read_bytes())
        out = []
        _check_long_functions(tree, str(cpp_path), 2, out)
        assert out
        violation_symref = out[0].symref

        parsed = parse_file(cpp_path).danger_ok
        edges, _malformed = parse_directives(parsed)
        waive_edges = [e for e in edges if e.kind.value == "waive"]
        assert waive_edges
        waiver_src = waive_edges[0].src

        assert violation_symref == waiver_src


# frob:ticket T-0687
class TestCppMayThrow:
    """T-0687: frob.arch._cpp_mayraise -- C++ may-throw analysis wired
    into analyze_project's "cpp" dispatch branch. A noexcept function
    whose computed may-throw set (explicit throw, curated STL throwers,
    same-file callee propagation, Unknown fail-closed for anything else)
    is non-empty and not discharged by its own catch (...) fires
    cpp-noexcept-throws at ArchSeverity "error"."""

    # frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_calling_throwing_function_fires_error  # noqa: E501
    def test_noexcept_calling_throwing_function_fires_error(self, tmp_path):
        """noexcept `caller` calls same-file `risky` (which throws) with
        no try/catch of its own -- an error finding names the call site."""
        from frob.arch import analyze_project

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "risky.cpp").write_text(
            "int risky() {\n"
            '    throw std::runtime_error("bad");\n'
            "}\n\n"
            "void caller() noexcept {\n"
            "    risky();\n"
            "}\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "cpp-noexcept-throws"]
        assert hits
        assert any(s.symref == "risky.cpp::caller" for s in hits)
        assert any(s.severity == "error" for s in hits)

    # frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_with_catch_all_does_not_fire  # noqa: E501
    def test_noexcept_with_catch_all_does_not_fire(self, tmp_path):
        """Same shape as above, but `caller` wraps the risky call in a
        try/catch (...) -- the hard boundary is discharged, no finding."""
        from frob.arch import analyze_project

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "safe.cpp").write_text(
            "int risky() {\n"
            '    throw std::runtime_error("bad");\n'
            "}\n\n"
            "void caller() noexcept {\n"
            "    try {\n"
            "        risky();\n"
            "    } catch (...) {\n"
            "    }\n"
            "}\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "cpp-noexcept-throws"]
        assert hits == []

    # frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_non_noexcept_function_never_fires  # noqa: E501
    def test_non_noexcept_function_never_fires(self, tmp_path):
        """A function that may throw but is NOT noexcept is normal
        propagation, not a hard-boundary violation -- never flagged."""
        from frob.arch import analyze_project

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "propagates.cpp").write_text(
            "int risky() {\n"
            '    throw std::runtime_error("bad");\n'
            "}\n\n"
            "void caller() {\n"
            "    risky();\n"
            "}\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "cpp-noexcept-throws"]
        assert hits == []

    # frob:tests tests/unit/test_arch.py::TestCppMayThrow.test_noexcept_calling_vector_at_fires_curated_thrower  # noqa: E501
    def test_noexcept_calling_vector_at_fires_curated_thrower(self, tmp_path):
        """A noexcept function calling `.at(...)` (curated STL thrower,
        out_of_range) with no catch fires, naming out_of_range."""
        from frob.arch import analyze_project

        src_dir = tmp_path / "src"
        src_dir.mkdir()
        (src_dir / "at_call.cpp").write_text(
            "void reads(std::vector<int>& v) noexcept {\n    int x = v.at(0);\n}\n"
        )
        result = analyze_project(src_dir)
        hits = [s for s in result.suggestions if s.category == "cpp-noexcept-throws"]
        assert hits
        assert any("out_of_range" in s.message for s in hits)
