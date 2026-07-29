"""frob.dup exhaustiveness registry (T-0199): a single-source (rung x
clone-type x language) matrix extending the T-0158 capability-matrix mold
to duplicate detection. Every rung names the clone type(s) (Type-1..4, the
classic Roy/Cordy taxonomy) it is designed to catch (`RUNG_SPECS`); every
(rung, clone_type, language) cell that follows from that design is either
`DUP_CLAIMS`-backed by a real litmus fixture proving the rung fires on
that language, or `DUP_MATRIX_EXCUSES`-backed by a specific written reason
it is not (yet) proven. `unclaimed_cells()` is empty iff every cell is one
or the other -- the same "patterned xor excused, never neither" discipline
`frob.vet._capability_registry.unexcused_empty_cells` enforces for the
capability matrix. `tests/test_dup_exhaustiveness.py` is the drift-lock:
adding a rung or a clone-type claim without a firing fixture, or letting a
claim and an excuse coexist on one cell, fails the suite.
"""
# frob:waive INV006 preset="split-carried-prose"

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from frob.logging import get_logger

_log = get_logger(__name__)

# frob:doc docs/modules/dup.md#public-api
#: every language `frob.lang` can parse into the symbol/token stream the
#: rung ladder operates over (`frob.lang._SUPPORTED_LANGUAGES` minus the
#: `.strata` grammar, which has no clone-detection use case). `c`/`cpp` are
#: kept separate here (unlike the capability registry's merged `c-cpp`
#: bucket) because `frob.lang` itself reports them as distinct labels.
LANGUAGES: tuple[str, ...] = ("python", "typescript", "rust", "c", "cpp")

# frob:doc docs/modules/dup.md#public-api
#: the classic Roy/Cordy clone taxonomy `docs/modules/dup.md`'s rung table
#: implicitly claims against: Type-1 (exact copy modulo whitespace/
#: comments), Type-2 (syntactically identical modulo renamed identifiers/
#: literals), Type-3 (near-miss -- statements added/removed/changed),
#: Type-4 (semantically equivalent, syntactically different).
CLONE_TYPES: tuple[int, ...] = (1, 2, 3, 4)

# frob:doc docs/modules/dup.md#public-api
#: human-readable label per `CLONE_TYPES` member, for matrix/report output.
CLONE_TYPE_DESCRIPTIONS: dict[int, str] = {
    1: "Type-1: exact copy modulo whitespace/comments",
    2: "Type-2: syntactically identical modulo renamed identifiers/literals",
    3: "Type-3: near-miss -- statements added, removed, or changed",
    4: "Type-4: semantically equivalent, syntactically different",
}


# frob:doc docs/modules/dup.md#public-api
class RungSpec(BaseModel):
    """One rung's identity: its `frob.dup` name, the clone type(s) its
    technique is designed to catch (docs/modules/dup.md's rung table
    "Catches" column), and a one-line technique summary."""

    model_config = ConfigDict(frozen=True)

    rung: str
    claimed_clone_types: tuple[int, ...]
    technique: str


# frob:doc docs/modules/dup.md#public-api
# frob:ticket T-0199
#: one entry per rung `frob.dup._pipeline`/`docs/modules/dup.md` names.
#: `claimed_clone_types` is deliberately narrow (one type per rung, not
#: the multi-type "roughly overlaps" reading) so each rung's exhaustiveness
#: cells stay a tractable, individually provable set -- widening a rung's
#: claim later is exactly the drift this registry is built to catch.
RUNG_SPECS: tuple[RungSpec, ...] = (
    RungSpec(
        rung="r1",
        claimed_clone_types=(1,),
        technique="exact token hash over the whole symbol body",
    ),
    RungSpec(
        rung="r1.5",
        claimed_clone_types=(1,),
        technique="generalized suffix array over the corpus token stream "
        "(exact sub-region matches, opt-in via [dup].region_kernel)",
    ),
    RungSpec(
        rung="r2",
        claimed_clone_types=(2,),
        technique="alpha-renamed token hash over the whole symbol body",
    ),
    RungSpec(
        rung="r3",
        claimed_clone_types=(2,),
        technique="canonicalized-AST subtree hash (folds the r2-normalized "
        "token stream; frob-core's r3_canonical_hash)",
    ),
    RungSpec(
        rung="r4",
        claimed_clone_types=(3,),
        technique="winnowed fingerprints + tree-edit-distance verification",
    ),
    RungSpec(
        rung="r5",
        claimed_clone_types=(3,),
        technique="Weisfeiler-Lehman graph-kernel hash over a def-use/"
        "control-flow graph",
    ),
    RungSpec(
        rung="r6",
        claimed_clone_types=(4,),
        technique="observational-equivalence probing of pure callables",
    ),
    RungSpec(
        rung="r7",
        claimed_clone_types=(4,),
        technique="bounded-SMT equivalence check via z3 (opt-in, frob[smt])",
    ),
)

