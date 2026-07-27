"""REL394-REL397 ABI-COMPAT-WINDOW + BOOT-ATTESTATION obligation family
unit coverage (T-0962, `frob.strata._supply_chain_boot`) -- mirrors
`test_process_bounds.py`'s `tmp_path` real-file convention for
proof-against-code (bind_code-backed, so it needs a real file tree, not
just an in-memory `KernelModel`).
"""

from __future__ import annotations

from pathlib import Path

from frob.strata import KernelModel, Node, Waiver
from frob.strata._supply_chain_boot import (
    REL_MISSING_ABI_COMPAT_WINDOW,
    REL_MISSING_BOOT_ATTESTATION,
    REL_UNPROVEN_ABI_COMPAT_WINDOW,
    REL_UNPROVEN_BOOT_ATTESTATION,
    check_supply_chain_boot_obligations,
)


def _write(root: Path, rel: str, source: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


class TestMissingAbiCompatWindow:
    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow.test_compiled_artifact_node_without_compat_window_fires
    def test_compiled_artifact_node_without_compat_window_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="auth_library",
                    trust="trusted",
                    attrs=("compiled_artifact",),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_ABI_COMPAT_WINDOW
        ]
        assert {v.node for v in missing} == {"auth_library"}

    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow.test_discharged_and_non_compiled_artifact_nodes_clean
    def test_discharged_and_non_compiled_artifact_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="auth_library",
                    trust="trusted",
                    attrs=("compiled_artifact", "abi_compat_window"),
                ),
                Node(id="pure_script", trust="trusted"),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_ABI_COMPAT_WINDOW
        ]

    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestMissingAbiCompatWindow.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="auth_library",
                    trust="trusted",
                    attrs=("compiled_artifact",),
                    waives=(
                        Waiver(
                            rule="REL394",
                            reason="legacy artifact, compat window tracked in T-9910",
                        ),
                    ),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [
            v for v in report.violations if v.rule == REL_MISSING_ABI_COMPAT_WINDOW
        ]
        assert {
            v.node for v in report.waived if v.rule == REL_MISSING_ABI_COMPAT_WINDOW
        } == {"auth_library"}


class TestUnprovenAbiCompatWindow:
    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_lib.py",
            "def build():\n    return link_object()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="auth_library",
                    trust="trusted",
                    attrs=(
                        "compiled_artifact",
                        "abi_compat_window",
                        "code=src/widget/**",
                    ),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_ABI_COMPAT_WINDOW
        ]
        assert {v.node for v in violations} == {"auth_library"}

    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_lib.py",
            "def build():\n"
            "    # abi_version compat_window enforced via semver check\n"
            "    return link_object()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="auth_library",
                    trust="trusted",
                    attrs=(
                        "compiled_artifact",
                        "abi_compat_window",
                        "code=src/widget/**",
                    ),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_ABI_COMPAT_WINDOW
        ]

    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestUnprovenAbiCompatWindow.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="auth_library",
                    trust="trusted",
                    attrs=("compiled_artifact", "abi_compat_window"),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_ABI_COMPAT_WINDOW
        ]


class TestMissingBootAttestation:
    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation.test_boot_chain_stage_node_without_attestation_fires
    def test_boot_chain_stage_node_without_attestation_fires(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="bootloader_stage",
                    trust="trusted",
                    attrs=("boot_chain_stage",),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        missing = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_BOOT_ATTESTATION
        ]
        assert {v.node for v in missing} == {"bootloader_stage"}

    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation.test_discharged_and_non_boot_chain_stage_nodes_clean
    def test_discharged_and_non_boot_chain_stage_nodes_clean(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="bootloader_stage",
                    trust="trusted",
                    attrs=("boot_chain_stage", "boot_attested"),
                ),
                Node(id="userspace_daemon", trust="trusted"),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_MISSING_BOOT_ATTESTATION
        ]

    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestMissingBootAttestation.test_waiver_discharges_finding
    def test_waiver_discharges_finding(self, tmp_path: Path):
        model = KernelModel(
            nodes=(
                Node(
                    id="bootloader_stage",
                    trust="trusted",
                    attrs=("boot_chain_stage",),
                    waives=(
                        Waiver(
                            rule="REL396",
                            reason="legacy stage, attestation tracked in T-9910",
                        ),
                    ),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        report = result.danger_ok
        assert not [
            v for v in report.violations if v.rule == REL_MISSING_BOOT_ATTESTATION
        ]
        assert {
            v.node for v in report.waived if v.rule == REL_MISSING_BOOT_ATTESTATION
        } == {"bootloader_stage"}


class TestUnprovenBootAttestation:
    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation.test_declared_with_no_code_evidence_fires
    def test_declared_with_no_code_evidence_fires(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_boot.py",
            "def run_stage():\n    return jump_to_next()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="bootloader_stage",
                    trust="trusted",
                    attrs=("boot_chain_stage", "boot_attested", "code=src/widget/**"),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        violations = [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOOT_ATTESTATION
        ]
        assert {v.node for v in violations} == {"bootloader_stage"}

    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation.test_declared_with_real_code_evidence_discharges
    def test_declared_with_real_code_evidence_discharges(self, tmp_path: Path):
        _write(
            tmp_path,
            "src/widget/_boot.py",
            "def run_stage():\n"
            "    # secure_boot verify_signature before jumping to next stage\n"
            "    return jump_to_next()\n",
        )
        model = KernelModel(
            nodes=(
                Node(
                    id="bootloader_stage",
                    trust="trusted",
                    attrs=("boot_chain_stage", "boot_attested", "code=src/widget/**"),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOOT_ATTESTATION
        ]

    # frob:tests tests/unit/strata/test_supply_chain_boot.py::TestUnprovenBootAttestation.test_declared_with_no_bound_code_is_uncheckable_not_a_violation
    def test_declared_with_no_bound_code_is_uncheckable_not_a_violation(
        self, tmp_path: Path
    ):
        model = KernelModel(
            nodes=(
                Node(
                    id="bootloader_stage",
                    trust="trusted",
                    attrs=("boot_chain_stage", "boot_attested"),
                ),
            ),
        )
        result = check_supply_chain_boot_obligations(model, tmp_path)
        assert result.is_ok
        assert not [
            v
            for v in result.danger_ok.violations
            if v.rule == REL_UNPROVEN_BOOT_ATTESTATION
        ]
