"""End-to-end tests for `frob sys export` (T-0086): k8s/seccomp/iam config
skeletons rendered from a `.strata` design file, run against frob's own
self-hosting model (`design/frob.strata`, T-0081) since it is guaranteed to
be a real, parseable, elaboratable design already locked in CI
(tests/system/test_frob_self_model.py).
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from tests.system.conftest import run

_REPO_ROOT = Path(__file__).resolve().parents[2]
_MODEL_PATH = _REPO_ROOT / "design" / "frob.strata"


class TestCliSysExport:
    """End-to-end tests for the `frob sys export` CLI command."""

    def test_k8s_export_is_valid_yaml(self) -> None:
        """`frob sys export --format k8s` prints parseable multi-doc YAML
        with no stray log lines mixed into stdout."""
        result = run("sys", "export", "--format", "k8s", str(_MODEL_PATH))
        assert result.returncode == 0, result.stderr
        docs = list(yaml.safe_load_all(result.stdout))
        assert docs
        for doc in docs:
            assert doc["kind"] == "NetworkPolicy"

    def test_seccomp_export_is_valid_json(self) -> None:
        """`frob sys export --format seccomp` prints parseable JSON, one
        profile per component node."""
        result = run("sys", "export", "--format", "seccomp", str(_MODEL_PATH))
        assert result.returncode == 0, result.stderr
        profiles = json.loads(result.stdout)
        assert profiles
        for profile in profiles.values():
            assert profile["defaultAction"] == "SCMP_ACT_ERRNO"

    def test_iam_export_is_valid_json(self) -> None:
        """`frob sys export --format iam` prints parseable JSON with a
        statements list."""
        result = run("sys", "export", "--format", "iam", str(_MODEL_PATH))
        assert result.returncode == 0, result.stderr
        doc = json.loads(result.stdout)
        assert "statements" in doc

    def test_deterministic_across_two_processes(self) -> None:
        """Two separate `frob sys export` processes on the same design
        produce byte-identical stdout."""
        a = run("sys", "export", "--format", "k8s", str(_MODEL_PATH))
        b = run("sys", "export", "--format", "k8s", str(_MODEL_PATH))
        assert a.returncode == 0 and b.returncode == 0
        assert a.stdout == b.stdout

    def test_missing_design_file_errors(self, tmp_path) -> None:
        """A nonexistent design path is a clean error, not a traceback."""
        missing = tmp_path / "nope.strata"
        result = run("sys", "export", "--format", "iam", str(missing))
        assert result.returncode != 0

    def test_bad_format_errors(self) -> None:
        """An unsupported --format value is rejected by argparse."""
        result = run("sys", "export", "--format", "bogus", str(_MODEL_PATH))
        assert result.returncode != 0