_RUNG_BY_NAME: dict[str, RungSpec] = {spec.rung: spec for spec in RUNG_SPECS}


# frob:doc docs/modules/dup.md#public-api
class DupClaim(BaseModel):
    """One (rung, clone_type, language) cell backed by a real, reused
    litmus fixture: `fixture_root` names a `tests/fixtures/<dir>` this
    repo's dup test suite already builds a `GraphSnapshot` from (T-0199
    reuses, never duplicates, the existing per-rung fixture pairs), and
    `proof_test` is the exact node id that exercises it -- both must
    resolve, same discipline as a `frob:tests` directive."""

    model_config = ConfigDict(frozen=True)

    rung: str
    clone_type: int
    language: str
    fixture_root: str
    proof_test: str
    note: str


# frob:doc docs/modules/dup.md#public-api
class DupMatrixExcuse(BaseModel):
    """A written, specific reason a (rung, clone_type, language) cell has
    no `DupClaim` -- T-0158 discipline: never a boilerplate 'not
    applicable', always the actual missing idiom or structural limit."""

    model_config = ConfigDict(frozen=True)

    rung: str
    clone_type: int
    language: str
    reason: str


# frob:doc docs/modules/dup.md#public-api
# frob:ticket T-0199
#: every claim is proven against an EXISTING fixture directory already
#: exercised by `tests/test_dup_rungs.py`/`test_dup_region.py`/
#: `test_dup_smart.py` -- `tests/test_dup_exhaustiveness.py` re-runs
#: `find_clones`/`probe_equivalence` over the same `FIXTURE_ROOT`s those
#: files use and asserts the named rung/pair actually appears, so a
#: silent regression in an already-tested rung fails BOTH suites, not
#: just this one.
DUP_CLAIMS: tuple[DupClaim, ...] = (
    DupClaim(
        rung="r1",
        clone_type=1,
        language="python",
        fixture_root="dup_rungs",
        proof_test="tests/test_dup_exhaustiveness.py::TestMatrixClaimsFire::test_r1_python_type1",
        note="mod_r6.py::impure_logger/impure_logger_dup -- byte-identical "
        "bodies, only the symbol name differs",
    ),
    DupClaim(
        rung="r1.5",
        clone_type=1,
        language="python",
        fixture_root="dup_region",
        proof_test="tests/test_dup_exhaustiveness.py::TestMatrixClaimsFire::test_r1_5_python_type1",
        note="mod_a.py::alpha_process / mod_b.py::beta_transform -- one "
        "identical 6-line block inside two otherwise-different bodies "
        "([dup].region_kernel=True)",
    ),
    DupClaim(
        rung="r2",
        clone_type=2,
        language="python",
        fixture_root="dup_smart",
        proof_test="tests/test_dup_exhaustiveness.py::TestMatrixClaimsFire::test_r2_python_type2",
        note="mod_a.py::compute_total/compute_sum -- identical shape, "
        "renamed identifiers",
    ),
    DupClaim(
        rung="r4",
        clone_type=3,
        language="python",
        fixture_root="dup_rungs",
        proof_test="tests/test_dup_exhaustiveness.py::TestMatrixClaimsFire::test_r4_r5_python_type3[r4-process_gapped_a-process_gapped_b]",
        note="mod_r4.py::process_gapped_a/process_gapped_b -- statements "
        "inserted/removed between the two bodies",
    ),
    DupClaim(
        rung="r5",
        clone_type=3,
        language="python",
        fixture_root="dup_rungs",
        proof_test="tests/test_dup_exhaustiveness.py::TestMatrixClaimsFire::test_r4_r5_python_type3[r5-combine_a-combine_b]",
        note="mod_r5.py::combine_a/combine_b -- reordered but dataflow-identical logic",
    ),
    DupClaim(
        rung="r6",
        clone_type=4,
        language="python",
        fixture_root="dup_rungs",
        proof_test="tests/test_dup_exhaustiveness.py::TestMatrixClaimsFire::test_r6_python_type4",
        note="mod_r6.py::add_twice_a/add_twice_b -- different algorithm "
        "(`x + x` vs `2 * x`), same behavior, proven via probe_equivalence",
    ),
    # T-0487: T-0447 landed frob-core's r3_canonicalize (literal abstraction
    # + elif control-flow desugar), so r3 now independently fires where r2
    # does not -- the r3-vs-r2 excuse below is stale and removed in favor
    # of this claim. Fixture lives in tests/test_dup.py (not an existing
    # fixture_root dir like the claims above; T-0199's "reuse an existing
    # fixture directory" note predates T-0447's in-test tmp_path fixtures).
    DupClaim(
        rung="r3",
        clone_type=2,
        language="python",
        fixture_root="tests/test_dup.py (inline tmp_path fixture)",
        proof_test="tests/test_dup.py::TestR3LiteralAbstraction.test_r3_fires_where_r2_does_not",
        note="offset_by_one/offset_by_two -- identical shape, differ only "
        "by a numeric literal; r3's literal abstraction collapses both "
        "literals to a shared placeholder, r2 does not",
    ),
    # T-0487: R5's WL-hash operates on `_real_dataflow_graph`'s structural
    # def/use labels, not literal token identity, so it was already
    # cross-language-capable in principle; the `_KEYWORDS` fix (a Rust
    # `let` no longer mis-labels as an identifier) makes that provable even
    # when the rust side declares a local binding, closing the rust cell
    # of the generic non-python language-gap excuse for r5/type3.
    DupClaim(
        rung="r5",
        clone_type=3,
        language="rust",
        fixture_root="tests/test_dup.py (inline tmp_path fixture)",
        proof_test="tests/test_dup.py::TestCrossLanguageR5WithLet."
        "test_r5_fires_across_languages_with_a_let_binding",
        note="sum_with_local_py/sum_with_local_rs -- structurally "
        "identical function (one local binding, one return) written once "
        "in python and once in rust; r5's structural def-use graph "
        "collides across languages",
    ),
    # T-0518: T-0494 proved r5 also fires python/typescript (the same
    # _KEYWORDS fix that closed the rust cell above applies here -- a
    # TypeScript `let`/`const` no longer mis-labels as a plain identifier),
    # closing the typescript cell of the generic non-python language-gap
    # excuse for r5/type3.
    DupClaim(
        rung="r5",
        clone_type=3,
        language="typescript",
        fixture_root="tests/fixtures/dup_cross_lang",
        proof_test="tests/test_dup_cross_lang.py::TestCrossLanguageR5NowFires."
        "test_r5_group_fires_at_every_threshold",
        note="compute_total/computeTotal -- a running-total accumulator "
        "with a clamp, written once in python and once in typescript; "
        "r5's structural def-use WL-hash collides across languages "
        "(similarity=0.88, fires at every threshold 0.9-0.1)",
    ),
)

