"""Unit tests for `frob sys audit`'s model-side entrypoint (T-0115,
docs/strata/threat.md#the-exhaustiveness-proof-the-point item F).

Includes the vuln-litmus/hardened-twin pair the ticket names: a
deliberately-vulnerable model firing at least one undischarged obligation
per family (security, quality, compliance), refuted by `frob sys audit`
with exactly the expected named gaps, and its hardened twin proving clean.

Scope note (out-of-scope discovery, filed as T-0137): the litmus pair here
is built as `KernelModel` fixtures directly, the SAME convention every
existing `_threat.py`/`_compliance.py` obligation test already uses
(`test_threat.py`, `test_compliance.py` -- neither constructs a discharge
claim through `design/litmus/*.strata` surface source). The reason: a
`weakness:<cwe-id>:<node-id>` / `compliance:<reg-id>:<target-id>` discharge
claim id (`_threat.py::_discharge_claim_id`, `_compliance.py` docstring)
always contains a `:` -- and, for any real CWE id (e.g. `CWE-89`), a `-`
too -- but `strata-core/src/parse.rs::parse_claim`'s claim id is a bare
IDENT (`expect_ident("claim id")`, alnum+underscore only, no `:`/`-`
allowed in `is_ident_cont`). So no `.strata` source file can currently
author a claim that discharges a THREAT00x/COMPLIANCE00x obligation at
all -- a real surface-grammar gap, but `strata-core/**` is outside T-0115's
scope. Filed as T-0137 rather than fixed silently."""

from __future__ import annotations

from frob.strata import (
    Boundary,
    BoundaryDirection,
    Claim,
    Flow,
    KernelModel,
    Node,
    NoFlow,
    Rung,
)
from frob.strata._audit import (
    AuditReport,
    evaluate_exhaustiveness,
)
from frob.strata._threat import _discharge_claim_id


def _foreign(node_id: str) -> Node:
    """A `foreign`-trust node -- the source every discharge chokepoint in
    this file's fixtures reasons about (mirrors `test_threat.py`'s NoFlow
    fixtures)."""
    return Node(id=node_id, trust="foreign")


def _assumed_claim(claim_id: str, *, src: str, dst: str) -> Claim:
    """An ASSUMED discharge claim with owner+review: the discharge check
    (`_threat.py::_check_one_discharge`) skips the mitigation-chokepoint
    re-evaluation for assumed claims (`if not claim.assumed and not
    _mitigation_is_chokepoint(...)`), so this is a clean, minimal way to
    PROVE discharge in a fixture without also constructing a real ENDORSE
    boundary of the exact cited mitigation kind."""
    return Claim(
        id=claim_id,
        body=NoFlow(src=src, dst=dst),
        required_rung=Rung.L4,
        assumed=True,
        owner="logan",
        review="2026-10-01",
    )


class TestExhaustiveness:
    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_clean_proved(self):
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert isinstance(report, AuditReport)
        assert report.proved
        assert report.gaps == ()
        assert "security:owasp-top-10" in report.views_checked
        assert "quality:web-quality-security-baseline" in report.views_checked
        assert "compliance:all-regulations" in report.views_checked

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_unknown_view_errs(self):
        model = KernelModel(nodes=())
        result = evaluate_exhaustiveness(model, security_views=("no-such-view",))
        assert result.is_err


def _vulnerable_model() -> KernelModel:
    """The deliberately-vulnerable litmus model: one `may "sql"` capability
    firing an undischarged obligation in BOTH the security (CWE-89) and
    quality (CWE-639, same capability kind, docs/strata/threat.md#beyond-
    security-the-anti-pattern-families) catalogs, plus a `subject:child`
    collection flow into a Pii store with no boundary, firing COPPA
    (compliance). No claim discharges any of the three -- all fire
    undischarged."""
    kid = _foreign("browser_kid")
    web = Node(id="web", trust="trusted", may=("sql",))
    store = Node(id="store", trust="trusted", clearance="Pii")
    collect = Flow(
        id="f_collect",
        src="browser_kid",
        dst="store",
        label="Pii",
        attrs=("subject:child",),
    )
    return KernelModel(nodes=(kid, web, store), flows=(collect,))


def _hardened_model() -> KernelModel:
    """The hardened twin: the SAME firing preconditions as `_vulnerable_
    model`, each discharged -- `weakness:CWE-89:web` and `weakness:CWE-639:
    web` as ASSUMED NoFlow claims (owner+review), and an ENDORSE boundary
    on the collection flow (COPPA's precise mitigation shape,
    `_compliance.py::_check_coppa`: "any ENDORSE boundary on that flow")."""
    kid = _foreign("browser_kid")
    web = Node(id="web", trust="trusted", may=("sql",))
    store = Node(id="store", trust="trusted", clearance="Pii")
    collect = Flow(
        id="f_collect",
        src="browser_kid",
        dst="store",
        label="Pii",
        attrs=("subject:child",),
    )
    age_gate = Boundary(
        id="b_age_gate",
        flow_id="f_collect",
        direction=BoundaryDirection.ENDORSE,
        predicate="age_gate_boundary",
        from_level="foreign",
        to_level="authenticated",
    )
    claims = (
        _assumed_claim(_discharge_claim_id("CWE-89", "web"), src="foreign", dst="web"),
        _assumed_claim(_discharge_claim_id("CWE-639", "web"), src="foreign", dst="web"),
    )
    return KernelModel(
        nodes=(kid, web, store), flows=(collect,), boundaries=(age_gate,), claims=claims
    )


class TestVulnLitmus:
    """T-0115 vuln-litmus exit criterion: `frob sys audit`'s model-side
    entrypoint refutes the vulnerable model with EXACTLY the expected named
    gap per family."""

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_refutes_gap_per_family(self):
        model = _vulnerable_model()
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert not report.proved

        # security: THREAT003 undischarged CWE-89 on web
        assert any(
            g.family == "security" and g.rule == "THREAT003" and "CWE-89" in g.detail
            for g in report.gaps
        )
        # quality: THREAT003 undischarged CWE-639 on web
        assert any(
            g.family == "quality" and g.rule == "THREAT003" and "CWE-639" in g.detail
            for g in report.gaps
        )
        # compliance: COMPLIANCE002 undischarged COPPA on f_collect
        assert any(
            g.family == "compliance"
            and g.rule == "COMPLIANCE002"
            and g.view == "us-coppa"
            and "f_collect" in g.detail
            for g in report.gaps
        )


class TestHardenedLitmus:
    """T-0115 vuln-litmus exit criterion: the hardened twin proves clean --
    zero gaps for every obligation the vulnerable model fired."""

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_hardened_clean(self):
        model = _hardened_model()
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert report.proved
        assert report.gaps == ()
