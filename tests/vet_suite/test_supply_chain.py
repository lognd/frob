from pathlib import Path


class TestSupplyChainUnpinnedDependencies:
    """T-1088: VET007, SC-ATTACK-UNPINNED-DEPENDENCIES."""

    def test_pyproject_caret_range_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_supplychain.py::_unpinned_dependency_violations \
        # kind="unit"
        from frob.vet._supplychain import _unpinned_dependency_violations

        (tmp_path / "pyproject.toml").write_text(
            'dependencies = [\n  "requests>=2.0",\n  "typani==0.0.3",\n]\n'
        )
        violations = _unpinned_dependency_violations(tmp_path)
        rules = {v.rule for v in violations}
        assert "VET007" in rules
        messages = " ".join(v.message for v in violations)
        assert "requests" in messages
        assert "typani" not in messages

    def test_pyproject_exact_pin_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_dependency_violations

        (tmp_path / "pyproject.toml").write_text(
            'dependencies = [\n  "typani==0.0.3",\n]\n'
        )
        violations = _unpinned_dependency_violations(tmp_path)
        assert violations == []

    def test_package_json_wildcard_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_dependency_violations

        (tmp_path / "package.json").write_text(
            '{"dependencies": {"lodash": "*", "left-pad": "1.3.0"}}\n'
        )
        violations = _unpinned_dependency_violations(tmp_path)
        rules = {v.rule for v in violations}
        assert "VET007" in rules
        messages = " ".join(v.message for v in violations)
        assert "lodash" in messages
        assert "left-pad" not in messages

    def test_cargo_toml_caret_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_dependency_violations

        (tmp_path / "Cargo.toml").write_text(
            '[dependencies]\nserde = "^1.0"\nlibc = "0.2.150"\n'
        )
        violations = _unpinned_dependency_violations(tmp_path)
        rules = {v.rule for v in violations}
        assert "VET007" in rules
        messages = " ".join(v.message for v in violations)
        assert "serde" in messages
        assert "libc" not in messages


class TestSupplyChainInstallArtifacts:
    """T-1088: VET008, SC-DETECTION-PYTHON-INSTALL-ARTIFACTS."""

    def test_setup_py_absolute_data_files_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_supplychain.py::_python_install_artifact_violations \
        # kind="unit"
        from frob.vet._supplychain import _python_install_artifact_violations

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\n"
            "setup(data_files=[('/etc/cron.d', ['evil.cron'])])\n"
        )
        violations = _python_install_artifact_violations(tmp_path)
        assert any(v.rule == "VET008" for v in violations)

    def test_setup_py_traversal_data_files_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _python_install_artifact_violations

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\n"
            "setup(data_files=[('../../etc', ['evil'])])\n"
        )
        violations = _python_install_artifact_violations(tmp_path)
        assert any(v.rule == "VET008" for v in violations)

    def test_setup_py_package_relative_data_files_not_flagged(
        self, tmp_path: Path
    ) -> None:
        from frob.vet._supplychain import _python_install_artifact_violations

        (tmp_path / "setup.py").write_text(
            "from setuptools import setup\n"
            "setup(data_files=[('share/pkg', ['data.json'])])\n"
        )
        violations = _python_install_artifact_violations(tmp_path)
        assert violations == []

    def test_no_setup_py_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _python_install_artifact_violations

        assert _python_install_artifact_violations(tmp_path) == []


class TestSupplyChainCiActionPin:
    """T-1088: VET009, SC-DETECTION-UNPINNED-CI-ACTION."""

    def test_workflow_branch_ref_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_supplychain.py::_unpinned_ci_action_violations \
        # kind="unit"
        from frob.vet._supplychain import _unpinned_ci_action_violations

        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yaml").write_text(
            "jobs:\n  build:\n    steps:\n      - uses: actions/checkout@main\n"
        )
        violations = _unpinned_ci_action_violations(tmp_path)
        assert any(v.rule == "VET009" for v in violations)

    def test_workflow_full_sha_ref_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_ci_action_violations

        workflows = tmp_path / ".github" / "workflows"
        workflows.mkdir(parents=True)
        (workflows / "ci.yaml").write_text(
            "jobs:\n  build:\n    steps:\n"
            "      - uses: actions/checkout@"
            "8f4b7f84864484a7bde6ce6dbe0021e11a91c0f4\n"
        )
        violations = _unpinned_ci_action_violations(tmp_path)
        assert violations == []

    def test_no_workflows_dir_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _unpinned_ci_action_violations

        assert _unpinned_ci_action_violations(tmp_path) == []


class TestSupplyChainOpaqueBinaryArtifact:
    """T-1088: VET010, SC-DETECTION-OPAQUE-BINARY-ARTIFACT."""

    def test_tracked_so_without_recipe_flagged(self, tmp_path: Path) -> None:
        # frob:tests src/frob/vet/_supplychain.py::_opaque_binary_artifact_violations \
        # kind="unit"
        from frob.vet._supplychain import _opaque_binary_artifact_violations

        blob_dir = tmp_path / "vendor"
        blob_dir.mkdir()
        (blob_dir / "mystery.so").write_bytes(b"\x7fELF")
        violations = _opaque_binary_artifact_violations(tmp_path)
        assert any(v.rule == "VET010" for v in violations)

    def test_so_with_nearby_cargo_toml_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _opaque_binary_artifact_violations

        crate_dir = tmp_path / "native"
        crate_dir.mkdir()
        (crate_dir / "Cargo.toml").write_text('[package]\nname = "native"\n')
        (crate_dir / "built.so").write_bytes(b"\x7fELF")
        violations = _opaque_binary_artifact_violations(tmp_path)
        assert violations == []

    def test_no_binary_files_not_flagged(self, tmp_path: Path) -> None:
        from frob.vet._supplychain import _opaque_binary_artifact_violations

        (tmp_path / "readme.txt").write_text("hello\n")
        assert _opaque_binary_artifact_violations(tmp_path) == []
