"""Cross-language clone litmus (T-0198, docs/modules/dup-sota-survey.md
item 13; re-characterized by T-0494): the SAME logic -- a running-total
accumulator with a clamp, matching tests/fixtures/dup_smart/src/mod_a.py's
compute_total/compute_sum pair -- expressed once in Python and once in
TypeScript, run through the REAL `find_clones` pipeline (real `frob.lang`
parse, real `frob_core` bucketing/verification, no hand-built symbol
records).

The survey's item 13 disposition (docs/modules/dup-sota-survey.md
#13-cross-language-clone-detection-general) claimed cross-language
matching is "architecturally already claimed... PROVIDED frob.lang
actually normalizes multiple grammars to a shared node vocabulary" and
flagged that as unverified.

**R1/R2/R3 (lexical rungs): still negative, unchanged since T-0198.**
`_r1_hash`/`_r2_hash`/`_r3_fingerprint` (src/frob/dup/_pipeline.py) all
bucket on the symbol's literal `body_tokens` (R1 raw, R2 with
identifier-shaped tokens alpha-renamed but every other token, including
language keywords/punctuation, passed through unchanged). Python's
`def ... for item in items: ... if ...:` and TypeScript's
`function ...(...) { for (const item of items) { if (...) { } } }` share
no token vocabulary at all once keywords/punctuation are included, so R1
and R2 buckets never collide across the pair.

**R5 (structural rung): now POSITIVE for this pair (T-0494, following
T-0487's `_KEYWORDS` fix).** R5's WL-hash operates on `_real_dataflow_graph`'s
structural def/use labels, not literal token identity, and was already
cross-language-capable in principle -- but the pre-fix `_KEYWORDS` table
mis-labeled TypeScript's `let`/`const` declaration keywords as plain
identifiers, corrupting `mod_b.ts::computeTotal`'s def-use graph. With
that fixed, `mod_a.py::compute_total` and `mod_b.ts::computeTotal`
genuinely WL-hash-collide at r5, similarity=0.88, verified directly
against `find_clones` -- and, because R1-R4 never bucket this pair
together (see above), `candidate_pairs` only reaches them via R5's own
independent bucketing pass, not by falling through a shared earlier-rung
bucket. The group fires at EVERY tested threshold (0.9, 0.7, 0.5, 0.3,
0.1) -- `CloneMatchGroup.pairs[0].similarity` (0.88) is compared against
each rung's own internal acceptance criterion, not linearly gated by
`DupConfig.threshold`, so lowering the threshold does not additionally
gate an r5 hit already accepted at the rung's own bar.

This is a real accuracy improvement (R5 is documented as
structural/language-agnostic, T-0196/T-0199), not a regression -- and is
now asserted as a POSITIVE fixture below, the mirror image of the
negative-result pattern `tests/unit/strata/litmus/cwe_611_unfired.strata`
+ `tests/unit/strata/test_litmus_cwe.py` use for CWE-611/CWE-22/CWE-352/
CWE-798: never a skip, never silently dropped, whichever way the true
result points. The follow-up (giving `frob.lang` a shared cross-grammar
node-kind vocabulary so R1-R3 could bucket structurally instead of
lexically, closing the remaining negative rungs) is out of this ticket's
scope (`src/frob/lang/**` is not in T-0198's or T-0494's declared scope)
and remains filed separately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DupConfig, find_clones
from frob.dup import _cache as dup_cache
from frob.dup import _core as dup_core
from frob.graph import build_graph

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dup_cross_lang"


# frob:ticket T-0517
# frob:waive DEAD001 reason="pytest autouse fixture (T-0565): invoked by the test runner for every test in this module without ever appearing as a name/call token anywhere, the one DEAD001 false-positive class build_reference_graph's sig_tokens+body_tokens broadening cannot see (autouse has no referencing site at all, unlike a fixture consumed by parameter name)"  # noqa: E501
@pytest.fixture(autouse=True)
def _isolated_dup_cache(tmp_path, monkeypatch):
    """Redirect `find_clones`'s dup.db to `tmp_path`, never the tracked fixture dir.

    T-0517: `find_clones` keys its cache path on `snapshot.root`, which for
    this module is `FIXTURE_ROOT` (a tracked fixture directory) -- an
    unpatched run leaves an untracked `.frob/dup.db` sitting inside it,
    which previously served stale cache hits to a later test run against a
    changed algorithm (6 cache hits, 0 pairs verified) without ever
    appearing as a diff. Monkeypatching `_db_path` keeps every fingerprint/
    verdict this module writes confined to `tmp_path`, cleaned up by
    pytest's own teardown.
    """
    real_db_path = dup_cache._db_path
    monkeypatch.setattr(dup_cache, "_db_path", lambda root: tmp_path / "dup.db")
    yield
    dup_cache._close_all()
    # Guard against any stray leak from before this fixture existed.
    leaked = real_db_path(FIXTURE_ROOT)
    leaked.unlink(missing_ok=True)
    leaked.with_name(leaked.name + "-wal").unlink(missing_ok=True)
    leaked.with_name(leaked.name + "-shm").unlink(missing_ok=True)


@pytest.fixture()
def snapshot(tmp_path):
    """Real `build_graph` snapshot of the cross-language fixture pair (Python + TS)."""
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURE_ROOT, cache)
    assert result.is_ok, result.err
    return result.danger_ok


class TestCrossLanguageCloneNotYetDetected:
    """T-0198/T-0494: same accumulator-with-clamp logic in Python
    (`compute_total`) and TypeScript (`computeTotal`), run through the
    real pipeline. Both symbols parse and fingerprint successfully.

    Class name kept from T-0198 (rather than renamed to something like
    "AtLexicalRungsOnly") so this class's still-valid evidence ids
    (`test_both_languages_parse_into_the_snapshot`,
    `test_both_symbols_are_individually_fingerprinted`) keep resolving
    for T-0198's archived Done report -- only the ORIGINAL
    `test_no_clone_group_at_any_threshold` (whose assertion is now false)
    was removed; see `TestCrossLanguageR5NowFires` for its replacement.

    R1/R2/R3 never bucket this pair together, at any threshold, because
    those rungs bucket on literal token vocabulary that the two grammars
    do not share -- this part of the T-0198 characterization is
    unchanged. What HAS changed (T-0494, following T-0487's `_KEYWORDS`
    fix) is R5: see `TestCrossLanguageR5NowFires` below for the positive
    counterpart. This class only characterizes the still-negative
    lexical rungs; it does NOT assert `report.groups == ()` overall
    (that blanket assertion is false since T-0487 -- R5 fires -- see
    `TestCrossLanguageR5NowFires`)."""

    # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_clones kind="unit"
    # frob:ticket T-0198
    def test_both_languages_parse_into_the_snapshot(self, snapshot):
        refs = set(snapshot.symbols)
        assert any("compute_total" in r for r in refs)
        assert any("computeTotal" in r for r in refs)

    # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_clones kind="unit"
    # frob:ticket T-0198
    def test_both_symbols_are_individually_fingerprinted(self, snapshot):
        # Confirms the negative lexical-rung result below is a bucketing
        # miss, not a fingerprinting failure -- both symbols must actually
        # reach the fingerprint stage (stats.fingerprinted counts them)
        # for "vocabulary does not align" to be a meaningful finding
        # rather than a fixture that just failed to parse.
        result = find_clones(snapshot, DupConfig(min_tokens=3, threshold=0.1))
        assert result.is_ok, result.err
        assert result.danger_ok.stats.fingerprinted >= 2


class TestCrossLanguageR5NowFires:
    """T-0494: R5 DOES group this python/typescript pair as a clone, at
    every threshold from 0.9 down to 0.1 -- a real accuracy improvement
    (R5 is documented as structural/language-agnostic, T-0196/T-0199)
    that T-0487's `_KEYWORDS` fix unlocked, not a regression. This
    replaces T-0198's original `test_no_clone_group_at_any_threshold`
    (which asserted the opposite and went stale the moment `_KEYWORDS`
    started correctly recognizing TypeScript's `let`/`const`)."""

    # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_clones kind="unit"
    # frob:ticket T-0494
    @pytest.mark.parametrize("threshold", [0.9, 0.7, 0.5, 0.3, 0.1])
    def test_r5_group_fires_at_every_threshold(self, snapshot, threshold):
        result = find_clones(snapshot, DupConfig(min_tokens=3, threshold=threshold))
        assert result.is_ok, result.err
        report = result.danger_ok
        assert len(report.groups) == 1, (
            f"expected exactly one cross-language r5 clone group at "
            f"threshold={threshold} (T-0494: R5's structural def-use "
            f"WL-hash collides for compute_total/computeTotal since "
            f"T-0487's _KEYWORDS fix -- see module docstring); "
            f"got {report.groups!r}"
        )
        (pair,) = report.groups[0].pairs
        assert pair.rung == "r5"
        assert pair.similarity == pytest.approx(0.88)
        refs = {pair.left.ref, pair.right.ref}
        assert refs == {
            "src/mod_a.py::compute_total",
            "src/mod_b.ts::computeTotal",
        }

    # frob:tests src/frob/dup/_pipeline/_fingerprint.py::find_clones kind="unit"
    # frob:ticket T-0494
    def test_r5_group_is_not_gated_by_a_threshold_above_its_own_similarity(
        self, snapshot
    ):
        # T-0494: confirms the r5 hit's fixed similarity (0.88, see
        # frob.dup._pipeline._R5_SIMILARITY) is not linearly compared
        # against DupConfig.threshold -- it still fires even when
        # threshold (0.9) is numerically ABOVE the pair's own
        # similarity (0.88), because r5 grouping uses its own internal
        # acceptance bar, not a threshold >= similarity gate.
        result = find_clones(snapshot, DupConfig(min_tokens=3, threshold=0.9))
        assert result.is_ok, result.err
        assert len(result.danger_ok.groups) == 1
