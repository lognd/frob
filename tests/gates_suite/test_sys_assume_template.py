"""Tests for the templated-assume gate (D-M8, T-5105).

`TestFindTemplatedAssumes`/`TestFindSharedExpiry` exercise the pure
detectors in `frob.strata._assume_template` directly with synthetic
`Claim`s. `TestSelfaudit001TemplatedAssume` is the ticket's MANDATORY
positive control: the gate must be RED against today's real
`design/frob.strata` (the 33 boilerplate CWE assumes SF-08 measured) --
a green result there means the detector does not work.
"""
# frob:ticket T-5105

from __future__ import annotations

from pathlib import Path

from frob.gates._sys_selfaudit import _templated_assume_violations
from frob.strata._assume_template import (
    ModuleClaim,
    find_shared_expiry,
    find_templated_assumes,
    module_claims_from_models,
)
from frob.strata._models import Claim, NoFlow


def _assume(
    claim_id: str,
    dst: str,
    *,
    src: str = "registry",
    owner: str = "logan",
    review: str = "2026-10-15",
) -> Claim:
    """Build one `assume "id" noflow src -> dst owner .. review ".."`-shaped
    `Claim`, the exact SF-08 boilerplate shape, for test fixtures."""
    return Claim(
        id=claim_id,
        body=NoFlow(src=src, dst=dst),
        assumed=True,
        owner=owner,
        review=review,
    )


# frob:ticket T-5105
class TestFindTemplatedAssumes:
    """`find_templated_assumes` (pure, no design tree needed)."""

    # frob:tests src/frob/strata/_assume_template.py::find_templated_assumes kind="unit"
    # frob:tests src/frob/strata/_assume_template.py::TemplatedAssumeGroup
    def test_red_on_monolith_cwe78_cluster(self) -> None:
        """GIVEN 3 assumes shaped exactly like design/frob.strata's CWE-78
        cluster (same weakness code, same owner/review, only the node
        differs) WHEN `find_templated_assumes` runs THEN it reports one
        group naming all 3 -- the exact SF-08 shape, proving the detector
        fires on the real boilerplate pattern before it is even run
        against the real file."""
        claims = [
            ModuleClaim(
                claim=_assume("weakness:CWE-78:claude_hooks", "claude_hooks"),
                module="frob",
            ),
            ModuleClaim(
                claim=_assume("weakness:CWE-78:scripts_ops", "scripts_ops"),
                module="frob",
            ),
            ModuleClaim(
                claim=_assume("weakness:CWE-78:checker", "checker"), module="frob"
            ),
        ]
        groups = find_templated_assumes(claims)
        assert len(groups) == 1
        assert set(groups[0].claim_ids) == {
            "weakness:CWE-78:claude_hooks",
            "weakness:CWE-78:scripts_ops",
            "weakness:CWE-78:checker",
        }
        assert set(groups[0].nodes) == {"claude_hooks", "scripts_ops", "checker"}

    # frob:tests src/frob/strata/_assume_template.py::find_templated_assumes kind="unit"
    def test_distinct_weakness_class_not_merged(self) -> None:
        """GIVEN two assumes about the SAME node but DIFFERENT weakness
        classes (CWE-78 vs CWE-94) WHEN `find_templated_assumes` runs THEN
        neither is reported -- the weakness code is not the substituted
        node token, so it is preserved in the signature and the two do not
        collapse into one template group (a real difference sharing
        keywords must not be flagged)."""
        claims = [
            ModuleClaim(claim=_assume("weakness:CWE-78:cli", "cli"), module="frob"),
            ModuleClaim(claim=_assume("weakness:CWE-94:cli", "cli"), module="frob"),
        ]
        groups = find_templated_assumes(claims)
        assert groups == ()

    # frob:tests src/frob/strata/_assume_template.py::find_templated_assumes kind="unit"
    def test_genuinely_specific_assume_not_reported(self) -> None:
        """GIVEN one boilerplate-shaped assume and one assume whose `id`
        embeds a concrete, module-specific mechanism (not just the node
        name) WHEN `find_templated_assumes` runs THEN the specific assume
        is not grouped with anything -- its token stream differs by more
        than the substituted node identifier, so it is not templated."""
        claims = [
            ModuleClaim(claim=_assume("weakness:CWE-78:vet", "vet"), module="frob"),
            ModuleClaim(
                claim=_assume(
                    "weakness:CWE-78:vet:validated-via-shlex-quote-and-allowlist",
                    "vet",
                ),
                module="frob",
            ),
        ]
        groups = find_templated_assumes(claims)
        assert groups == ()

    # frob:tests src/frob/strata/_assume_template.py::find_templated_assumes kind="unit"
    def test_non_assumed_claim_excluded(self) -> None:
        """GIVEN two identically-shaped claims where one is a real `assert`
        (`assumed=False`) WHEN `find_templated_assumes` runs THEN neither
        is reported -- only ASSUMED claims (owned, expiring TCB entries)
        are in scope for the templated-assume gate; a proven assertion is
        not boilerplate."""
        asserted = Claim(
            id="weakness:CWE-78:cli", body=NoFlow(src="registry", dst="cli")
        )
        claims = [
            ModuleClaim(claim=asserted, module="frob"),
            ModuleClaim(claim=_assume("weakness:CWE-78:cli2", "cli2"), module="frob"),
        ]
        groups = find_templated_assumes(claims)
        assert groups == ()


