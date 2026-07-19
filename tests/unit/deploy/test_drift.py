"""Unit-level coverage for `frob.deploy._drift`'s DEPLOY001 opt-in drift
check (T-0257): no `deploy/` dir skips, matching scripts are clean, a
stale committed script is flagged by name.
"""

from __future__ import annotations

from pathlib import Path

from frob.deploy._drift import deploy_drift_violations
from frob.deploy._generate import generate_all
from frob.strata._models import KernelModel, Node

_STRATA_SRC = """\
module deploy_drift_fixture

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


class TestDrift:
    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_no_dir(self, tmp_path):
        _write_design(tmp_path)
        assert deploy_drift_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_clean(self, tmp_path):
        _write_design(tmp_path)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        for filename, content in generate_all(_model()).items():
            (deploy_dir / filename).write_text(content)
        assert deploy_drift_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_stale(self, tmp_path):
        _write_design(tmp_path)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        for filename, content in generate_all(_model()).items():
            (deploy_dir / filename).write_text(content)
        (deploy_dir / "install.sh").write_text("# hand edit\n")

        violations = deploy_drift_violations(tmp_path)
        assert len(violations) == 1
        assert violations[0].file == "deploy/install.sh"
