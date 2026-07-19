"""Unit-level coverage for `frob.deploy._vm_runner` (T-0259): the graceful-
degrade gate (`vboxmanage_available`, `run_vm_audit`'s skip-before-any-
subprocess-call behavior when `VBoxManage` is absent), PLUS the full
happy-path sequence with the `subprocess.run` boundary mocked (T-0293's
zero-TEST005 pass) -- `_restore_base_snapshot`/`_capture_state`/`_ssh`/
`_scp_to_guest`/`_vboxmanage` are real `VBoxManage`/`ssh` orchestration
against a live guest in production, but their CONTROL FLOW (the sequence
of calls `run_vm_audit` drives, and each helper's own branches) is
exercised here with `subprocess.run` faked at the module boundary, so no
real VM is needed to prove the sequence itself is correct.
"""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

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


def _fake_subprocess_run(cmd, **kwargs):
    """Stand-in for `subprocess.run` used by every `_vm_runner` helper
    (`_vboxmanage`/`_ssh`/`_scp_to_guest`) -- dispatches on the real argv
    shape each helper builds and returns plausible stdout, so
    `run_vm_audit`'s full sequence (restore -> C0/S0 -> install -> C1/S1
    -> install again -> C1'/S1' -> uninstall -> C2/S2 -> attestation)
    runs start to finish against a fake guest instead of a real VM."""
    prog = cmd[0]
    if prog in ("VBoxManage", "scp"):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    if prog == "ssh":
        remote_command = cmd[-1]
        if "status.sh" in remote_command:
            stdout = (
                "unit=frob-deploy-api.service node=api "
                "active=active enabled=enabled\n"
                "unit=frob-deploy-api.service port=8080=open\n"
            )
        elif "sha256sum" in remote_command:
            stdout = "deadbeefcafe\nroot root 644\n"
        elif remote_command == "cat /etc/passwd":
            stdout = "root:x:0:0::/root:/bin/bash\n"
        elif remote_command == "cat /etc/group":
            stdout = "root:x:0:\n"
        elif "systemd/system" in remote_command:
            stdout = "[Unit]\nDescription=fake\n"
        elif "list-unit-files" in remote_command:
            stdout = "frob-deploy-api.service enabled\n"
        elif "ss -tln" in remote_command:
            stdout = "LISTEN 0 128 *:8080 *:*\n"
        else:
            stdout = ""
        return subprocess.CompletedProcess(cmd, 0, stdout=stdout, stderr="")
    raise AssertionError(f"unexpected subprocess.run call: {cmd!r}")


class TestFullSequence:
    """`run_vm_audit`'s happy path with `subprocess.run` faked at the
    `_vm_runner` module boundary (module docstring) -- no real
    `VBoxManage`/`ssh`/`scp` is invoked, but every helper
    (`_restore_base_snapshot`/`_capture_state`/`_run_status_and_assert`/
    `_ssh`/`_scp_to_guest`/`_vboxmanage`) runs its real code path."""

    def _cfg(self) -> VmAuditConfig:
        return VmAuditConfig(
            vm_name="frob-audit-vm",
            base_snapshot="base",
            ssh_host="127.0.0.1",
            ssh_user="root",
            ssh_key_path=Path("/fake/key"),
            deploy_dir=Path("/fake/deploy"),
            expected_paths=("/etc/api",),
            expected_units=("frob-deploy-api.service",),
            expected_targets=frozenset(),
        )

    # frob:tests src/frob/deploy/_vm_runner.py::run_vm_audit kind="unit"
    def test_run_vm_audit_runs_full_sequence(self) -> None:
        with (
            patch("shutil.which", return_value="/usr/bin/VBoxManage"),
            patch(
                "frob.deploy._vm_runner.subprocess.run",
                side_effect=_fake_subprocess_run,
            ),
        ):
            result = run_vm_audit(self._cfg())
        assert result.status == "ran"
        assert result.reason is None
        assert result.attestation is not None
        assert [c.label for c in result.attestation.checkpoints] == [
            "C0",
            "C1",
            "C1'",
            "C2",
        ]

    # frob:tests src/frob/deploy/_vm_runner.py::run_vm_audit kind="unit"
    def test_run_vm_audit_propagates_ssh_error(self) -> None:
        """An ssh/VBoxManage failure (`check=True` raising
        `CalledProcessError`) is NOT swallowed -- it propagates out of
        `run_vm_audit` so a real VM/network failure surfaces as a hard
        error rather than a silently-wrong attestation."""

        def _raise(cmd, **kwargs):
            if cmd[0] == "ssh":
                raise subprocess.CalledProcessError(255, cmd, stderr="ssh: timed out")
            return _fake_subprocess_run(cmd, **kwargs)

        with (
            patch("shutil.which", return_value="/usr/bin/VBoxManage"),
            patch("frob.deploy._vm_runner.subprocess.run", side_effect=_raise),
            pytest.raises(subprocess.CalledProcessError),
        ):
            run_vm_audit(self._cfg())
