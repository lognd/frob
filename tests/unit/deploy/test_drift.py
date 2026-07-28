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


_STRATA_SRC_WITH_WINDOWS = """\
module deploy_drift_fixture

node api : trusted {
    clearance Internal;
    runs_as "api-svc";
    unit;
    owns "/etc/api" "0644";
    listens 8080;
}

node winapi : trusted {
    clearance Internal;
    platform "windows";
    service_account "svc-api";
    service;
}
"""


def _write_design(root: Path) -> None:
    design = root / "design"
    design.mkdir(parents=True, exist_ok=True)
    (design / "fixture.strata").write_text(_STRATA_SRC)


def _model_with_windows() -> KernelModel:
    return KernelModel(
        nodes=(
            Node(
                id="api",
                trust="trusted",
                attrs=("runs_as=api-svc", "unit", "owns=/etc/api:0644", "listens=8080"),
            ),
            Node(
                id="winapi",
                trust="trusted",
                attrs=("platform=windows", "service_account=svc-api", "service"),
            ),
        )
    )


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

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_no_model_loads(self, tmp_path):
        """deploy/ exists but no `.strata` design file loads anywhere ->
        `_current_model_output` returns None -> clean (nothing to check
        against), exercising the `fresh is None` branch."""
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        (deploy_dir / "install.sh").write_text("# whatever\n")
        assert deploy_drift_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_partial_committed(self, tmp_path):
        """Only one of the three generated filenames is committed -- the
        other two hit the `not committed_path.exists()` continue branch,
        and the committed one still gets checked for drift."""
        _write_design(tmp_path)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        rendered = generate_all(_model())
        (deploy_dir / "status.sh").write_text(rendered["status.sh"])
        violations = deploy_drift_violations(tmp_path)
        assert violations == ()

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_malformed_strata_file_yields_no_model(self, tmp_path):
        """A `.strata` file that fails to parse makes `load_design_ids`
        report `.errors`, so `_load_current_model` returns None and drift
        checking is skipped clean -- exercises the `ids.errors` branch."""
        design = tmp_path / "design"
        design.mkdir()
        (design / "broken.strata").write_text("this is not valid strata !!\n")
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        (deploy_dir / "install.sh").write_text("# whatever\n")
        assert deploy_drift_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_bad_frob_toml_falls_back_to_default_design_dir(self, tmp_path):
        """An unparseable `frob.toml` makes `_design_dir` catch
        `TOMLDecodeError` and fall back to `DEFAULT_DESIGN_DIR` -- the
        design still loads from the default location so the drift check
        stays functional despite the bad toml."""
        (tmp_path / "frob.toml").write_text("this = is [ not valid toml\n")
        _write_design(tmp_path)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        for filename, content in generate_all(_model()).items():
            (deploy_dir / filename).write_text(content)
        assert deploy_drift_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_windows_file_no_longer_produced_is_flagged(self, tmp_path):
        """T-0264: a committed `install.ps1` that the CURRENT model no
        longer produces at all (no windows manifest declared) is itself
        drift -- exercises the `filename not in fresh` branch, distinct
        from a content mismatch."""
        _write_design(tmp_path)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        for filename, content in generate_all(_model()).items():
            (deploy_dir / filename).write_text(content)
        (deploy_dir / "install.ps1").write_text("# stale windows script\n")

        violations = deploy_drift_violations(tmp_path)
        assert len(violations) == 1
        assert violations[0].file == "deploy/install.ps1"

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_windows_clean(self, tmp_path):
        """T-0264: a model WITH a windows manifest regenerates all six
        filenames clean."""
        design = tmp_path / "design"
        design.mkdir()
        (design / "fixture.strata").write_text(_STRATA_SRC_WITH_WINDOWS)
        model = _model_with_windows()
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        rendered = generate_all(model)
        assert set(rendered) == {
            "install.sh",
            "status.sh",
            "uninstall.sh",
            "install.ps1",
            "status.ps1",
            "uninstall.ps1",
        }
        for filename, content in rendered.items():
            (deploy_dir / filename).write_text(content)
        assert deploy_drift_violations(tmp_path) == ()

    # frob:tests src/frob/deploy/_drift.py::deploy_drift_violations kind="unit"
    def test_custom_design_dir_from_frob_toml(self, tmp_path):
        """`[strata].design_dir` in `frob.toml` is honored -- covers the
        `toml_path.exists()` true branch and the custom-value read in
        `_design_dir`."""
        (tmp_path / "frob.toml").write_text('[strata]\ndesign_dir = "custom_design"\n')
        design = tmp_path / "custom_design"
        design.mkdir()
        (design / "fixture.strata").write_text(_STRATA_SRC)
        deploy_dir = tmp_path / "deploy"
        deploy_dir.mkdir()
        for filename, content in generate_all(_model()).items():
            (deploy_dir / filename).write_text(content)
        assert deploy_drift_violations(tmp_path) == ()
