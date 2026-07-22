"""SYS2xx resource-contention family litmus + unit coverage (T-0699,
`frob.strata._contention`) -- mirrors `test_litmus_host.py`'s real
`strata_core` parse -> elaborate round-trip discipline: each rule gets a
firing (`_vuln`) and clean fixture pair under `litmus/`, proving the
check fires on the real grammar text, not just a hand-built `KernelModel`.
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Module, elaborate, parse_module
from frob.strata._contention import (
    SYS_DUPLICATE_PORT,
    SYS_OVERLAPPING_PATH,
    SYS_SHARED_PIPE,
    SYS_SHARED_STORE_WRITE,
    check_resource_contention,
)

_LITMUS_DIR = Path(__file__).resolve().parent / "litmus"


def _load(filename: str) -> tuple[Module, KernelModel]:
    """Parse+elaborate one `.strata` fixture under `litmus/`, returning
    both the pre-elaboration `Module` (for its `stores` id set) and the
    elaborated `KernelModel` -- `check_resource_contention`'s two inputs."""
    text = (_LITMUS_DIR / filename).read_text(encoding="utf-8")
    module = parse_module(text).danger_ok
    model = elaborate(module).danger_ok
    return module, model


class TestDuplicatePort:
    # frob:tests tests/unit/strata/test_contention.py::TestDuplicatePort.test_two_nodes_same_port_fires
    def test_two_nodes_same_port_fires(self):
        _module, model = _load("contention_port_vuln.strata")
        report = check_resource_contention(model)
        port_findings = [v for v in report.violations if v.rule == SYS_DUPLICATE_PORT]
        nodes = {v.node for v in port_findings}
        assert nodes == {"api_a", "api_b"}
        assert all(v.sub_target == "8080" for v in port_findings)
        # api_a's distinct port 9000 must not spuriously fire.
        assert all("9000" not in v.detail for v in port_findings)

    # frob:tests tests/unit/strata/test_contention.py::TestDuplicatePort.test_distinct_ports_clean
    def test_distinct_ports_clean(self):
        _module, model = _load("contention_port_clean.strata")
        report = check_resource_contention(model)
        assert not [v for v in report.violations if v.rule == SYS_DUPLICATE_PORT]

    # frob:tests tests/unit/strata/test_contention.py::TestDuplicatePort.test_one_sided_waiver_keeps_the_other_nodes_finding
    def test_one_sided_waiver_keeps_the_other_nodes_finding(self):
        _module, model = _load("contention_port_waived.strata")
        report = check_resource_contention(model)
        kept_nodes = {v.node for v in report.violations if v.rule == SYS_DUPLICATE_PORT}
        waived_nodes = {v.node for v in report.waived if v.rule == SYS_DUPLICATE_PORT}
        assert kept_nodes == {"api_b"}
        assert waived_nodes == {"api_a"}


class TestOverlappingPath:
    # frob:tests tests/unit/strata/test_contention.py::TestOverlappingPath.test_owns_subtree_overlap_fires_write_capable
    def test_owns_subtree_overlap_fires_write_capable(self):
        _module, model = _load("contention_path_vuln.strata")
        report = check_resource_contention(model)
        findings = [v for v in report.violations if v.rule == SYS_OVERLAPPING_PATH]
        nodes = {v.node for v in findings}
        assert nodes == {"api_a", "api_b"}
        assert all(v.write_capable for v in findings)
        # api_b's disjoint /etc/other-service claim must not fire.
        assert all("/etc/other-service" not in v.detail for v in findings)

    # frob:tests tests/unit/strata/test_contention.py::TestOverlappingPath.test_disjoint_paths_clean
    def test_disjoint_paths_clean(self):
        _module, model = _load("contention_path_clean.strata")
        report = check_resource_contention(model)
        assert not [v for v in report.violations if v.rule == SYS_OVERLAPPING_PATH]

    # frob:tests tests/unit/strata/test_contention.py::TestOverlappingPath.test_readonly_acl_overlap_fires_but_not_write_capable
    def test_readonly_acl_overlap_fires_but_not_write_capable(self):
        _module, model = _load("contention_acl_readonly_vuln.strata")
        report = check_resource_contention(model)
        findings = [v for v in report.violations if v.rule == SYS_OVERLAPPING_PATH]
        assert {v.node for v in findings} == {"svc_a", "svc_b"}
        assert all(not v.write_capable for v in findings)


class TestSharedPipe:
    # frob:tests tests/unit/strata/test_contention.py::TestSharedPipe.test_same_pipe_name_fires
    def test_same_pipe_name_fires(self):
        _module, model = _load("contention_pipe_vuln.strata")
        report = check_resource_contention(model)
        findings = [v for v in report.violations if v.rule == SYS_SHARED_PIPE]
        assert {v.node for v in findings} == {"svc_a", "svc_b"}

    # frob:tests tests/unit/strata/test_contention.py::TestSharedPipe.test_distinct_pipe_names_clean
    def test_distinct_pipe_names_clean(self):
        _module, model = _load("contention_pipe_clean.strata")
        report = check_resource_contention(model)
        assert not [v for v in report.violations if v.rule == SYS_SHARED_PIPE]


class TestSharedStoreWrite:
    # frob:tests tests/unit/strata/test_contention.py::TestSharedStoreWrite.test_two_writers_fires_mode_blind
    def test_two_writers_fires_mode_blind(self):
        module, model = _load("contention_store_vuln.strata")
        store_ids = frozenset(s.id for s in module.stores)
        report = check_resource_contention(model, store_ids=store_ids)
        findings = [v for v in report.violations if v.rule == SYS_SHARED_STORE_WRITE]
        nodes = {v.node for v in findings}
        assert nodes == {"writer_a", "writer_b"}
        assert all(v.sub_target == "shared_store" for v in findings)
        assert all("other_store" not in v.detail for v in findings)

    # frob:tests tests/unit/strata/test_contention.py::TestSharedStoreWrite.test_single_writer_clean
    def test_single_writer_clean(self):
        module, model = _load("contention_store_clean.strata")
        store_ids = frozenset(s.id for s in module.stores)
        report = check_resource_contention(model, store_ids=store_ids)
        assert not [v for v in report.violations if v.rule == SYS_SHARED_STORE_WRITE]

    # frob:tests tests/unit/strata/test_contention.py::TestSharedStoreWrite.test_empty_store_ids_is_silent
    def test_empty_store_ids_is_silent(self):
        """`store_ids` empty (the default): SYS203 must emit nothing at
        all, even though the SAME fixture fires with `store_ids` supplied
        -- `KernelModel` alone cannot reconstruct which nodes are stores
        (`_contention.py` module docstring), so an empty set is "no store
        facts available", never a guess."""
        _module, model = _load("contention_store_vuln.strata")
        report = check_resource_contention(model)
        assert not [v for v in report.violations if v.rule == SYS_SHARED_STORE_WRITE]
