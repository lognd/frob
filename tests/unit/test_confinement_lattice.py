"""Tests for T-2504's path-confinement provenance lattice
(`frob.graph.summary.compute_confinement_summaries`), hosted on the
existing protocol-summary engine's SCC-ordered worklist.

`docs/modules/graph.md#path-confinement-census`.
"""

from __future__ import annotations

from pathlib import Path

from frob.graph.summary import (
    ConfinementState,
    compute_confinement_summaries,
    scan_confinement_facts,
)


def _write_sample(tmp_path: Path, source: str) -> Path:
    """Write `source` as `sample.py` under `tmp_path` and return its path
    -- the shared fixture-write helper every test in this module uses to
    feed `scan_confinement_facts` a real file on disk (the engine itself
    is offline/pure past that one read, matching `compute_protocol_
    summaries`'s existing no-filesystem-walk contract)."""
    sample = tmp_path / "sample.py"
    sample.write_text(source, encoding="utf-8")
    return sample


class TestConfinementLatticePositiveControl:
    """MANDATORY positive control (T-2504's own ticket body): a planted
    ESCAPING write must FIRE as `ESCAPED`, and the ordinary `tmp_path`
    pattern must NOT."""

    def test_absolute_literal_write_is_escaped(self, tmp_path: Path) -> None:
        """`Path("/tmp/evil.txt").write_text(...)` -- an absolute string
        literal feeding a write -- resolves `ESCAPED`, never `ROOTED` or
        silently dropped."""
        sample = _write_sample(
            tmp_path,
            'from pathlib import Path\n'
            'def test_evil():\n'
            '    p = Path("/tmp/evil.txt")\n'
            '    p.write_text("bad")\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["escaped"] == 1
        assert result.counts["rooted"] == 0
        escaped_sites = [s for s in result.sites if s.state is ConfinementState.ESCAPED]
        assert len(escaped_sites) == 1
        assert escaped_sites[0].symref.endswith("::test_evil")

    def test_ordinary_tmp_path_write_is_rooted_not_escaped(
        self, tmp_path: Path
    ) -> None:
        """The ordinary, correct pytest pattern -- `(tmp_path /
        "file.txt").write_text(...)` -- resolves `ROOTED`, never a false
        `ESCAPED` positive."""
        sample = _write_sample(
            tmp_path,
            'def test_ordinary(tmp_path):\n'
            '    (tmp_path / "file.txt").write_text("ok")\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["rooted"] == 1
        assert result.counts["escaped"] == 0


class TestConfinementLatticeUnknown:
    """`UNKNOWN` is the honest default whenever this pass cannot prove
    either endpoint -- never silently rendered as a pass."""

    def test_unresolved_private_helper_call_poisons_to_unknown(
        self, tmp_path: Path
    ) -> None:
        """A write inside a helper reached only via a call this pass
        cannot resolve to a known summary (the helper is never itself
        analyzed -- absent from `facts` entirely) resolves `UNKNOWN`,
        attributing the poison source by symref."""
        sample = _write_sample(
            tmp_path,
            'def test_calls_unknown_helper(tmp_path):\n'
            '    result = _external_helper(tmp_path)\n'
            '    result.write_text("who knows")\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["unknown"] == 1
        site = result.sites[0]
        assert site.state is ConfinementState.UNKNOWN
        assert site.poison_source is not None
        # `_external_helper` is never itself scanned (out of `facts`
        # entirely) -- this pass has no candidate to resolve it against
        # at all, so it correctly reports the SAME `UNRESOLVED_CALLEE`
        # sentinel the protocol engine's own poisoning uses (T-0809),
        # not a fabricated per-name attribution.
        from frob.graph.callgraph import UNRESOLVED_CALLEE

        assert site.poison_source == UNRESOLVED_CALLEE

    def test_env_lookup_feeding_a_write_is_escaped_not_unknown(
        self, tmp_path: Path
    ) -> None:
        """`os.environ[...]` feeding a write path is a PROVABLY escaping
        source (T-2504's own lattice spec), not merely unprovable --
        must resolve `ESCAPED`."""
        sample = _write_sample(
            tmp_path,
            'import os\n'
            'from pathlib import Path\n'
            'def test_env_path():\n'
            '    target = Path(os.environ["HOME"]) / "x.txt"\n'
            '    target.write_text("bad")\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["escaped"] == 1


class TestConfinementLatticeHelperPropagation:
    """A helper's RETURN value's confinement propagates through the same
    bottom-up SCC worklist the protocol engine uses -- T-2504's own
    "`_write_fixture(tmp: Path)` summarizes as param0 confined => result
    confined" example."""

    def test_helper_return_value_confinement_propagates_to_caller_site(
        self, tmp_path: Path
    ) -> None:
        """A private helper that RETURNS a path built only from its own
        parameter via confinement-preserving ops, called with a `ROOTED`
        argument and then written to by the caller, resolves `ROOTED` at
        the CALLER's write site -- proving the param0-confined-through
        propagation the ticket names, not just same-function reasoning."""
        sample = _write_sample(
            tmp_path,
            'from pathlib import Path\n'
            'def _make_path(base: Path) -> Path:\n'
            '    return base / "nested" / "file.txt"\n'
            'def test_uses_helper(tmp_path):\n'
            '    target = _make_path(tmp_path)\n'
            '    target.write_text("ok")\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["rooted"] == 1
        assert result.counts["unknown"] == 0
        site = result.sites[0]
        assert site.symref.endswith("::test_uses_helper")
        assert site.state is ConfinementState.ROOTED


class TestParam0Credit:
    """T-2519: a private helper that writes DIRECTLY to its own first
    positional parameter (never returning it, unlike `TestConfinement
    LatticeHelperPropagation` above) gets ROOTED credit at exactly that
    site once every observed call site in the corpus passes it a
    provably ROOTED argument -- closing the 727-of-740-UNKNOWN gap
    T-2504's census measured."""

    def test_helper_writing_directly_to_its_own_param_gets_credit_when_every_call_is_rooted(
        self, tmp_path: Path
    ) -> None:
        """POSITIVE CONTROL: the exact `_write_fixture(tmp: Path)` shape
        the ticket names -- writes to its own param, never returns it,
        called ONLY with a `tmp_path`-derived argument -- resolves
        ROOTED, not UNKNOWN."""
        sample = _write_sample(
            tmp_path,
            'from pathlib import Path\n'
            'def _write_fixture(tmp: Path):\n'
            '    target = tmp / "sub" / "file.txt"\n'
            '    target.write_text("hi")\n'
            'def test_uses_fixture(tmp_path):\n'
            '    _write_fixture(tmp_path)\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["unknown"] == 0
        assert result.counts["rooted"] == 1
        site = result.sites[0]
        assert site.symref.endswith("::_write_fixture")
        assert site.state is ConfinementState.ROOTED

    def test_helper_that_escapes_its_param_gets_no_credit(
        self, tmp_path: Path
    ) -> None:
        """NEGATIVE CONTROL, mandatory both-directions requirement: a
        helper that REASSIGNS its own parameter to an absolute literal
        before writing must NOT receive credit -- it must resolve
        ESCAPED (the reassignment is a real, provable escape), never a
        false ROOTED pass just because it was called with a rooted
        argument."""
        sample = _write_sample(
            tmp_path,
            'from pathlib import Path\n'
            'def _escapes_param(tmp: Path):\n'
            '    tmp = Path("/etc/evil")\n'
            '    tmp.write_text("bad")\n'
            'def test_uses_escaping_helper(tmp_path):\n'
            '    _escapes_param(tmp_path)\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["rooted"] == 0
        assert result.counts["escaped"] == 1
        site = result.sites[0]
        assert site.symref.endswith("::_escapes_param")
        assert site.state is ConfinementState.ESCAPED

    def test_helper_with_one_unrooted_caller_gets_no_credit_for_any_site(
        self, tmp_path: Path
    ) -> None:
        """A helper called from TWO sites, only one of which passes a
        provably ROOTED argument, must NOT receive credit at all -- a
        partial-evidence credit would be unsound (the helper's write
        genuinely is unrooted on the OTHER caller's path). Stays
        UNKNOWN, never a false ROOTED."""
        sample = _write_sample(
            tmp_path,
            'from pathlib import Path\n'
            'def _mixed_calls(tmp: Path):\n'
            '    (tmp / "x.txt").write_text("mixed")\n'
            'def test_mixed_good(tmp_path):\n'
            '    _mixed_calls(tmp_path)\n'
            'def test_mixed_bad():\n'
            '    _mixed_calls(Path("/tmp/not_rooted"))\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["rooted"] == 0
        assert result.counts["unknown"] == 1
        site = result.sites[0]
        assert site.symref.endswith("::_mixed_calls")
        assert site.state is ConfinementState.UNKNOWN

    def test_helper_never_called_gets_no_credit(self, tmp_path: Path) -> None:
        """A helper with ZERO observed call sites (never invoked anywhere
        in the scanned corpus) has no evidence to credit against --
        absence of evidence is not evidence of confinement. Stays
        UNKNOWN, same as before T-2519."""
        sample = _write_sample(
            tmp_path,
            'from pathlib import Path\n'
            'def _never_called(tmp: Path):\n'
            '    (tmp / "x.txt").write_text("orphan")\n',
        )
        facts = scan_confinement_facts(tmp_path, [sample.name])
        result = compute_confinement_summaries(facts, list(facts))
        assert result.counts["unknown"] == 1
        assert result.counts["rooted"] == 0