# frob:ticket T-5105
class TestFindSharedExpiry:
    """`find_shared_expiry` (pure, no design tree needed)."""

    # frob:tests src/frob/strata/_assume_template.py::find_shared_expiry kind="unit"
    def test_red_on_monolith_shared_date(self) -> None:
        """GIVEN assumes from 3 distinct modules all sharing one review
        date, with `max_modules=2` WHEN `find_shared_expiry` runs THEN it
        reports one group naming all 3 modules -- more than N modules
        sharing a single expiry date is exactly SF-08's second smell (one
        date, `2026-10-15`, for all 33 assumes)."""
        claims = [
            ModuleClaim(claim=_assume("a", "node_a"), module="platform"),
            ModuleClaim(claim=_assume("b", "node_b"), module="gates"),
            ModuleClaim(claim=_assume("c", "node_c"), module="tickets"),
        ]
        groups = find_shared_expiry(claims, max_modules=2)
        assert len(groups) == 1
        assert groups[0].review == "2026-10-15"
        assert set(groups[0].modules) == {"platform", "gates", "tickets"}
        assert set(groups[0].claim_ids) == {"a", "b", "c"}

    # frob:tests src/frob/strata/_assume_template.py::find_shared_expiry kind="unit"
    def test_at_or_below_n_modules_not_reported(self) -> None:
        """GIVEN assumes sharing one review date across exactly
        `max_modules` (2) distinct modules WHEN `find_shared_expiry` runs
        THEN nothing is reported -- the finding requires MORE than N, not
        N or fewer."""
        claims = [
            ModuleClaim(claim=_assume("a", "node_a"), module="platform"),
            ModuleClaim(claim=_assume("b", "node_b"), module="gates"),
        ]
        groups = find_shared_expiry(claims, max_modules=2)
        assert groups == ()

    # frob:tests src/frob/strata/_assume_template.py::find_shared_expiry kind="unit"
    def test_distinct_review_dates_not_grouped(self) -> None:
        """GIVEN assumes across many modules but each with its OWN distinct
        review date WHEN `find_shared_expiry` runs THEN nothing is
        reported -- a deliberately different per-module date is not the
        copy-forward smell this check targets."""
        claims = [
            ModuleClaim(
                claim=_assume("a", "node_a", review="2026-11-01"), module="platform"
            ),
            ModuleClaim(
                claim=_assume("b", "node_b", review="2026-11-02"), module="gates"
            ),
            ModuleClaim(
                claim=_assume("c", "node_c", review="2026-11-03"), module="tickets"
            ),
        ]
        groups = find_shared_expiry(claims, max_modules=2)
        assert groups == ()


