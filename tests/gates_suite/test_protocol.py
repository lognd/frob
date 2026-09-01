from pathlib import Path

from frob.gates import (
    Severity,
)
from tests.conftest import (
    _snapshot,
    _write,
)


# frob:ticket T-0813
class TestProtocolSummaryGate:
    """T-0813: the production `mark_unresolved=True` wiring into
    `compute_protocol_summaries` -- a `frob:requires`/`frob:transition`-
    tagged symbol whose transitive call closure hits an unresolved private
    callee is PROTO001; a clean or untagged one is not."""

    def test_unresolved_callee_poisons_a_protocol_tagged_symbol(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Lock" state="held"\n'
            "    _do_work()\n"
            "\n\n"
            "def _do_work() -> None:\n"
            "    _missing_helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO001"), None)
        assert v is not None
        assert "src/a.py::enter" in v.message
        assert v.severity == Severity.WARN

    def test_clean_protocol_tagged_symbol_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Lock" state="held"\n'
            "    _do_work()\n"
            "\n\n"
            "def _do_work() -> None:\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO001" for v in violations)

    def test_untagged_symbol_with_unresolved_call_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Lock" state="held"\n'
            "    pass\n"
            "\n\n"
            "def untagged() -> None:\n"
            "    _missing_helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO001" for v in violations)

    def test_real_repo_scan_runs_end_to_end_without_crashing(self) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="integration"
        # T-0813: the honest "real repo scan" smoke test -- runs the actual
        # production entrypoint (build_call_graph(mark_unresolved=True) +
        # compute_protocol_summaries) over this repo's OWN real graph
        # snapshot, not a hand-fabricated fixture. Nothing in this repo's
        # production code carries a frob:requires/frob:transition directive
        # yet (T-0744's declaration surface has no first production
        # consumer besides this gate's own tests), so 0 violations is the
        # correct, honest result today -- the assertion that matters is
        # that a real repo scan, including every UNRESOLVED_CALLEE the
        # dunder/cross-package exemption (T-0813) had to be built to
        # filter, completes without the IndexError/crash class T-0809's
        # own Done report disclosed as the reason mark_unresolved defaulted
        # to False.
        from frob.gates._protocol_summary import protocol_summary_gate

        root = Path(__file__).resolve().parents[2]
        snap = _snapshot(root)
        violations = protocol_summary_gate(root, snap)
        assert isinstance(violations, tuple)
