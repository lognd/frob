"""T-0439: `scan_text_for_fingerprints` (`frob.strata._cve_fingerprint`)
and its gate wrapper `cve_fingerprint_scan_gate`
(`frob.gates._cve_fingerprint_scan`) -- the first-party repo-lint sibling
of `check_fingerprint_catalog_drift` (CVEFP001, catalog-only) and
`frob.vet._capability._scan_file_fingerprints` (third-party dependency
source, no line info), docs/strata/threat.md#cve-fingerprints-code-level-
pattern-catalog-t-0153.

Litmus pair (module docstring's non-vacuous requirement): a "smelly" text
containing a real fingerprint needle fires; a "clean" text using the safe
alternative for the exact same operation does not.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from frob.gates._cve_fingerprint_scan import cve_fingerprint_scan_gate
from frob.strata._cve_fingerprint import CveFingerprint, scan_text_for_fingerprints

_SMELLY_PYTHON = "subprocess.run(cmd, shell=True)\n"
_CLEAN_PYTHON = 'subprocess.run(["ls", "-la"], shell=False)\n'

_FINGERPRINTS = (
    CveFingerprint(
        id="FP-TEST-001",
        title="test fingerprint",
        cve=("CVE-2014-6271",),
        cwe_id="CWE-78",
        language="python",
        needles=("shell=True",),
        remediation="pass args as a list with shell=False",
    ),
)


class TestScanTextForFingerprints:
    """`scan_text_for_fingerprints` (`frob.strata._cve_fingerprint`)."""

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints.test_smelly_text_fires  # noqa: E501
    def test_smelly_text_fires(self):
        hits = scan_text_for_fingerprints(_SMELLY_PYTHON, "python", _FINGERPRINTS)
        assert len(hits) == 1
        assert hits[0].fingerprint_id == "FP-TEST-001"
        assert hits[0].cwe_id == "CWE-78"
        assert hits[0].line == 1
        assert hits[0].needle == "shell=True"

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints.test_clean_text_does_not_fire  # noqa: E501
    def test_clean_text_does_not_fire(self):
        hits = scan_text_for_fingerprints(_CLEAN_PYTHON, "python", _FINGERPRINTS)
        assert hits == ()

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints.test_wrong_language_does_not_fire  # noqa: E501
    def test_wrong_language_does_not_fire(self):
        hits = scan_text_for_fingerprints(_SMELLY_PYTHON, "rust", _FINGERPRINTS)
        assert hits == ()

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints.test_multiple_occurrences_each_reported  # noqa: E501
    def test_multiple_occurrences_each_reported(self):
        text = "a(shell=True)\nb(shell=True)\n"
        hits = scan_text_for_fingerprints(text, "python", _FINGERPRINTS)
        assert [h.line for h in hits] == [1, 2]

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestScanTextForFingerprints.test_real_catalog_pickle_needle_fires  # noqa: E501
    def test_real_catalog_pickle_needle_fires(self):
        """Sanity check against the REAL shipped `CVE_FINGERPRINTS` catalog
        (default arg), not just the local test fixture above."""
        hits = scan_text_for_fingerprints("x = pickle.loads(data)\n", "python")
        ids = {h.fingerprint_id for h in hits}
        assert "FP-DESERIALIZE-PICKLE-001" in ids


def _init_git_repo(tmp_path: Path) -> Path:
    """A minimal git repo with tracked files for `cve_fingerprint_scan_gate`
    (which shells out to `git ls-files`) -- same arrange shape
    `tests/test_walk_lint_gate.py`/`tests/test_secrets_gate.py` use for
    their own gates."""
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"], cwd=repo, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    return repo


def _commit_all(repo: Path) -> None:
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "init"], cwd=repo, check=True)


class TestGate:
    """`cve_fingerprint_scan_gate` (`frob.gates._cve_fingerprint_scan`) --
    the real `frob check` entrypoint, over an actual git-tracked file (not
    a direct `scan_text_for_fingerprints` call), against the REAL shipped
    `CVE_FINGERPRINTS` catalog."""

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_smelly_file_fires
    def test_smelly_file_fires(self, tmp_path: Path):
        repo = _init_git_repo(tmp_path)
        (repo / "smelly.py").write_text(_SMELLY_PYTHON, encoding="utf-8")
        _commit_all(repo)

        violations = cve_fingerprint_scan_gate(repo)
        assert len(violations) == 1
        assert violations[0].rule == "SEC-CVE-FINGERPRINT-001"
        assert violations[0].file == "smelly.py"
        assert violations[0].line == 1
        assert "FP-EXEC-SHELL-001" in violations[0].message

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_clean_file_does_not_fire  # noqa: E501
    def test_clean_file_does_not_fire(self, tmp_path: Path):
        repo = _init_git_repo(tmp_path)
        (repo / "clean.py").write_text(_CLEAN_PYTHON, encoding="utf-8")
        _commit_all(repo)

        violations = cve_fingerprint_scan_gate(repo)
        assert violations == ()

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_self_excluded_files_not_scanned  # noqa: E501
    def test_self_excluded_files_not_scanned(self, tmp_path: Path):
        """This gate's own module + `_cve_fingerprint.py` both legitimately
        contain every needle as literal DATA (the catalog itself, this
        gate's own docstring) -- self-excluded so the gate is not
        permanently, unfixably noisy against its own source."""
        repo = _init_git_repo(tmp_path)
        src = repo / "src" / "frob" / "gates"
        src.mkdir(parents=True)
        real = Path("src/frob/gates/_cve_fingerprint_scan.py").read_text(
            encoding="utf-8"
        )
        (src / "_cve_fingerprint_scan.py").write_text(real, encoding="utf-8")
        _commit_all(repo)

        violations = cve_fingerprint_scan_gate(repo)
        assert violations == ()

    # frob:tests tests/unit/strata/test_cve_fingerprint_scan.py::TestGate.test_unscanned_extension_is_silent  # noqa: E501
    def test_unscanned_extension_is_silent(self, tmp_path: Path):
        repo = _init_git_repo(tmp_path)
        (repo / "smelly.md").write_text(_SMELLY_PYTHON, encoding="utf-8")
        _commit_all(repo)

        violations = cve_fingerprint_scan_gate(repo)
        assert violations == ()