# frob:ticket T-5105
class TestModuleClaimsFromModels:
    """`module_claims_from_models` -- the `{module: claims}` -> flat
    `ModuleClaim` sequence seam `frob.gates._sys_selfaudit` calls."""

    # frob:tests src/frob/strata/_assume_template.py::module_claims_from_models \
    # kind="unit"
    def test_flattens_and_tags_each_claim_with_its_module(self) -> None:
        """GIVEN a `{module_label: claims}` mapping with two modules WHEN
        `module_claims_from_models` runs THEN every claim reappears exactly
        once, tagged with the module label it came from."""
        models_by_module = {
            "platform": [_assume("a", "node_a"), _assume("b", "node_b")],
            "gates": [_assume("c", "node_c")],
        }
        result = module_claims_from_models(models_by_module)
        assert len(result) == 3
        assert all(isinstance(mc, ModuleClaim) for mc in result)
        by_id = {mc.claim.id: mc.module for mc in result}
        assert by_id == {"a": "platform", "b": "platform", "c": "gates"}

    # frob:tests src/frob/strata/_assume_template.py::module_claims_from_models \
    # kind="unit"
    def test_empty_mapping_yields_empty_tuple(self) -> None:
        """GIVEN an empty mapping WHEN `module_claims_from_models` runs
        THEN it returns an empty tuple, never raising."""
        assert module_claims_from_models({}) == ()


class TestSelfaudit001TemplatedAssume:
    """`_templated_assume_violations`'s production wiring, run against the
    REPO'S OWN real `design/frob.strata` -- the ticket's mandatory
    positive control."""

    # frob:tests src/frob/gates/_sys_selfaudit.py::_templated_assume_violations \
    # kind="unit"
    # invariant spec: [INV-041](invariants/INV-041.md)
    def test_red_on_todays_design_frob_strata(self) -> None:
        """GIVEN today's REAL `design/frob.strata` in this repo (SF-08: 33
        boilerplate CWE assumes, one `noflow registry -> <node> owner
        logan review "2026-10-15"` shape per node per weakness class,
        clustered into 6 groups by weakness code -- CWE-78 x18, CWE-94 x6,
        CWE-89 x3, CWE-502/639/918 x2 each) WHEN
        `_templated_assume_violations` runs against this repo's own root
        THEN it is RED: exactly the 6 SF-08 clusters are reported as
        SYS119 templated-assume findings, together naming all 33 assumed
        claim ids. A green (empty) result here means the detector does
        not work and this leaf is not done (ticket body, mandatory
        positive control). SYS120 (shared-expiry) is a SEPARATE finding
        that needs >1 distinct MODULE sharing a date to fire -- today's
        design/frob.strata is still one monolithic file (one module,
        `_templated_assume_module_claims`'s file-stem fallback), so it
        cannot fire yet; SYS119 alone is this leaf's mandated positive
        control (acceptance criterion 1)."""
        repo_root = Path(__file__).resolve().parents[2]
        assert (repo_root / "design" / "frob.strata").is_file(), (
            "expected to find this repo's own design/frob.strata -- "
            "positive control requires the real file, not a fixture"
        )
        violations = _templated_assume_violations(repo_root, "design")
        sys114 = [v for v in violations if "SYS119" in v.message]
        assert len(sys114) == 6, (
            "expected the 6 SF-08 weakness-code clusters as SYS119 "
            f"findings; got {len(sys114)}: {[v.message for v in sys114]}"
        )
        all_ids = {
            claim_id
            for v in sys114
            for claim_id in v.message.split(" -- ", 1)[1]
            .split(". Write")[0]
            .split(", ")
        }
        assert len(all_ids) == 33, (
            f"expected all 33 SF-08 boilerplate assumes named; got {len(all_ids)}"
        )

    # frob:tests src/frob/gates/_sys_selfaudit.py::_templated_assume_violations \
    # kind="unit"
    def test_module_owned_specific_assume_not_reported(self, tmp_path: Path) -> None:
        """GIVEN a `.strata` file with ONE module-owned specific assume
        (its id names a concrete mechanism, not just the node) WHEN
        `_templated_assume_violations` runs THEN it reports nothing --
        acceptance criterion 4: a specific assume is not templated."""
        design_dir = tmp_path / "design"
        design_dir.mkdir()
        (design_dir / "m.strata").write_text(
            "module m\n"
            'node vet : trusted { code "src/frob/vet/**"; }\n'
            'assume "weakness:CWE-78:vet:validated-via-shlex-quote-allowlist" '
            'noflow registry -> vet owner logan review "2026-11-01"\n'
        )
        violations = _templated_assume_violations(tmp_path, "design")
        assert violations == []
