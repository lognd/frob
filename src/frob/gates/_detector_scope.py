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

from typing import Final

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


__all__ = ["DETECTOR_PACKAGE_ROOTS", "is_detector_package_file"]
