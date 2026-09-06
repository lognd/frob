"""T-3947: `frob.gates._ffi_boundary`'s FFI002 site (`_ffi002_violations`)
`rel` path (fed to `frob.excludes.is_excluded`/`is_test_file`) must be
POSIX-style regardless of platform. `str(path.relative_to(root))`
preserves the platform separator -- backslash on Windows -- which
silently broke both checks: `[graph].exclude` was never honored, and
test files were misclassified as production and scanned. Fixed at the
producer via `.as_posix()`, the same fix (and test pattern) T-3941
applied at `frob.xref.xref()`'s equivalent site, and T-3948 applied at
`_exhaustive_handling`'s equivalent site. FFI001's own `rel`/`rs_rel` are
display-only (message text), never compared, and are unaffected -- not
covered here.

A standalone module (not tests/gates_suite/test_compliance.py, where
this gate's other fixtures live) so this ticket's scope stays narrow --
that shared file's `frob:tests` directives fan out into dozens of
unrelated gates' source files via scope closure."""

from __future__ import annotations

from pathlib import Path, PureWindowsPath

from frob.gates._ffi_boundary import ffi_boundary_gate
from tests.conftest import _by_rule, _write

_CTYPES_SRC = 'import ctypes\nlib = ctypes.CDLL("libfoo.so")\nlib.do_thing(1)\n'


# frob:ticket T-3947
def test_exclude_glob_and_test_dir_are_honored_not_scanned_as_production(
    tmp_path: Path,
) -> None:
    """MUST-FIRE: the identical undeclared ctypes call is placed in a
    real production file, a `[graph].exclude`-matched directory, and a
    nested `tests/` directory. `is_excluded`/`is_test_file` both require
    a POSIX-style `rel` to work correctly (a nested directory is
    required -- a bare `test_*.py` filename would already be classified
    as a test by naming convention alone, which would not distinguish
    this bug). FFI002 must fire for the production copy only -- proving
    the gate scans the RIGHT set, the wrong-set failure mode T-3947
    describes (on Windows this gate used to scan the excluded/test
    copies as production instead of, or in addition to, the real
    production violation)."""
    _write(tmp_path, "frob.toml", '[graph]\nexclude = ["vendor/**"]\n')
    _write(tmp_path, "prod/sub/mod.py", _CTYPES_SRC)
    _write(tmp_path, "vendor/sub/mod.py", _CTYPES_SRC)
    _write(tmp_path, "tests/sub/test_mod.py", _CTYPES_SRC)

    violations = ffi_boundary_gate(tmp_path, tmp_path)
    found = _by_rule(violations, "FFI002")
    assert any(v.file == "prod/sub/mod.py" for v in found)
    assert not any(v.file.startswith("vendor/") for v in found)
    assert not any(v.file.startswith("tests/") for v in found)


# frob:ticket T-3947
def test_rel_path_fed_to_exclude_and_test_checks_is_posix_style(
    tmp_path: Path,
) -> None:
    """Path-shape contract (same pattern as T-3941's
    `test_definition_and_usage_file_fields_are_posix_style` for
    `frob.xref.xref`): a nested-directory FFI002 finding's `file` field
    (built from the same `rel` fed to `is_excluded`/`is_test_file`) is
    always forward-slash-separated -- a single-component path could not
    prove this, since it has no separator to get wrong."""
    _write(tmp_path, "pkg/sub/mod.py", _CTYPES_SRC)

    violations = ffi_boundary_gate(tmp_path, tmp_path)
    found = _by_rule(violations, "FFI002")
    assert found
    for v in found:
        assert v.file == "pkg/sub/mod.py"
        assert "\\" not in v.file


# frob:ticket T-3947
def test_windows_shaped_rel_path_mechanism() -> None:
    """Reproduces the exact pre-fix/post-fix mechanism with
    `PureWindowsPath` (no Windows machine available -- same method
    T-3941 used to prove PROFILE001's identical bug class, and T-3948's
    sibling fix at `_exhaustive_handling`'s equivalent site). Pre-fix
    (`str(a_relative_WindowsPath)`), a backslash-joined `rel` makes
    `is_excluded` fail to match a real `[graph].exclude` glob AND makes
    `is_test_file`'s `tests/` directory-component check see only one
    opaque part -- both silently wrong. Post-fix (`.as_posix()`), both
    are correct."""
    from frob.excludes import is_excluded, is_test_file

    root = PureWindowsPath("C:/repo")
    excluded_path = PureWindowsPath("C:/repo/vendor/sub/mod.py")
    test_path = PureWindowsPath("C:/repo/tests/sub/test_mod.py")

    pre_excl_rel = str(excluded_path.relative_to(root))
    post_excl_rel = excluded_path.relative_to(root).as_posix()
    pre_test_rel = str(test_path.relative_to(root))
    post_test_rel = test_path.relative_to(root).as_posix()

    assert is_excluded(pre_excl_rel, ("vendor/**",)) is False
    assert is_excluded(post_excl_rel, ("vendor/**",)) is True
    assert is_test_file(pre_test_rel) is False
    assert is_test_file(post_test_rel) is True
