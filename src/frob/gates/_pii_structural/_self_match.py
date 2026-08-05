"""Self-match exclusion for `pii_structural_gate` (T-0201/T-0539, T-1076
split of `frob.gates._pii_structural`): this gate's own detector-definition
sources, sibling detector pattern tables, and their dedicated test/fixture
files must never be scanned as if they were ordinary application code."""

from __future__ import annotations

from pathlib import Path

from frob.vet._capability import is_self_pattern_path

#: This package's own module paths relative to a repo root -- excluded from
#: scanning outright (T-0201 self-match lesson, package docstring). Compared
#: against the git-relative path `_tracked_python_files` yields. T-1076 split
#: `_pii_structural.py` into this package -- every sibling module needs the
#: same self-exclusion the single file used to get, not just `__init__.py`.
_SELF_EXCLUDED_FILES = frozenset(
    {
        f"src/frob/gates/_pii_structural/{name}"
        for name in (
            "__init__.py",
            "_tracked.py",
            "_self_match.py",
            "_signatures.py",
            "_declared_surface.py",
            "_python_fields.py",
            "_emails.py",
            "_keywords.py",
            "_env_access.py",
            "_crosslang.py",
        )
    }
)

# T-0539: the PII011/PII012 warn-pool histogram showed the overwhelming
# majority of findings landing on this gate's OWN detector-definition
# sources, the sibling secrets/fingerprint detectors' pattern tables, and
# those detectors' DEDICATED test/fixture files -- the exact self-match
# class T-0253's `is_self_pattern_path` discriminator already solved for
# `frob.vet._capability`'s SYS100 (a static-analysis tool's own keyword/
# needle tables and the tests that assert those tables fire legitimately
# CONTAIN the keyword text they detect). Reused here via `is_self_pattern_
# path`'s new `suffixes` parameter -- the SAME root-identity-gated
# discriminator (`_is_frob_repo_root` + path-suffix match), a second
# suffix list, not a second implementation. A genuine keyword hit in
# ordinary application code is NOT in this list and still fires.
_PII_SELF_PATTERN_SUFFIXES: tuple[tuple[str, ...], ...] = (
    # T-1076: `_pii_structural.py` split into this package -- one suffix
    # entry per sibling module, same self-match posture the single file
    # used to get as a whole.
    ("frob", "gates", "_pii_structural", "__init__.py"),
    ("frob", "gates", "_pii_structural", "_tracked.py"),
    ("frob", "gates", "_pii_structural", "_self_match.py"),
    ("frob", "gates", "_pii_structural", "_signatures.py"),
    ("frob", "gates", "_pii_structural", "_declared_surface.py"),
    ("frob", "gates", "_pii_structural", "_python_fields.py"),
    ("frob", "gates", "_pii_structural", "_emails.py"),
    ("frob", "gates", "_pii_structural", "_keywords.py"),
    ("frob", "gates", "_pii_structural", "_env_access.py"),
    ("frob", "gates", "_pii_structural", "_crosslang.py"),
    ("frob", "gates", "_secrets.py"),
    ("frob", "strata", "_secrets.py"),
    ("frob", "security", "_redact.py"),
    ("frob", "gates", "_cve_fingerprint_scan.py"),
    ("frob", "strata", "_cve_fingerprint.py"),
    ("tests", "test_secrets_gate.py"),
    ("tests", "unit", "security", "test_redact.py"),
    ("tests", "test_pii_structural_gate.py"),
    ("tests", "unit", "strata", "test_secrets.py"),
    ("tests", "unit", "strata", "test_cve_fingerprint_scan.py"),
    ("tests", "unit", "strata", "test_compliance.py"),
    ("tests", "unit", "strata", "test_litmus_deploy_secret.py"),
)


def _is_pii_self_pattern_file(root: Path, rel_path: str) -> bool:
    """Whether `rel_path` (root-relative) is a PII011/PII012 detector-
    definition/pattern-table/corpus/fixture self-match file (T-0539),
    via the shared `is_self_pattern_path` discriminator gated on `root`
    actually being frob's own repo checkout -- never true when scanning
    a third-party tree (e.g. `frob vet`'s dependency scan, if this gate
    is ever reused there)."""
    return is_self_pattern_path(
        root / rel_path, root, suffixes=_PII_SELF_PATTERN_SUFFIXES
    )
