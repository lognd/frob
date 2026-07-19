"""Unit-level coverage for `frob.app.deploy_runner` (T-0257/T-0259 CLI
wiring): `run`'s three-way dispatch (`generate`/`audit`/unrecognized),
`_run_generate`'s write vs `--check` paths, and `_run_audit`'s required-
flag validation plus the skipped/passed/failed exit-code contract
(module docstring's 0/1/2 exit codes) -- `run_vm_audit` itself is mocked
here (it is unit-tested with a faked `subprocess.run` boundary in
`tests/unit/deploy/test_vm_runner.py`), so this file is purely about the
CLI dispatch and file-writing logic around it.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from frob.app.config import AppConfig
from frob.app.deploy_runner import run
from frob.deploy import AuditAttestation, AuditRunResult, CheckpointResult, generate_all
from frob.strata._models import KernelModel, Node

_STRATA_SRC = """\
module deploy_runner_fixture

node api : trusted {
    clearance Internal;
    runs_as "api-svc";
    unit;
    owns "/etc/api" "0644";
    listens 8080;
}
"""


def _write_design(root: Path) -> None:
    design = root / "design"
    design.mkdir(parents=True, exist_ok=True)
    (design / "fixture.strata").write_text(_STRATA_SRC)


def _model() -> KernelModel:
    return KernelModel(
        nodes=(
            Node(
                id="api",
                trust="trusted",
                attrs=("runs_as=api-svc", "unit", "owns=/etc/api:0644", "listens=8080"),
            ),
        )
    )


class TestDispatch:
    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_unrecognized_command_prints_usage_and_exits(self, tmp_path):
        cfg = AppConfig(deploy_command="bogus", deploy_path=tmp_path)
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_no_command_prints_usage_and_exits(self, tmp_path):
        cfg = AppConfig(deploy_command=None, deploy_path=tmp_path)
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1


class TestGenerate:
    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_generate_no_model_exits_1(self, tmp_path):
        cfg = AppConfig(deploy_command="generate", deploy_path=tmp_path)
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_generate_writes_files(self, tmp_path):
        _write_design(tmp_path)
        cfg = AppConfig(deploy_command="generate", deploy_path=tmp_path)
        run(cfg)
        deploy_dir = tmp_path / "deploy"
        rendered = generate_all(_model())
        for filename, content in rendered.items():
            written = deploy_dir / filename
            assert written.read_text(encoding="utf-8") == content
            # writer sets the scripts executable (0o755)
            assert written.stat().st_mode & 0o777 == 0o755

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_generate_check_clean_no_exit(self, tmp_path):
        _write_design(tmp_path)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        for filename, content in generate_all(_model()).items():
            (deploy_dir / filename).write_text(content)
        cfg = AppConfig(deploy_command="generate", deploy_path=tmp_path, deploy_check=True)
        # No SystemExit -- clean check returns normally.
        run(cfg)

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_generate_check_missing_files_exits_1(self, tmp_path):
        """`deploy/` does not exist at all -- every filename hits the
        `not path.exists()` branch inside `--check`."""
        _write_design(tmp_path)
        cfg = AppConfig(deploy_command="generate", deploy_path=tmp_path, deploy_check=True)
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_generate_check_stale_file_exits_1(self, tmp_path):
        """`deploy/` exists with all three files present, but one has
        stale content -- hits the `read_text() != content` branch."""
        _write_design(tmp_path)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        for filename, content in generate_all(_model()).items():
            (deploy_dir / filename).write_text(content)
        (deploy_dir / "install.sh").write_text("# stale hand-edit\n")
        cfg = AppConfig(deploy_command="generate", deploy_path=tmp_path, deploy_check=True)
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1


def _fake_attestation(*, passed: bool) -> AuditAttestation:
    checkpoint = CheckpointResult(
        label="C0", status_assertion="unit=fake inactive", status_assertion_passed=passed
    )
    return AuditAttestation(
        vm_name="fake-vm",
        base_snapshot="base",
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        checkpoints=(checkpoint,),
        idempotence_holds=passed,
        artifact_freeness_holds=passed,
        install_exactness_holds=passed,
        install_exactness_extra=(),
        install_exactness_missing=(),
    )


class TestAudit:
    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_audit_missing_vm_exits_1(self, tmp_path):
        cfg = AppConfig(
            deploy_command="audit",
            deploy_path=tmp_path,
            deploy_ssh_host="127.0.0.1",
            deploy_ssh_key=tmp_path / "key",
        )
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_audit_missing_ssh_host_exits_1(self, tmp_path):
        cfg = AppConfig(
            deploy_command="audit",
            deploy_path=tmp_path,
            deploy_vm="frob-audit-vm",
            deploy_ssh_key=tmp_path / "key",
        )
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_audit_missing_ssh_key_exits_1(self, tmp_path):
        cfg = AppConfig(
            deploy_command="audit",
            deploy_path=tmp_path,
            deploy_vm="frob-audit-vm",
            deploy_ssh_host="127.0.0.1",
        )
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_audit_no_model_exits_1(self, tmp_path):
        cfg = AppConfig(
            deploy_command="audit",
            deploy_path=tmp_path,
            deploy_vm="frob-audit-vm",
            deploy_ssh_host="127.0.0.1",
            deploy_ssh_key=tmp_path / "key",
        )
        with pytest.raises(SystemExit) as excinfo:
            run(cfg)
        assert excinfo.value.code == 1

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_audit_skipped_exits_2(self, tmp_path):
        _write_design(tmp_path)
        cfg = AppConfig(
            deploy_command="audit",
            deploy_path=tmp_path,
            deploy_vm="frob-audit-vm",
            deploy_ssh_host="127.0.0.1",
            deploy_ssh_key=tmp_path / "key",
        )
        with patch(
            "frob.app.deploy_runner.run_vm_audit",
            return_value=AuditRunResult(status="skipped", reason="VBoxManage not found"),
        ):
            with pytest.raises(SystemExit) as excinfo:
                run(cfg)
        assert excinfo.value.code == 2

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_audit_passed_writes_attestation_no_exit(self, tmp_path):
        _write_design(tmp_path)
        cfg = AppConfig(
            deploy_command="audit",
            deploy_path=tmp_path,
            deploy_vm="frob-audit-vm",
            deploy_ssh_host="127.0.0.1",
            deploy_ssh_key=tmp_path / "key",
        )
        attestation = _fake_attestation(passed=True)
        with patch(
            "frob.app.deploy_runner.run_vm_audit",
            return_value=AuditRunResult(status="ran", attestation=attestation),
        ):
            run(cfg)
        output = tmp_path / "deploy-audit-attestation.json"
        assert output.exists()
        assert "fake-vm" in output.read_text(encoding="utf-8")

    # frob:tests src/frob/app/deploy_runner.py::run kind="unit"
    def test_audit_failed_exits_1(self, tmp_path):
        _write_design(tmp_path)
        cfg = AppConfig(
            deploy_command="audit",
            deploy_path=tmp_path,
            deploy_vm="frob-audit-vm",
            deploy_ssh_host="127.0.0.1",
            deploy_ssh_key=tmp_path / "key",
        )
        attestation = _fake_attestation(passed=False)
        with patch(
            "frob.app.deploy_runner.run_vm_audit",
            return_value=AuditRunResult(status="ran", attestation=attestation),
        ):
            with pytest.raises(SystemExit) as excinfo:
                run(cfg)
        assert excinfo.value.code == 1
