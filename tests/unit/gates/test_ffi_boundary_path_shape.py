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
unrelated gates' source files via scope closure.

T-4102: `test_windows_shaped_rel_path_mechanism` below originally
asserted a false premise (it predicted `os.path.normcase`-under-Windows
behaviour from a `PureWindowsPath` run on Linux, which does not
simulate the stdlib) -- see that function's own docstring."""

from __future__ import annotations

from pathlib import Path

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


# frob:ticket T-4102
def test_windows_shaped_rel_path_mechanism() -> None:
    """T-4102: this fixture used to reproduce the pre-fix/post-fix
    mechanism with `PureWindowsPath` and assert `is_excluded` returns
    `False` for a backslash-joined `rel` against a POSIX glob. That
    claim was true on Linux (where `fnmatch.normcase` is the identity
    function) but FALSE on real Windows (`fnmatch.fnmatch`, excludes.py's
    old matcher, runs BOTH operands through `os.path.normcase`, which
    turns the glob's `/` into `\\` on Windows -- so the backslash path
    incidentally MATCHED). `PureWindowsPath` simulates Windows PATH
    SHAPES; it does not simulate the Windows STDLIB, so this was never
    provable from Linux -- exactly the trap this ticket exists to
    document (do not repeat it: MEMORY.md).

    T-4102 migrated `is_excluded` to pathspec's gitwildmatch dialect,
    which never normcases either operand, so the matching question is no
    longer platform-conditional at all: the same (rel, glob) pair
    answers identically everywhere. What is actually true and actually
    worth asserting is that directly, plus the specific failure mode
    (case-folding) `os.path.normcase` used to introduce -- not a
    prediction of what a Windows library would do, run from Linux.

    `is_test_file`'s own `tests/` directory-component check is unrelated
    to this bug: it parses via `PurePosixPath`, which never consults
    `os.path`, so it was never platform-dependent -- see
    `test_rel_path_fed_to_exclude_and_test_checks_is_posix_style` for its
    POSIX-`rel` coverage."""
    from frob.excludes import is_excluded

    # A POSIX-shaped rel (what the producers now emit via `.as_posix()`)
    # matches its glob the same way on every platform -- pathspec never
    # consults `os.path`, so there is no platform for the answer to vary
    # by.
    assert is_excluded("vendor/sub/mod.py", ("vendor/**",)) is True

    # A backslash-joined rel (what a naive `str(a_relative_path)` would
    # have produced pre-`.as_posix()`) never matches a POSIX-shaped glob,
    # on ANY platform: gitwildmatch treats `\\` as a literal character,
    # never a path separator, and performs no normcase step. This is the
    # replacement for the false pre-fix/post-fix claim above -- true
    # unconditionally, not true-on-Linux-only.
    assert is_excluded("vendor\\sub\\mod.py", ("vendor/**",)) is False

    # THIRD FIXTURE (ticket T-4102): a glob and a path differing only in
    # case never match, proving there is no `os.path.normcase` dependence
    # left. `fnmatch.fnmatch` case-folded on Windows and on
    # case-insensitive filesystems' `normcase`, silently making
    # `[graph].exclude` mean different things per platform for the exact
    # same repo config.
    assert is_excluded("Vendor/sub/mod.py", ("vendor/**",)) is False
    assert is_excluded("vendor/sub/mod.py", ("Vendor/**",)) is False
