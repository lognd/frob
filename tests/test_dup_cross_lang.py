"""Cross-language clone litmus (T-0198, docs/modules/dup-sota-survey.md
item 13): the SAME logic -- a running-total accumulator with a clamp,
matching tests/fixtures/dup_smart/src/mod_a.py's compute_total/
compute_sum pair -- expressed once in Python and once in TypeScript,
run through the REAL `find_clones` pipeline (real `frob.lang` parse,
real `frob_core` bucketing/verification, no hand-built symbol records).

The survey's item 13 disposition (docs/modules/dup-sota-survey.md
#13-cross-language-clone-detection-general) claimed cross-language
matching is "architecturally already claimed... PROVIDED frob.lang
actually normalizes multiple grammars to a shared node vocabulary" and
flagged that as unverified. This fixture is that verification, and the
answer is negative: it is a design finding, not a pass.

`_r1_hash`/`_r2_hash`/`_r3_fingerprint` (src/frob/dup/_pipeline.py) all
bucket on the symbol's literal `body_tokens` (R1 raw, R2 with
identifier-shaped tokens alpha-renamed but every other token, including
language keywords/punctuation, passed through unchanged). Python's
`def ... for item in items: ... if ...:` and TypeScript's
`function ...(...) { for (const item of items) { if (...) { } } }` share
no token vocabulary at all once keywords/punctuation are included, so R1
and R2 buckets never collide across the pair -- and `candidate_pairs`
(frob_core) only ever compares symbols that share a bucket, so the pair
never reaches R4 tree-edit-distance verification, R5, or any similarity
threshold. Lowering `DupConfig.threshold` cannot help: the pair is
excluded before threshold comparison ever runs. `find_clones` reports
zero groups for this fixture at every threshold from 0.9 down to 0.1
(measured, not assumed -- see the Done report).

This is asserted explicitly here, the same non-firing-by-design pattern
`tests/unit/strata/litmus/cwe_611_unfired.strata` +
`tests/unit/strata/test_litmus_cwe.py` use for CWE-611/CWE-22/CWE-352/
CWE-798: never a skip, never silently dropped. The follow-up (giving
`frob.lang` a shared cross-grammar node-kind vocabulary so R1-R3 could
bucket structurally instead of lexically) is out of this ticket's scope
(`src/frob/lang/**` is not in T-0198's declared scope) and is filed
separately.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from frob.dup import DupConfig, find_clones
from frob.dup import _core as dup_core
from frob.graph import build_graph

pytestmark = pytest.mark.skipif(
    not dup_core.core_available(),
    reason="frob-core native extension not installed (build with maturin develop)",
)

FIXTURE_ROOT = Path(__file__).parent / "fixtures" / "dup_cross_lang"


@pytest.fixture()
def snapshot(tmp_path):
    """Real `build_graph` snapshot of the cross-language fixture pair (Python + TS)."""
    cache = tmp_path / "graph-cache"
    result = build_graph(FIXTURE_ROOT, cache)
    assert result.is_ok, result.err
    return result.danger_ok


class TestCrossLanguageCloneNotYetDetected:
    """T-0198: same accumulator-with-clamp logic in Python
    (`compute_total`) and TypeScript (`computeTotal`), run through the
    real pipeline. Both symbols parse and fingerprint successfully; they
    are never grouped as a clone, at any threshold, because R1/R2/R3
    bucket on literal token vocabulary that the two grammars do not
    share. This is a characterization test of a KNOWN LIMITATION (not a
    design choice): cross-grammar structural bucketing is tracked as a
    follow-up (frob.lang shared node vocabulary). It locks in the current
    behavior so the follow-up's fix has a red-to-green target."""

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0198
    def test_both_languages_parse_into_the_snapshot(self, snapshot):
        refs = set(snapshot.symbols)
        assert any("compute_total" in r for r in refs)
        assert any("computeTotal" in r for r in refs)

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0198
    @pytest.mark.parametrize("threshold", [0.9, 0.7, 0.5, 0.3, 0.1])
    def test_no_clone_group_at_any_threshold(self, snapshot, threshold):
        result = find_clones(snapshot, DupConfig(min_tokens=3, threshold=threshold))
        assert result.is_ok, result.err
        report = result.danger_ok
        assert report.groups == (), (
            f"expected zero cross-language clone groups at threshold={threshold} "
            f"(R1/R2/R3 bucket on literal token vocabulary the two grammars do "
            f"not share -- see module docstring); got {report.groups!r}"
        )

    # frob:tests src/frob/dup/_pipeline.py::find_clones kind="unit"
    # frob:ticket T-0198
    def test_both_symbols_are_individually_fingerprinted(self, snapshot):
        # The negative result above is a bucketing miss, not a fingerprinting
        # failure -- both symbols must actually reach the fingerprint stage
        # (stats.fingerprinted counts them) for the "vocabulary does not
        # align" finding to be meaningful rather than a fixture that just
        # failed to parse.
        result = find_clones(snapshot, DupConfig(min_tokens=3, threshold=0.1))
        assert result.is_ok, result.err
        assert result.danger_ok.stats.fingerprinted >= 2
