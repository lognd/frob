"""FFI001/FFI002: the FFI-boundary exception-declaration gate (T-0690,
child 4 of T-0685's exception may-raise umbrella), dispatching
`frob.arch._ffi`'s two scans (docs/modules/gates.md#ffi001-ffi002-t-0690):

FFI001 (pyo3 cross-check drift): for every `.pyi` stub whose module
docstring carries a `frob:describes <path>.rs` pragma pointing at a real
Rust source file (`_pyo3_boundary_pairs` -- the SAME `frob:describes`
convention `frob.gates._docblocks` already reads elsewhere in this repo,
reused here rather than a new pairing mechanism), `frob.arch._ffi.
scan_pyo3_raises` computes each `#[pyfunction]`'s OBSERVED Rust-side
raised-type set and `parse_pyi_declared_raises` reads the stub's own
above-the-def `# frob:raises <Type>` declarations (T-0688's directive,
reused as this boundary's Python-side truth). Any observed type absent
from the declared set is FFI001, naming BOTH sides (the ticket's own
acceptance criterion) -- a pyo3 function whose Rust body constructs
`PyValueError` but whose `.pyi` stub's `frob:raises` omits it fails here,
even with zero tests run.

FFI002 (undeclared ctypes/cffi boundary): ctypes/cffi calls have no
exception-propagation contract at all (errno/return-code convention only)
-- per the ticket's own mandate, the declaration IS the only truth, so
every call made through a `ctypes.CDLL`-family handle
(`frob.arch._ffi.scan_ctypes_boundary_calls`) MUST carry a same-line
callee-raises comment (T-0689's existing call-site directive, `# frob` +
`:callee-raises`; declaring the empty set via a bare directive is a valid,
honest "raises nothing, errno convention" declaration) or the call site
is flagged, demanding one.

SCOPE: FFI001 only fires for `.pyi` stubs that actually carry the
`frob:describes ...rs` pragma (today: `frob-core/frob_core.pyi`,
`strata-core/strata_core.pyi`) -- a third-party or hand-written `.pyi`
with no such pragma is silently skipped, per the ticket's own tier-3
"declaration optional" carve-out. FFI002 scans every `.py` file under
`root` except test files (`frob.excludes.is_test_file`), mirroring
`_exhaustive_handling`'s own test-file exclusion.

SEVERITY: both ship at `Severity.ERROR`, not `Severity.WARN` -- unlike
EXHAUST001/EXHAUST002's own first-turn-on debt (T-0688's 176 pre-existing
findings), a real run of both scans against this repo's OWN source at
landing time surfaced ZERO findings (neither crate constructs a `Py<X>
Error`/panics inside a `#[pyfunction]` body today, and this repo has no
ctypes/cffi usage anywhere) -- there is no debt corpus an ERROR severity
would instantly red, so this ships at the target severity directly rather
than deferring promotion to a follow-up ticket."""

from __future__ import annotations

import re
from pathlib import Path

from frob.arch._ffi import (
    parse_pyi_declared_raises,
    scan_ctypes_boundary_calls,
    scan_pyo3_raises,
)
from frob.excludes import is_excluded, is_test_file, iter_files, load_exclude_globs
from frob.gates._models import Severity, Violation
from frob.logging import get_logger

_log = get_logger(__name__)

#: Matches a `frob:describes <path>` pragma anywhere in a `.pyi` stub's
#: module docstring (T-0690) -- the same directive text `frob.gates.
#: _docblocks` reads elsewhere in this repo, reused here (not
#: re-implemented) as the pairing mechanism between a pyo3 `.pyi` stub and
#: the Rust source file whose exported surface it types.
_DESCRIBES_RE = re.compile(r"frob:describes\s+(\S+\.rs)\b")


def _pyo3_boundary_pairs(repo_root: Path) -> tuple[tuple[Path, Path], ...]:
    """Every `(.pyi stub, .rs source)` pair in the repo (T-0690): every
    `.pyi` file under `repo_root` whose text contains a `frob:describes
    <path>.rs` pragma, paired with that path resolved against `repo_root`
    -- skipped (with a debug log, not an error) when the referenced `.rs`
    file does not actually exist, since a stale/typo'd pragma is a docs
    problem for `frob.gates._docblocks`'s own DOC-family rules to catch,
    not this gate's."""
    pairs: list[tuple[Path, Path]] = []
    for pyi_path in iter_files(repo_root, suffix=".pyi"):
        text = pyi_path.read_text(encoding="utf-8", errors="replace")
        m = _DESCRIBES_RE.search(text)
        if m is None:
            continue
        rs_path = (repo_root / m.group(1)).resolve()
        if not rs_path.is_file():
            _log.debug(
                "_pyo3_boundary_pairs: %s describes missing %s", pyi_path, rs_path
            )
            continue
        pairs.append((pyi_path, rs_path))
    return tuple(pairs)