# frob:ticket T-0746
# frob:ticket T-0841
class TestProtocolVerificationGate:
    """T-0746: PROTO002 (state-requirement violation) and PROTO003 (invalid
    transition), the ERROR-tier verification rules sharing PROTO001's
    per-package `protocol_summary_gate` scan. T-0841 adds the Rust/
    TypeScript real-repo-scan cases."""

    def test_state_never_established_is_an_error(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO002"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::enter" in v.message
        assert "Net" in v.message and "active" in v.message

    def test_state_established_by_a_reachable_transition_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def net_init() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n"
            "\n\n"
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO002" for v in violations)

    def test_state_equal_to_initial_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Net states="idle,active" initial="idle"\n'
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="idle"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO002" for v in violations)

    def test_poisoned_summary_at_a_requires_symbol_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    _do_work()\n"
            "\n\n"
            "def _do_work() -> None:\n"
            "    _missing_helper()\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO002"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "poisoned" in v.message

    def test_invalid_transition_precondition_never_established_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def net_close() -> None:\n"
            '    # frob:transition proto="Net" from="active" to="closed"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO003"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::net_close" in v.message
        assert "active" in v.message

    def test_valid_transition_chain_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Net states="idle,active,closed" initial="idle"\n'
            "def net_init() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n"
            "\n\n"
            "def net_close() -> None:\n"
            '    # frob:transition proto="Net" from="active" to="closed"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO003" for v in violations)

    def test_python_with_block_discharges_the_requirement(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    with Net() as _n:\n"
            "        pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO002" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO002"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "python-with" in discharge.message

    # frob:ticket T-0841
    def test_rust_file_state_never_established_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # T-0841: PROTO002 now real-repo-scans Rust files too, not just
        # Python -- proves the gate's own `.py`-only filter is lifted.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.rs",
            '// frob:requires proto="Net" state="active"\nfn enter() {\n}\n',
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO002"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.rs::enter" in v.message

    # frob:ticket T-0841
    def test_rust_drop_impl_discharges_the_requirement(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # T-0841: `_discharge` dispatches to `rust_drop_discharge` for a
        # `.rs` file -- the real cross-language discharge wiring this
        # ticket adds (T-0746 built the predicate, only Python was wired).
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.rs",
            '// frob:requires proto="Net" state="active"\n'
            "fn enter() {\n"
            "}\n"
            "impl Drop for Net {\n"
            "    fn drop(&mut self) {}\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO002" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO002"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "rust-drop" in discharge.message

    # frob:ticket T-0841
    def test_typescript_using_discharges_the_requirement(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.ts",
            '// frob:requires proto="Net" state="active"\n'
            "function enter(): void {\n"
            "  using n = Net();\n"
            "}\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO002" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO002"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "typescript-using" in discharge.message
# frob:ticket T-0840
class TestProtocolOrderingGate:
    """T-0840: PROTO004, the per-call-site ordering check that narrows
    PROTO002/PROTO003's existential ("established SOMEWHERE in the
    closure") approximation using `build_ordered_call_graph`'s source-
    text-ordered call sequences."""

    # frob:ticket T-0840
    def test_call_before_establishing_transition_is_an_ordering_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # The crisp T-0840 case: `caller` calls `_consume` (requires
        # Net:active) BEFORE `_establish` (transitions Net idle->active)
        # -- a real ordering bug. PROTO002's existential check alone
        # would NOT catch this (state IS established somewhere in the
        # closure, just too late) -- see the companion test below.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def caller() -> None:\n"
            "    _consume()\n"
            "    _establish()\n"
            "\n\n"
            "def _consume() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n"
            "\n\n"
            "def _establish() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        # PROTO002's own existential check does not fire here -- disclosed
        # limitation this ticket narrows, not replaces.
        assert not any(v.rule == "PROTO002" for v in violations)
        v = next((v for v in violations if v.rule == "PROTO004"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::caller" in v.message
        assert "src/a.py::_consume" in v.message
        assert "Net" in v.message and "active" in v.message

    # frob:ticket T-0840
    def test_call_after_establishing_transition_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # Same functions, correct order: no PROTO004.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def caller() -> None:\n"
            "    _establish()\n"
            "    _consume()\n"
            "\n\n"
            "def _consume() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n"
            "\n\n"
            "def _establish() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO004" for v in violations)

    # frob:ticket T-0840
    def test_python_with_block_discharges_the_ordering_violation(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # The same language-excuse discharge PROTO002/PROTO003 get,
        # checked against the CALLER's own file.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def caller() -> None:\n"
            "    with Net() as _n:\n"
            "        _consume()\n"
            "        _establish()\n"
            "\n\n"
            "def _consume() -> None:\n"
            '    # frob:requires proto="Net" state="active"\n'
            "    pass\n"
            "\n\n"
            "def _establish() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO004" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO004"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "python-with" in discharge.message
# frob:ticket T-0746
class TestProtocolLanguageExcuseDischarge:
    """T-0746: the per-language discharge predicates
    (`frob.arch._protocol_excuse`) each rule's language-excuse doctrine
    reduces to -- built and directly tested here even where a real
    cross-file repo-scan wiring for that language is not built yet
    (Rust/C++/TypeScript/GC, disclosed T-0839 follow-up; see
    docs/modules/gates.md#proto002-proto003-t-0746)."""

    def test_rust_drop_impl_discharges(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # rust_drop_impl_discharges
        from frob.arch._protocol_excuse import rust_drop_discharge

        source = "struct Net;\nimpl Drop for Net {\n    fn drop(&mut self) {}\n}\n"
        result = rust_drop_discharge(source, "Net")
        assert result.discharged
        assert result.mechanism == "rust-drop"

    def test_rust_mem_forget_revokes_the_drop_discharge(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # rust_mem_forget_revokes_the_drop_discharge
        from frob.arch._protocol_excuse import rust_drop_discharge

        source = (
            "struct Net;\n"
            "impl Drop for Net {\n    fn drop(&mut self) {}\n}\n"
            "fn leak(n: Net) {\n    mem::forget(n);\n}\n"
        )
        result = rust_drop_discharge(source, "Net")
        assert not result.discharged
        assert "forget" in result.reason

    def test_rust_manually_drop_revokes_the_discharge(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # rust_manually_drop_revokes_the_discharge
        from frob.arch._protocol_excuse import rust_drop_discharge

        source = (
            "struct Net;\n"
            "impl Drop for Net {\n    fn drop(&mut self) {}\n}\n"
            "struct Holder(ManuallyDrop<Net>);\n"
        )
        result = rust_drop_discharge(source, "Net")
        assert not result.discharged
        assert "ManuallyDrop" in result.reason

    def test_rust_no_drop_impl_is_not_discharged(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # rust_no_drop_impl_is_not_discharged
        from frob.arch._protocol_excuse import rust_drop_discharge

        result = rust_drop_discharge("struct Net;\n", "Net")
        assert not result.discharged

    def test_cpp_raii_destructor_discharges(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # cpp_raii_destructor_discharges
        from frob.arch._protocol_excuse import cpp_raii_discharge

        source = "class Net {\npublic:\n    ~Net() {}\n};\n"
        result = cpp_raii_discharge(source, "Net")
        assert result.discharged
        assert result.mechanism == "cpp-raii"

    def test_cpp_no_destructor_is_not_discharged(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # cpp_no_destructor_is_not_discharged
        from frob.arch._protocol_excuse import cpp_raii_discharge

        result = cpp_raii_discharge("class Net {\n};\n", "Net")
        assert not result.discharged

    def test_python_with_block_discharges(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # python_with_block_discharges
        from frob.arch._protocol_excuse import python_with_discharge

        result = python_with_discharge("with Net() as n:\n    pass\n", "Net")
        assert result.discharged
        assert result.mechanism == "python-with"

    def test_python_no_with_block_is_not_discharged(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # python_no_with_block_is_not_discharged
        from frob.arch._protocol_excuse import python_with_discharge

        result = python_with_discharge("Net().connect()\n", "Net")
        assert not result.discharged

    def test_typescript_using_discharges(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # typescript_using_discharges
        from frob.arch._protocol_excuse import typescript_using_discharge

        result = typescript_using_discharge("using n = Net();\n", "Net")
        assert result.discharged
        assert result.mechanism == "typescript-using"

    def test_typescript_try_finally_discharges(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # typescript_try_finally_discharges
        from frob.arch._protocol_excuse import typescript_using_discharge

        source = "try {\n  n.use();\n} finally {\n  n.close();\n}\n"
        result = typescript_using_discharge(source, "n")
        assert result.discharged
        assert result.mechanism == "typescript-try-finally"

    def test_typescript_bare_call_is_not_discharged(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # typescript_bare_call_is_not_discharged
        from frob.arch._protocol_excuse import typescript_using_discharge

        result = typescript_using_discharge("net.connect();\n", "net")
        assert not result.discharged

    def test_gc_finalizer_never_discharges(self) -> None:
        # frob:tests \
        # tests/gates_suite/test_protocol.py::TestProtocolLanguageExcuseDischarge.test_\
        # gc_finalizer_never_discharges
        from frob.arch._protocol_excuse import gc_finalizer_discharge

        result = gc_finalizer_discharge("Net")
        assert not result.discharged
        assert result.mechanism == "gc-finalizer"
# frob:ticket T-0747
class TestCleanupObligationGate:
    """T-0747: PROTO005, cleanup obligations -- release-postdominates-
    acquisition on all exits (including exceptional, via T-0686's
    may-raise sets), escape transfer, and per-protocol cleanup="always"
    deinit-never-called."""

    def test_early_return_before_release_call_is_an_error(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_conn() -> int:\n"
            "    # frob:acquire conn\n"
            "    fd = 1\n"
            "    if fd < 0:\n"
            "        return -1\n"
            "    _close(fd)\n"
            "    return 0\n"
            "\n\n"
            "def _close(fd: int) -> None:\n"
            "    # frob:release conn\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next((v for v in violations if v.rule == "PROTO005"), None)
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::open_conn" in v.message
        assert "conn" in v.message

    def test_release_before_return_is_not_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_conn() -> int:\n"
            "    # frob:acquire conn\n"
            "    fd = 1\n"
            "    _close(fd)\n"
            "    return 0\n"
            "\n\n"
            "def _close(fd: int) -> None:\n"
            "    # frob:release conn\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO005" for v in violations)

    def test_escape_transfer_discharges_the_obligation(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_conn() -> int:\n"
            "    # frob:acquire conn\n"
            "    # frob:escapes conn\n"
            "    if True:\n"
            "        return -1\n"
            "    return 1\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO005" for v in violations)

    def test_self_contained_acquire_and_release_is_trusted(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_and_close() -> int:\n"
            "    # frob:acquire conn\n"
            "    # frob:release conn\n"
            "    if True:\n"
            "        return -1\n"
            "    return 0\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO005" for v in violations)

    def test_python_with_block_discharges_the_acquisition(self, tmp_path: Path) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def enter() -> int:\n"
            "    # frob:acquire conn\n"
            "    with conn() as _c:\n"
            "        if bad():\n"
            "            return -1\n"
            "    return 0\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        error = next(
            (
                v
                for v in violations
                if v.rule == "PROTO005" and v.severity == Severity.ERROR
            ),
            None,
        )
        assert error is None
        discharge = next((v for v in violations if v.rule == "PROTO005"), None)
        assert discharge is not None
        assert discharge.severity == Severity.WARN
        assert "python-with" in discharge.message

    def test_process_exit_ok_policy_discharges_a_terminator_guarded_return(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # Same "early return before release" shape as the crisp true-
        # positive test above, but this acquisition's own frob:protocol
        # declares cleanup="process-exit-ok" and the early return is
        # itself preceded by a process-terminating call -- discharged
        # silently by the declared policy, per the module docstring's
        # per-protocol-policy clause.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Res states="idle,active" initial="idle" '
            'cleanup="process-exit-ok"\n'
            "def open_conn() -> int:\n"
            "    # frob:acquire conn\n"
            "    fd = 1\n"
            "    if fd < 0:\n"
            "        exit(1)\n"
            "        return -1\n"
            "    _close(fd)\n"
            "    return 0\n"
            "\n\n"
            "def _close(fd: int) -> None:\n"
            "    # frob:release conn\n"
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(v.rule == "PROTO005" for v in violations)

    def test_exceptional_exit_with_no_release_anywhere_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        # Reuses T-0686's compute_may_raise: open_conn calls a same-module
        # function that unconditionally raises, and NOTHING in open_conn's
        # own body ever releases "conn" -- an exceptional exit skips
        # cleanup.
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            "def open_conn() -> None:\n"
            "    # frob:acquire conn\n"
            "    _maybe_raise()\n"
            "    return\n"
            "\n\n"
            "def _maybe_raise() -> None:\n"
            '    raise ValueError("bad")\n',
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next(
            (
                v
                for v in violations
                if v.rule == "PROTO005" and "may raise" in v.message
            ),
            None,
        )
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "src/a.py::open_conn" in v.message

    def test_deinit_never_called_for_cleanup_always_protocol_is_an_error(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Net states="idle,active,closed" initial="idle" '
            'cleanup="always"\n'
            "def net_init() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        v = next(
            (
                v
                for v in violations
                if v.rule == "PROTO005" and "deinit-never-called" in v.message
            ),
            None,
        )
        assert v is not None
        assert v.severity == Severity.ERROR
        assert "Net" in v.message and "closed" in v.message

    def test_deinit_reachable_for_cleanup_always_protocol_is_not_flagged(
        self, tmp_path: Path
    ) -> None:
        # frob:tests src/frob/gates/_protocol_summary.py::protocol_summary_gate \
        # kind="unit"
        from frob.gates._protocol_summary import protocol_summary_gate

        _write(
            tmp_path,
            "src/a.py",
            '# frob:protocol Net states="idle,active,closed" initial="idle" '
            'cleanup="always"\n'
            "def net_init() -> None:\n"
            '    # frob:transition proto="Net" from="idle" to="active"\n'
            "    pass\n"
            "\n\n"
            "def net_close() -> None:\n"
            '    # frob:transition proto="Net" from="active" to="closed"\n'
            "    pass\n",
        )
        snap = _snapshot(tmp_path)
        violations = protocol_summary_gate(tmp_path, snap)
        assert not any(
            v.rule == "PROTO005" and "deinit-never-called" in v.message
            for v in violations
        )
