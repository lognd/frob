"""Unit-level coverage for `frob.deploy._vm_runner`'s ONE VM-free surface:
`vboxmanage_available`'s graceful-degrade gate and `run_vm_audit`'s
skip-before-any-subprocess-call behavior when `VBoxManage` is absent
(T-0259). Everything past that gate (`_restore_base_snapshot`,
`_capture_state`, `_ssh`, ...) is real `VBoxManage`/`ssh` orchestration,
deliberately NOT unit-tested here -- that is this feature's one
VM-gated, untested-in-CI sliver, per `frob.deploy._audit`'s module
docstring.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from frob.deploy._vm_runner import VmAuditConfig, run_vm_audit, vboxmanage_available


class TestAvail:
    """`vboxmanage_available` / `run_vm_audit`'s graceful degrade."""

    # frob:tests src/frob/deploy/_vm_runner.py::vboxmanage_available kind="unit"
    def test_no_bin(self) -> None:
        with patch("shutil.which", return_value=None):
            assert not vboxmanage_available()

    # frob:tests src/frob/deploy/_vm_runner.py::run_vm_audit kind="unit"
    def test_run_vm_audit_skips_cleanly(self) -> None:
        cfg = VmAuditConfig(
            vm_name="frob-audit-vm",
            base_snapshot="base",
            ssh_host="127.0.0.1",
            ssh_user="root",
            ssh_key_path=Path("/nonexistent/key"),
            deploy_dir=Path("/nonexistent/deploy"),
            expected_paths=(),
            expected_units=(),
            expected_targets=frozenset(),
        )
        with patch("shutil.which", return_value=None):
            result = run_vm_audit(cfg)
        assert result.status == "skipped"
        assert result.reason is not None
        assert result.attestation is None