# frob:doc docs/modules/dup.md#public-api
# frob:ticket T-0199
#: every claimable cell without a `DupClaim` above, each with the actual
#: reason (never a blanket "not applicable"). T-draft-d6bca168 tracks the deferred
#: work these name -- filed as a follow-up rather than silently dropped
#: (T-0158 "escape valve" precedent).
DUP_MATRIX_EXCUSES: tuple[DupMatrixExcuse, ...] = (
    # -- r3-vs-r2 excuse removed (T-0487): T-0447 landed frob-core's
    # r3_canonicalize (literal abstraction + elif desugar), so r3 now
    # independently fires where r2 does not -- see the r3/python DUP_CLAIMS
    # entry above, which supersedes this excuse.
    # -- r7: opt-in, zero fixtures, dependency not installed by default ---
    DupMatrixExcuse(
        rung="r7",
        clone_type=4,
        language="python",
        reason="opt-in bounded-SMT rung requires the z3-solver optional "
        "extra (frob[smt]), not installed by default and not present in "
        "this dev environment; no litmus fixture exists yet -- tracked by "
        "T-draft-d6bca168",
    ),
)


def _language_gap_reason(rung: str) -> str:
    """The honest, rung-specific reason a non-python language cell has no
    claim -- distinguishes a structural language restriction (r6/r7) from
    a missing-fixture gap (every other rung, which is language-agnostic by
    construction over `frob.lang`'s normalized token/AST output)."""
    if rung in ("r6", "r7"):
        return (
            f"{rung} resolves candidates to importable Python callables via "
            "frob.dup._pipeline._load_python_callable -- Err(NotPure) for "
            "every non-python language by construction, not a missing-"
            "fixture gap; no cross-language FFI probing harness exists"
        )
    return (
        f"{rung}'s technique operates on frob.lang's normalized token/AST "
        "output and is not language-restricted by construction, but no "
        "non-python litmus fixture has been authored yet to prove it fires "
        "cross-language -- tracked by T-draft-d6bca168"
    )


