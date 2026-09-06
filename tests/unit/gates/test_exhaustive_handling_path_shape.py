"""T-3948: `frob.gates._exhaustive_handling.exhaustive_handling_gate`'s
`rel` path (fed to `frob.excludes.is_excluded`/`is_test_file`) must be
POSIX-style regardless of platform. `str(path.relative_to(root))`
preserves the platform separator -- backslash on Windows -- which
silently broke both checks: `[graph].exclude` was never honored, and
test files were misclassified as production and scanned. Fixed at the
producer via `.as_posix()`, the same fix (and test pattern) T-3941
applied at `frob.xref.xref()`'s equivalent site, and T-3947 applied at
`_ffi_boundary`'s equivalent site.

A standalone module (not tests/gates_suite/test_compliance.py, where
this gate's other fixtures live) so this ticket's scope stays narrow --
that shared file's `frob:tests` directives fan out into dozens of
unrelated gates' source files via scope closure."""

from __future__ import annotations

from pathlib import Path

from frob.gates._exhaustive_handling import exhaustive_handling_gate
from tests.conftest import _by_rule, _write
from tests.unit.gates.test_ffi_boundary_path_shape import (
    test_windows_shaped_rel_path_mechanism as _shared_windows_mechanism_test,
)

_BOUNDARY_SRC = (
    "def risky():\n"
    "    raise TypeError('bad')\n"
    "\n"
    "def boundary():\n"
    "    try:\n"
    "        risky()\n"
    "    except ValueError:\n"
    "        pass\n"
)


# frob:ticket T-3948
def test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production(
    tmp_path: Path,
) -> None:
    """MUST-FIRE: the identical genuine boundary is placed in a real
    production file, a `[graph].exclude`-matched directory, and a nested
    `tests/` directory. `is_excluded`/`is_test_file` both require a
    POSIX-style `rel` to work correctly (a nested directory is required
    here -- a bare `test_*.py` filename would already be classified as a
    test by naming convention alone, which would not distinguish this
    bug). EXHAUST002 must fire for the production copy only -- proving
    the gate scans the RIGHT set, the wrong-set failure mode T-3948
    describes (on Windows this gate used to scan the excluded/test
    copies as production instead of, or in addition to, missing the
    real production violation)."""
    _write(tmp_path, "frob.toml", '[graph]\nexclude = ["vendor/**"]\n')
    _write(tmp_path, "prod/sub/mod.py", _BOUNDARY_SRC)
    _write(tmp_path, "vendor/sub/mod.py", _BOUNDARY_SRC)
    _write(tmp_path, "tests/sub/test_mod.py", _BOUNDARY_SRC)

    violations = exhaustive_handling_gate(tmp_path)
    found = _by_rule(violations, "EXHAUST002")
    assert any(v.symref == "prod/sub/mod.py::boundary" for v in found)
    assert not any(v.symref.startswith("vendor/") for v in found)
    assert not any(v.symref.startswith("tests/") for v in found)


# frob:ticket T-3948
def test_rel_path_fed_to_exclude_and_test_checks_is_posix_style(
    tmp_path: Path,
) -> None:
    """Path-shape contract (same pattern as T-3941's
    `test_definition_and_usage_file_fields_are_posix_style` for
    `frob.xref.xref`): a nested-directory finding's `symref`/`file`
    (built from the same `rel` fed to `is_excluded`/`is_test_file`) is
    always forward-slash-separated -- a single-component path could not
    prove this, since it has no separator to get wrong."""
    _write(tmp_path, "pkg/sub/mod.py", _BOUNDARY_SRC)

    violations = exhaustive_handling_gate(tmp_path)
    found = _by_rule(violations, "EXHAUST002")
    assert found
    for v in found:
        assert v.file == "pkg/sub/mod.py"
        assert "\\" not in v.file
        assert v.symref is not None and "\\" not in v.symref


# frob:ticket T-3948
def test_windows_shaped_rel_path_mechanism() -> None:
    """T-3948 binds T-3947's own `test_windows_shaped_rel_path_mechanism`
    (tests/unit/gates/test_ffi_boundary_path_shape.py) as its own
    evidence too, by calling it directly, rather than duplicating its
    body (DUP001: both tickets fix the identical `frob.excludes`
    contract violation the same way -- `is_excluded`/`is_test_file` both
    require a POSIX-style `rel`, proven the same way for both). See that
    function's own docstring for what the mechanism proof covers."""
    _shared_windows_mechanism_test()