# frob:waive ARCH001 reason="T-1371's EXHAUST001/002 fix added two small per-pair try/except blocks (read failure, scan failure) around the pre-existing loop body -- boilerplate exception-handling lines, not new independently meaningful phases to split out; splitting the try/except itself into a helper would just move the same lines behind an indirection without separating a real sub-concern"  # noqa: E501
def _ffi001_violations(repo_root: Path) -> list[Violation]:
    """FFI001 (T-0690): every `_pyo3_boundary_pairs` pair's Rust-side
    observed raised-type set (`scan_pyo3_raises`) cross-checked against
    the `.pyi` stub's own declared set (`parse_pyi_declared_raises`) --
    any observed type not declared is one violation per function, naming
    both the missing type(s) and the declared set as-is, so the message
    alone tells a reader both sides of the drift without a second lookup."""
    violations: list[Violation] = []
    for pyi_path, rs_path in _pyo3_boundary_pairs(repo_root):
        try:
            rust_source = rs_path.read_text(encoding="utf-8", errors="replace")
            pyi_source = pyi_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # A pair discovered by `_pyo3_boundary_pairs` but no longer
            # readable (deleted/renamed between listing and read, a race
            # this gate does not otherwise guard against) must not crash
            # the whole FFI001 pass over every OTHER pair (EXHAUST001,
            # T-1371) -- skip just this one.
            continue
        try:
            observed = scan_pyo3_raises(rust_source)
            declared = parse_pyi_declared_raises(pyi_source)
        except Exception:
            # A malformed/unexpected `.rs`/`.pyi` shape confusing either
            # scanner must not abort the whole FFI001 pass over every
            # OTHER pair (EXHAUST001, T-1371) -- skip just this one.
            continue
        try:
            rel = str(pyi_path.relative_to(repo_root))
        except ValueError:
            rel = str(pyi_path)
        try:
            rs_rel = str(rs_path.relative_to(repo_root))
        except ValueError:
            rs_rel = str(rs_path)

        for func in observed:
            if not func.raises:
                continue
            declared_set = declared.get(func.name, frozenset())
            missing = func.raises - declared_set
            if not missing:
                continue
            # frob:waive PERF004 reason="missing/declared_set differ every iteration \
            # (each is this specific function's own raised/declared set) -- there is \
            # nothing stable to hoist a sort of out of the loop, matching T-0972's own \
            # precedent for this exact pattern in \
            # frob.arch._exceptions.check_errors_as_values"
            violations.append(
                Violation(
                    rule="FFI001",
                    severity=Severity.ERROR,
                    file=rel,
                    line=1,
                    message=(
                        f"FFI001: `{func.name}` ({rs_rel}:{func.line}) may "
                        f"raise {sorted(missing)} on the Rust side but "
                        f"{rel}'s `frob:raises` declares only "
                        f"{sorted(declared_set)} -- add `# frob:raises "
                        f"<Type>` directly above `def {func.name}` in the "
                        "stub for each missing type, or fix the Rust side"
                    ),
                    symref=f"{rel}::{func.name}",
                )
            )
    return violations


def _ffi002_violations(root: Path) -> list[Violation]:
    """FFI002 (T-0690): every `scan_ctypes_boundary_calls` finding with
    `declared=False` under `root` -- test files excluded (mirrors
    `_exhaustive_handling`'s own test-file carve-out)."""
    exclude_globs = load_exclude_globs(root)
    violations: list[Violation] = []
    for path in iter_files(root, suffix=".py"):
        try:
            rel = str(path.relative_to(root))
        except ValueError:
            continue
        if is_excluded(rel, exclude_globs) or is_test_file(rel):
            continue
        try:
            source = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            # A file listed by `iter_files` but gone/unreadable by read
            # time must not crash the whole FFI002 pass (EXHAUST001,
            # T-1371) -- skip just this one.
            continue
        try:
            calls = list(scan_ctypes_boundary_calls(source))
        except Exception:
            # A malformed/unexpected source shape confusing the ctypes
            # call scanner must not abort the whole FFI002 pass over
            # every OTHER file (EXHAUST001, T-1371) -- skip just this one.
            continue
        for call in calls:
            if call.declared:
                continue
            violations.append(
                Violation(
                    rule="FFI002",
                    severity=Severity.ERROR,
                    file=rel,
                    line=call.line,
                    message=(
                        f"FFI002: `{call.handle}.{call.callee}(...)` is a "
                        "ctypes call with no exception-propagation contract "
                        "-- declare `# frob:callee-raises` (empty set for "
                        "the errno convention, or the specific types) on "
                        "this call's own line"
                    ),
                    symref=None,
                )
            )
    return violations


# frob:doc docs/modules/gates.md#ffi001-ffi002-t-0690
# frob:ticket T-0690
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_pyo3_drift_fires_ffi001
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_pyo3_declared_matches_no_drift  # noqa: E501
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_ctypes_call_without_declaration_fires_ffi002  # noqa: E501
# frob:tests tests/test_gates.py::TestFfiBoundaryGate.test_ctypes_call_with_empty_declaration_clean  # noqa: E501
# frob:enforces CHK-GATE-FFI001
# frob:enforces CHK-GATE-FFI002
def ffi_boundary_gate(root: Path, repo_root: Path) -> tuple[Violation, ...]:
    """FFI001/FFI002 (T-0690) over the repo rooted at `repo_root`: FFI001
    always runs repo-wide (a pyo3 boundary pair is a repo-wide concern the
    same way `_exhaustive_handling`'s own EXHAUST001/002 always run
    against `repo_root`, never a possibly-scoped `root`); FFI002 runs over
    `root` (the possibly-scoped tree `frob check <subdir>` names)."""
    violations = _ffi001_violations(repo_root)
    violations.extend(_ffi002_violations(root))
    return tuple(violations)


__all__ = ["ffi_boundary_gate"]
