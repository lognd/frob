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
    Quantity,
    Rung,
    Waiver,
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

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_cve_fingerprint_catalog_checked_every_call(self):
        """T-0153: `evaluate_exhaustiveness` runs `check_fingerprint_catalog_
        drift` (CVEFP001) under the fixed `cve-fingerprint:catalog` pseudo-
        view every call, model-independent -- same wiring shape as
        `pii:model` below."""
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert "cve-fingerprint:catalog" in report.views_checked
        # the shipped CVE_FINGERPRINTS catalog is drift-clean by construction
        # (test_cve_fingerprint.py::TestCatalogDrift proves this directly);
        # here we prove the OPERATIONAL path surfaces zero gaps for it too.
        assert not [g for g in report.gaps if g.family == "cve-fingerprint"]

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_pii_gap_reported(self):
        """T-0154: `evaluate_exhaustiveness` joins `_pii.py::evaluate_pii` in
        under the fixed `pii:model` view; a PII-carrying node with no
        retention/erasure path surfaces as a `family="pii"` gap, same as
        every other family's join."""
        model = KernelModel(
            nodes=(Node(id="store", trust="trusted", attrs=("pii=identifier.email",)),)
        )
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert not report.proved
        assert "pii:model" in report.views_checked
        pii_gaps = [g for g in report.gaps if g.family == "pii"]
        assert len(pii_gaps) == 1
        assert pii_gaps[0].rule == "PII003"

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_lint_gap_reported(self):
        """T-0155: `evaluate_exhaustiveness` joins `_lint.py::evaluate_lint`
        in under the fixed `lint:model` view; a foreign-sourced flow with
        no declared rate surfaces as a `family="lint"` gap, same as every
        other family's join."""
        kid = _foreign("kid")
        api = Node(id="api", trust="trusted")
        flow = Flow(id="f_open", src="kid", dst="api", label="Public")
        model = KernelModel(nodes=(kid, api), flows=(flow,))
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert not report.proved
        assert "lint:model" in report.views_checked
        lint_gaps = [g for g in report.gaps if g.family == "lint"]
        assert len(lint_gaps) == 1
        assert lint_gaps[0].rule == "LINT001"


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
        # T-0155 LINT001: a foreign-sourced flow needs a declared rate to
        # stay clean under the new lint family (module-level scope note).
        rate=Quantity(value=5, unit="req/s"),
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


def _shared_two_user_model() -> KernelModel:
    """Two service users sharing a writable path and a listening port, no
    declared `Flow` between them -- the HOST001/HOST002/blast-radius VULN
    shape (`test_host_isolation.py::_shared_user_model`'s convention),
    reused here to prove T-0280's CLI-level wiring: `evaluate_
    exhaustiveness` alone, with zero hand-written harness, must surface
    HOST001/HOST002/HOST-BLAST for this model."""
    api = Node(
        id="api",
        trust="trusted",
        attrs=(
            "runs_as=svc-a",
            "unit",
            "owns=/var/lib/shared:0664",
            "listens=9000",
        ),
    )
    worker = Node(
        id="worker",
        trust="trusted",
        attrs=(
            "runs_as=svc-b",
            "unit",
            "owns=/var/lib/shared:0664",
            "listens=9000",
        ),
    )
    return KernelModel(nodes=(api, worker))


def _isolated_hardened_two_user_model() -> KernelModel:
    """Two service users with disjoint owns/listens and explicit waivers
    for the two structurally-unprovable sub-targets (shared-group,
    sudoers) -- the HOST001/HOST002 HARDENED shape (`test_host_isolation.
    py::_isolated_hardened_model`'s convention) that discharges cleanly,
    including the blast-radius scenario claims."""
    api = Node(
        id="api",
        trust="trusted",
        attrs=("runs_as=svc-a", "unit", "owns=/etc/api:0640", "listens=8080"),
        waives=(
            Waiver(
                rule="HOST001:shared-group",
                reason="no group grammar yet, T-draft-7b5b5541",
            ),
            Waiver(
                rule="HOST002:sudoers",
                reason="no sudoers grammar yet, T-draft-7b5b5541",
            ),
        ),
    )
    worker = Node(
        id="worker",
        trust="trusted",
        attrs=("runs_as=svc-b", "unit", "owns=/etc/worker:0640", "listens=8081"),
        waives=(
            Waiver(
                rule="HOST002:sudoers",
                reason="no sudoers grammar yet, T-draft-7b5b5541",
            ),
        ),
    )
    return KernelModel(nodes=(api, worker))


class TestHostWiring:
    """T-0280: HOST001/HOST002 movement proofs + the compromised-user
    blast-radius scenario were built and sound (T-0256) but had ZERO
    caller reaching them from `frob sys audit` -- these tests exercise
    `evaluate_exhaustiveness` (the same entrypoint `frob sys audit`
    dispatches to, `test_interfaces.py::TestInterfaces.
    test_main_cli_dispatches`) directly, with no hand-written harness, to
    prove the wiring closes the CLI-reachability gap."""

    def test_shared_model_gaps(self):
        model = _shared_two_user_model()
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert not report.proved

        rules = {g.rule for g in report.gaps}
        assert "HOST001" in rules
        assert "HOST002" in rules
        assert "HOST-BLAST" in rules
        assert "host:model" in report.views_checked
        assert "host:blast-radius:svc-a" in report.views_checked
        assert "host:blast-radius:svc-b" in report.views_checked

    def test_hardened_model_proved(self):
        model = _isolated_hardened_two_user_model()
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert report.proved
        assert report.gaps == ()
        waived_rules = {(g.rule, g.sub_target) for g in report.waived}
        assert ("HOST001", "shared-group") in waived_rules
        assert ("HOST002", "sudoers") in waived_rules

    def test_no_runs_as_no_gaps(self):
        """A model with no `runs_as` service users (e.g. `design/frob.
        strata`'s own self-audit model) declares no HOST001/HOST002/
        blast-radius obligation at all -- confirms T-0280's wiring adds
        zero regression for models outside its scope."""
        model = KernelModel(nodes=(Node(id="solo", trust="trusted"),))
        result = evaluate_exhaustiveness(model)
        assert result.is_ok
        report = result.danger_ok
        assert report.proved
        assert "host:model" in report.views_checked
        assert not any(v.startswith("host:blast-radius:") for v in report.views_checked)
