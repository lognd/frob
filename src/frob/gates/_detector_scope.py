"""`DETECTOR_PACKAGE_ROOTS`: the one shared declaration of which packages
can contain a GATE-SHAPED DETECTOR -- code that decides a finding and
constructs a `Violation`-named object (T-2466, filed from T-2457's own
Done report).

WHY THIS EXISTS. Two meta-checks police detector QUALITY from raw text:
LEXCHECK001 (`_lexical_selfcheck.py`, "did a detector decide from a
regex/substring match with no symref") and PORT001
(`_port_selfcheck.py`, "did a detector hardcode this project's own
identity"). Both used to scope themselves to `src/frob/gates/**` only,
each via its OWN hardcoded prefix check
(`rel.startswith("src/frob/gates/")`). T-2457 shipped and survived
review specifically because LEXCHECK001's scope was narrower than the
class of code it polices: the `fs.write` capability detector doing
`bytes.find` substring matching lived in `src/frob/vet/_capability_
core.py`, which LEXCHECK001 never examined at all -- its own "0
findings" read as "no detector does lexical matching" when it actually
meant "no detector IN src/frob/gates DOES". A meta-check's green result
is only as trustworthy as its own disclosed scope (`docs/modules/
gates.md#lexcheck001-t-2344`'s own "must-report-scope" requirement,
mirroring PORT001's T-2388 convention).

MEASURED (T-2466), not guessed -- `git grep -c "Violation("` (any
`Violation`-suffixed constructor call, the same AST-detectable shape
LEXCHECK001/PORT001 already match on) restricted to each candidate
package:

    src/frob/gates/**   -- yes  (the population these gates already scan)
    src/frob/vet/**     -- yes  (T-2457's own proof: _capability_core.py,
                            _capability.py, _scan.py, _scan_violations.py,
                            _ecosystem.py, _supplychain.py, _models.py)
    src/frob/strata/**  -- yes  (33+ modules construct Violation(...),
                            e.g. _selfconform.py, _threat.py, _pii.py)
    src/frob/check/**   -- yes  (_python.py)
    src/frob/arch/**    -- NO, measured zero `Violation(`-shaped
                            constructor calls anywhere in the package at
                            T-2466 time -- excluded on that basis, not by
                            assumption; re-measure if `arch/` later grows
                            a detector (this tuple is the place to add it,
                            not a fresh hardcoded prefix at the call site).

TWO CONSUMERS, ONE DECLARATION (T-2466's own coordinator directive: "two
hardcoded scopes will drift apart, and that drift is this bug again").
LEXCHECK001 is the first consumer (this ticket). PORT001's own widening
(T-2405, filed separately, not touched here) is expected to import this
SAME tuple rather than hardcode its own -- see that ticket for its own
scope decision once it lands; this module's job is only to give it
something correct to import instead of a second copy to invent.
`tracked_python_files_for_gate` (`_walk_lint.py`, T-0861) already
enumerates every git-tracked `src/frob/**/*.py` file un-scoped; a
detector-scoped gate filters that shared list down to this tuple's
prefixes rather than re-invoking git itself."""

from __future__ import annotations

from pathlib import Path
from typing import Final

from frob.gates._walk_lint import tracked_python_files_for_gate

# frob:doc docs/modules/gates.md#lexcheck001-t-2344
# frob:tests tests/unit/gates/test_detector_scope.py::TestDetectorScope.test_gates_vet_strata_check_are_members kind="unit"  # noqa: E501
# frob:tests tests/unit/gates/test_detector_scope.py::TestDetectorScope.test_arch_is_not_a_member kind="unit"  # noqa: E501
# frob:tests tests/unit/gates/test_detector_scope.py::TestDetectorScope.test_roots_are_sorted_and_slash_terminated kind="unit"  # noqa: E501
#: Every package-root prefix (POSIX, trailing slash, relative to repo
#: root) that can contain a gate-shaped detector, per this module's own
#: docstring measurement. Sorted for a deterministic, reviewable diff
#: order; membership is a plain `str.startswith` test against one of
#: these prefixes, mirroring `tracked_python_files_for_gate`'s own
#: existing `src/frob/gates/` convention (never a glob engine -- these
#: are directory prefixes, not `**` patterns).
DETECTOR_PACKAGE_ROOTS: Final[tuple[str, ...]] = (
    "src/frob/check/",
    "src/frob/gates/",
    "src/frob/strata/",
    "src/frob/vet/",
)


# frob:doc docs/modules/gates.md#lexcheck001-t-2344
# frob:tests tests/unit/gates/test_detector_scope.py::TestDetectorScope.test_unrelated_package_is_not_a_member kind="unit"  # noqa: E501
def is_detector_package_file(rel_path: str) -> bool:
    """Whether `rel_path` (a repo-root-relative POSIX path, as returned by
    `tracked_python_files_for_gate`) sits under one of `DETECTOR_PACKAGE_
    ROOTS` -- the ONE membership test every detector-scoped meta-check
    should call, so widening the roots tuple widens every caller
    identically instead of needing a per-caller edit."""
    return rel_path.startswith(DETECTOR_PACKAGE_ROOTS)


