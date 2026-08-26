"""T-2917: CI ran ubuntu-latest only, so no platform regression (Windows or
macOS) could ever be detected -- locks that the `build` job's matrix
includes windows-latest and macos-latest alongside ubuntu-latest.
"""

from pathlib import Path

import yaml


def _load_ci_workflow() -> dict:
    """Parse .github/workflows/ci.yml (frob:tests target) into a dict."""
    text = (
        Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci.yml"
    ).read_text(encoding="utf-8")
    return yaml.safe_load(text)


class TestCiBuildMatrixCoversAllThreePlatforms:
    """T-2917: a single-OS CI matrix cannot detect a platform regression."""

    def test_build_job_declares_a_matrix_strategy(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        build_job = workflow["jobs"]["build"]
        assert "strategy" in build_job, (
            "build job has no matrix strategy -- it can only ever run on "
            "one OS, so a Windows- or macOS-only regression is undetectable"
        )
        assert build_job["runs-on"] == "${{ matrix.os }}"

    def test_build_matrix_includes_windows_and_macos(self) -> None:
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        matrix_os = workflow["jobs"]["build"]["strategy"]["matrix"]["os"]
        assert "ubuntu-latest" in matrix_os
        assert "windows-latest" in matrix_os
        assert "macos-latest" in matrix_os

    def test_build_matrix_is_fail_fast_false(self) -> None:
        """A single early platform failure must not hide the others' results."""
        # frob:tests .github/workflows/ci.yml
        workflow = _load_ci_workflow()
        strategy = workflow["jobs"]["build"]["strategy"]
        assert strategy.get("fail-fast") is False