def _non_python_excuses() -> tuple[DupMatrixExcuse, ...]:
    """Every (rung, clone_type, non-python-language) cell that follows
    from `RUNG_SPECS` and has no `DUP_CLAIMS` entry of its own, excused
    with `_language_gap_reason` -- generated rather than hand-listed so a
    new rung or a new `LANGUAGES` entry is covered automatically instead
    of silently falling through as an unexcused empty cell. A cell already
    covered by a `DUP_CLAIMS` entry (T-0487: e.g. r5/rust) is skipped here
    -- generating an excuse for an already-claimed cell would trip
    `test_no_cell_is_both_claimed_and_excused`, the same claimed-xor-
    excused discipline `DUP_MATRIX_EXCUSES` itself follows."""
    claimed_keys = {(c.rung, c.clone_type, c.language) for c in DUP_CLAIMS}
    out: list[DupMatrixExcuse] = []
    for spec in RUNG_SPECS:
        for clone_type in spec.claimed_clone_types:
            for language in LANGUAGES:
                if language == "python":
                    continue
                if (spec.rung, clone_type, language) in claimed_keys:
                    continue
                out.append(
                    DupMatrixExcuse(
                        rung=spec.rung,
                        clone_type=clone_type,
                        language=language,
                        reason=_language_gap_reason(spec.rung),
                    )
                )
    return tuple(out)


# frob:doc docs/modules/dup.md#public-api
class DupMatrixCell(BaseModel):
    """One (rung, clone_type, language) matrix cell's verdict: `claimed`
    (has a firing `DupClaim`), `excused` (has a `DupMatrixExcuse`), or
    neither -- the last case is a gate failure (T-0199, T-0158 mold)."""

    model_config = ConfigDict(frozen=True)

    rung: str
    clone_type: int
    language: str
    claimed: bool
    excused: bool
    excuse_reason: str | None = None


# frob:doc docs/modules/dup.md#public-api
# frob:ticket T-0199
# frob:tests tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness.test_matrix_covers_every_rung_clone_type_and_language kind="unit"  # noqa: E501
def dup_matrix() -> tuple[DupMatrixCell, ...]:
    """The full (rung x clone_type x language) matrix, restricted to
    cells `RUNG_SPECS.claimed_clone_types` actually puts in play: every
    cell is `claimed`, `excused`, or -- if neither -- a gate failure the
    caller must surface. Deterministic order: `RUNG_SPECS` order, then
    `claimed_clone_types` order, then `LANGUAGES` order."""
    claim_by_key = {(c.rung, c.clone_type, c.language): c for c in DUP_CLAIMS}
    excuse_by_key = {
        (e.rung, e.clone_type, e.language): e
        for e in (*DUP_MATRIX_EXCUSES, *_non_python_excuses())
    }

    cells: list[DupMatrixCell] = []
    for spec in RUNG_SPECS:
        for clone_type in spec.claimed_clone_types:
            for language in LANGUAGES:
                key = (spec.rung, clone_type, language)
                claim = claim_by_key.get(key)
                excuse = excuse_by_key.get(key)
                cells.append(
                    DupMatrixCell(
                        rung=spec.rung,
                        clone_type=clone_type,
                        language=language,
                        claimed=claim is not None,
                        excused=excuse is not None,
                        excuse_reason=excuse.reason if excuse else None,
                    )
                )
    return tuple(cells)


# frob:doc docs/modules/dup.md#public-api
# frob:ticket T-0199
# frob:tests tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness.test_no_unclaimed_cells kind="unit"  # noqa: E501
def unclaimed_cells() -> tuple[DupMatrixCell, ...]:
    """Every matrix cell with neither a claim nor an excuse -- the T-0199
    gate failure condition. Empty tuple = the exhaustiveness claim holds."""
    return tuple(c for c in dup_matrix() if not c.claimed and not c.excused)


# frob:doc docs/modules/dup.md#public-api
# frob:ticket T-0199
# frob:tests tests/test_dup_exhaustiveness.py::TestMatrixExhaustiveness.test_every_claim_names_a_registered_rung_and_claimed_type kind="unit"  # noqa: E501
def validate_claim_rungs(claims: tuple[DupClaim, ...] = DUP_CLAIMS) -> tuple[str, ...]:
    """Drift-lock: every `DupClaim.rung` must name a registered
    `RUNG_SPECS` entry and its `clone_type` must be one that rung claims.
    Returns a description per offending claim; empty tuple means clean."""
    offenders: list[str] = []
    for claim in claims:
        spec = _RUNG_BY_NAME.get(claim.rung)
        if spec is None:
            offenders.append(f"{claim.rung}: not a registered rung")
        elif claim.clone_type not in spec.claimed_clone_types:
            offenders.append(
                f"{claim.rung}: clone_type {claim.clone_type} not in "
                f"claimed_clone_types {spec.claimed_clone_types}"
            )
    if offenders:
        _log.error(
            "dup exhaustiveness: %d invalid claim(s): %s", len(offenders), offenders
        )
    return tuple(offenders)