# frob:doc docs/modules/gates.md#lexcheck001-t-2344
# frob:tests tests/unit/gates/test_detector_scope.py::TestDetectorScope.test_tracked_gate_files_filters_to_detector_roots kind="unit"  # noqa: E501
# frob:ticket T-2966
def tracked_gate_files(root: Path, log_prefix: str) -> tuple[str, ...]:
    """Every git-tracked `.py` file under one of `DETECTOR_PACKAGE_ROOTS`,
    reusing `tracked_python_files_for_gate` (T-0861) and filtering to
    `is_detector_package_file` -- the single home for the byte-identical
    body PORT001 (`_port_selfcheck.py`) and LEXCHECK001
    (`_lexical_selfcheck.py`) each carried as a private copy before
    T-2966 extracted it (both modules' own docstrings called this
    composition "expected to reuse rather than re-hardcode")."""
    return tuple(
        rel
        for rel in tracked_python_files_for_gate(root, log_prefix=log_prefix)
        if is_detector_package_file(rel)
    )


# frob:doc docs/modules/gates.md#port001-t-2388
# frob:tests tests/unit/gates/test_detector_scope.py::TestDetectorScope.test_tracked_repo_python_files_is_repo_wide_not_detector_scoped kind="unit"  # noqa: E501
# frob:ticket T-3275
def tracked_repo_python_files(root: Path, log_prefix: str) -> tuple[str, ...]:
    """Every git-tracked `src/frob/**/*.py` file, UNFILTERED by
    `DETECTOR_PACKAGE_ROOTS` (T-3275) -- the population PORT001 scans,
    distinct from `tracked_gate_files`'s detector-scoped population.

    WHY A SEPARATE POPULATION, MEASURED (T-3275), not guessed: this
    module's own `DETECTOR_PACKAGE_ROOTS` answers "is this file a
    gate-shaped DETECTOR" (does it construct `Violation(...)`).
    PORT001's defect class asks a different question -- "can this file
    embed THIS project's own identity as a literal instead of resolving
    it from config" -- and the two sets are not the same. `git grep -c
    '"src/frob' -- 'src/**/*.py'` (T-3275, 2026-08-29) found 31 files
    across SEVEN top-level packages: `gates` (17), `strata` (6),
    `tickets` (3), `app` (2), `testing` (1), `refactor` (1), `lang` (1).
    Four of those seven -- `tickets/`, `app/`, `testing/`, `refactor/`,
    `lang/` -- are NOT `DETECTOR_PACKAGE_ROOTS` members (T-2466 measured
    zero `Violation(`-constructing modules in each); `testing/
    _coverage_refresh.py`'s own hardcoded `_DEFAULT_COV_TARGET =
    "src/frob"` (T-3275's own originating defect, FROBLEMS.md F-011) is
    exactly this: identity hardcoded in a module that constructs no
    Violation and detects nothing. Unlike T-2466's `arch/` exclusion
    (measured zero on a structural, AST-detectable feature and excluded
    ON that evidence), no package here can be proven safe the same way:
    "does this module ever resolve a path or a project-scoped default"
    is not a bounded, package-scoped property the way "does this module
    construct a Violation" is -- any package could gain a hit tomorrow
    with nothing today ruling it out. The population is therefore every
    tracked `src/frob/**/*.py` file, the SAME unscoped set `tracked_
    python_files_for_gate`'s own default `pathspec="src/frob"` already
    returns unfiltered -- this function exists only to give PORT001 a
    named, `frob:tests`-bound call site of its own (mirroring `tracked_
    gate_files`'s shape) rather than calling the shared helper directly
    with no declared population of its own. Also mirrors RENDER001/
    WALK001's own already-unscoped "scanned N tracked src/frob .py
    file(s)" convention (`_render_lint.py`/`_walk_lint.py`) -- PORT001's
    widened population is not a novel shape in this codebase, just a
    different existing one than `tracked_gate_files` used before T-3275.

    T-2388's directive not to invent a second detector ARCHITECTURE
    still holds: this is not a second scanning engine, only a second,
    separately-derived POPULATION fed into the same AST-scanning
    machinery `_port_selfcheck.py` already runs -- LEXCHECK001 keeps
    `tracked_gate_files`/`DETECTOR_PACKAGE_ROOTS` unchanged, since its
    own question ("is this a detector") is the one that tuple actually
    answers."""
    return tracked_python_files_for_gate(root, log_prefix=log_prefix)


__all__ = [
    "DETECTOR_PACKAGE_ROOTS",
    "is_detector_package_file",
    "tracked_gate_files",
    "tracked_repo_python_files",
]
