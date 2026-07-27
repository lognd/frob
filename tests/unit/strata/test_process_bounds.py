"""REL39x KERNEL-INTERFACE-CLASSIFICATION + PROCESS-RESOURCE-BOUND
obligation family unit coverage (T-0960, `frob.strata._process_bounds`)
-- mirrors `test_backpressure.py`'s `tmp_path` real-file convention for
proof-against-code (bind_code-backed, so it needs a real file tree, not
just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._process_bounds import (
    REL_MISSING_INTERFACE_CLASSIFICATION,
    REL_MISSING_PROCESS_BOUNDS,
    REL_UNPROVEN_INTERFACE_CLASSIFICATION,
    REL_UNPROVEN_PROCESS_BOUNDS,
    check_process_bounds_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingInterfaceClassification:
    # frob:tests tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification.test_kernel_interface_node_without_classification_fires
    def test_kernel_interface_node_without_classification_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="open_procfs_entry",
                    trust="trusted",
                    attrs=("kernel_interface",),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_INTERFACE_CLASSIFICATION
        ]
        assert {v.node for v in missing} == {"open_procfs_entry"}

    # frob:tests tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification.test_discharged_and_non_kernel_interface_nodes_clean
    def test_discharged_and_non_kernel_interface_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="open_procfs_entry",
                    trust="trusted",
                    attrs=("kernel_interface", "interface_classified"),
                ),
                Node(id="userspace_only", trust="trusted"),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_INTERFACE_CLASSIFICATION
        ]

    # frob:tests tests/unit/strata/test_process_bounds.py::TestMissingInterfaceClassification.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="open_procfs_entry",
                    trust="trusted",
                    attrs=("kernel_interface",),
                    waives=(
                        Waiver(
                            rule="REL390",
                            reason="legacy shim, classification tracked in T-9910",
                        ),
                    ),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [
            v
            for v in report.violations
            if v.rule == REL_MISSING_INTERFACE_CLASSIFICATION
        ]
        assert {
            v.node
            for v in report.waived
            if v.rule == REL_MISSING_INTERFACE_CLASSIFICATION
        } == {"open_procfs_entry"}


class TestUnprovenInterfaceClassification:
    # frob:tests tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_ioctl.py",
            "def do_ioctl():\n    return open_device()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="open_procfs_entry",
                    trust="trusted",
                    attrs=(
                        "kernel_interface",
                        "interface_classified",
                        "code=src/widget/**",
                    ),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_INTERFACE_CLASSIFICATION
        ]
        assert {v.node for v in violations} == {"open_procfs_entry"}

    # frob:tests tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_ioctl.py",
            "def do_ioctl():\n"
            "    # trusted, read_only access to this procfs entry\n"
            "    return open_device()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="open_procfs_entry",
                    trust="trusted",
                    attrs=(
                        "kernel_interface",
                        "interface_classified",
                        "code=src/widget/**",
                    ),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_INTERFACE_CLASSIFICATION
        ]

    # frob:tests tests/unit/strata/test_process_bounds.py::TestUnprovenInterfaceClassification.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="open_procfs_entry",
                    trust="trusted",
                    attrs=("kernel_interface", "interface_classified"),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_INTERFACE_CLASSIFICATION
        ]


class TestMissingProcessBounds:
    # frob:tests tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds.test_deployed_process_node_without_bounds_fires
    def test_deployed_process_node_without_bounds_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="worker_service",
                    trust="trusted",
                    attrs=("deployed_process",),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_PROCESS_BOUNDS
        ]
        assert {v.node for v in missing} == {"worker_service"}

    # frob:tests tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds.test_discharged_and_non_deployed_process_nodes_clean
    def test_discharged_and_non_deployed_process_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="worker_service",
                    trust="trusted",
                    attrs=("deployed_process", "cgroup_bounds"),
                ),
                Node(id="library_call", trust="trusted"),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_PROCESS_BOUNDS
        ]

    # frob:tests tests/unit/strata/test_process_bounds.py::TestMissingProcessBounds.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="worker_service",
                    trust="trusted",
                    attrs=("deployed_process",),
                    waives=(
                        Waiver(
                            rule="REL392",
                            reason="legacy worker, bounds tracked in T-9910",
                        ),
                    ),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [
            v for v in report.violations if v.rule == REL_MISSING_PROCESS_BOUNDS
        ]
        assert {
            v.node for v in report.waived if v.rule == REL_MISSING_PROCESS_BOUNDS
        } == {"worker_service"}


class TestUnprovenProcessBounds:
    # frob:tests tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_run.py",
            "def run_worker():\n    return start_loop()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="worker_service",
                    trust="trusted",
                    attrs=("deployed_process", "cgroup_bounds", "code=src/widget/**"),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_PROCESS_BOUNDS
        ]
        assert {v.node for v in violations} == {"worker_service"}

    # frob:tests tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_run.py",
            "def run_worker():\n"
            "    # cgroup memory.max and cpu.max are set at deploy time\n"
            "    return start_loop()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="worker_service",
                    trust="trusted",
                    attrs=("deployed_process", "cgroup_bounds", "code=src/widget/**"),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_PROCESS_BOUNDS
        ]

    # frob:tests tests/unit/strata/test_process_bounds.py::TestUnprovenProcessBounds.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="worker_service",
                    trust="trusted",
                    attrs=("deployed_process", "cgroup_bounds"),
                ),
            ),
        )
        result = check_process_bounds_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_PROCESS_BOUNDS
        ]
