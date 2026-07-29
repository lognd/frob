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

from pathlib import Path
from unittest.mock import patch

from frob.gates import known_gate_rule_ids
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
    DEFAULT_QUALITY_VIEWS,
    AuditReport,
    evaluate_exhaustiveness,
    group_gaps_by_view,
)
from frob.strata._compliance import OutOfScopeRegulation
from frob.strata._threat import _discharge_claim_id


def _write(root: Path, rel: str, source: str) -> None:
    """Test helper: write `source` to `root/rel`, creating parent dirs
    (matches `test_threat.py::_write`'s convention)."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")


#: T-0503: the live gate-rule-id set (mirrors what `sys_runner.py`'s
#: production callsite passes) -- required so `COMPLIANCE_OUT_OF_SCOPE`'s
#: `caught_by="... (PII010) ..."` entry actually resolves instead of every
#: fixture in this file that used to call `evaluate_exhaustiveness(model)`
#: with the default empty `known_rule_ids` picking up a spurious COMPLIANCE004
#: gap now that the catalog is non-empty in production (T-0503's whole point).
_KNOWN_RULE_IDS = known_gate_rule_ids()


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
    # frob:ticket T-1157
    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_clean_proved(self):
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok
        assert isinstance(report, AuditReport)
        assert report.proved
        assert report.gaps == ()
        assert "security:owasp-top-10" in report.views_checked
        assert "quality:web-quality-security-baseline" in report.views_checked
        assert "compliance:all-regulations" in report.views_checked

    # frob:ticket T-1157
    # frob:tests src/frob/strata/_audit.py::_gap_rule_in_scope kind="unit"
    def test_sys205_waiver_is_not_reported_stale_by_exhaustiveness_pass(self):
        """T-1157: `check_mode_conformance` owns SYS205's own `apply_waivers`
        call (same as SYS200-203/REL200-201 already did before it) -- a
        `waive "SYS205:..."` clause must not ALSO be re-judged (and found
        stale) by this exhaustiveness pass's own `apply_waivers` call,
        since `gaps` here never contains a SYS205 finding at all (SYS205
        findings live entirely in `check_mode_conformance`'s own report).
        Regression for the bug filed by the w18-strata3 agent: the
        exhaustiveness pass's `_gap_rule_in_scope` predicate did not
        exclude SYS205, so every declared SYS205 waiver was unconditionally
        reported SYSWAIVE002-stale here regardless of whether the real
        SYS205 evaluator matched and waived it."""
        model = KernelModel(
            nodes=(
                Node(
                    id="api",
                    trust="trusted",
                    waives=(Waiver(rule="SYS205:some-resource", reason="test"),),
                ),
            )
        )
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok
        assert not any(gap.rule == "SYSWAIVE002" for gap in report.gaps)

    # frob:ticket T-0512
    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_default_run_discloses_narrower_than_baseline(self):
        """strata audit G6, counterexample #1: a default `frob sys audit`
        run's `security_views` (`DEFAULT_SECURITY_VIEWS`) does NOT include
        `cwe-top-25` -- proving that gap is DISCLOSED (`AuditReport.
        narrower_than_baseline == ("cwe-top-25",)`), not silently true the
        way it was before this fix (a PROVED report with zero mention that
        cwe-top-25 was never checked)."""
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok
        assert report.proved
        assert report.narrower_than_baseline == ("cwe-top-25",)

    # frob:ticket T-0512
    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_explicit_full_security_views_clears_the_disclosure(self):
        """strata audit G6, counterexample #2: a caller who explicitly
        passes BOTH baseline security views (`owasp-top-10` AND
        `cwe-top-25`) gets an EMPTY `narrower_than_baseline` -- proving the
        disclosure genuinely tracks configured-vs-baseline, not a hardcoded
        always-on warning."""
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        result = evaluate_exhaustiveness(
            model,
            security_views=("owasp-top-10", "cwe-top-25"),
            known_rule_ids=_KNOWN_RULE_IDS,
        )
        assert result.is_ok
        report = result.danger_ok
        assert report.narrower_than_baseline == ()

    # frob:ticket T-0499
    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_known_rule_ids_reaches_compliance_caught_by_check(self):
        """T-0499: `known_rule_ids` passed to `evaluate_exhaustiveness`
        must reach `evaluate_compliance`'s own `known_rule_ids` param (its
        COMPLIANCE004 caught_by check), not just the THREAT006 caught_by
        path -- both families were named in the ticket's dormant-wiring
        gap. Asserted via the actual kwarg `evaluate_compliance` is called
        with, since no `OutOfScopeRegulation` catalog is threaded into this
        module yet (a separate, out-of-scope gap) to observe a firing/
        non-firing COMPLIANCE004 violation end-to-end."""
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        rule_ids = frozenset({"SEC001"})
        with patch(
            "frob.strata._audit.evaluate_compliance",
            wraps=__import__(
                "frob.strata._audit", fromlist=["evaluate_compliance"]
            ).evaluate_compliance,
        ) as spy:
            result = evaluate_exhaustiveness(model, known_rule_ids=rule_ids)
        assert result.is_ok
        assert spy.call_count > 0
        for call in spy.call_args_list:
            assert call.kwargs["known_rule_ids"] == rule_ids

    # frob:ticket T-0503
    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_compliance_out_of_scope_reaches_real_audit_path(self):
        """T-0503: `COMPLIANCE_OUT_OF_SCOPE` is now threaded into
        `_compliance_pii_lint_fingerprint_gaps` -> `evaluate_compliance`
        (the exact production callsite `frob.app.sys_runner._evaluate_audit`
        dispatches through via `evaluate_exhaustiveness`), so COMPLIANCE004
        is no longer vacuous -- unlike `test_known_rule_ids_reaches_
        compliance_caught_by_check` above, this exercises the REAL
        production catalog (not a mock), with the live gate-rule-id set, and
        proves it discharges clean end-to-end."""
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok
        assert not [g for g in report.gaps if g.rule == "COMPLIANCE004"]

    # frob:ticket T-0503
    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_compliance_out_of_scope_bad_caught_by_fails_real_audit_path(self):
        """T-0503 non-vacuous proof: a `caught_by` naming a control that does
        not exist in `known_rule_ids` must FAIL through the real production
        entrypoint (`evaluate_exhaustiveness`, exactly what `frob sys audit`
        calls), not just `_check_regulation_caught_by_integrity` in isolation.
        Monkeypatches the production `COMPLIANCE_OUT_OF_SCOPE` constant
        `_audit.py` imports to swap in a fabricated `caught_by` -- the
        counterexample half of the litmus pair completed by the clean case
        above (`test_compliance_out_of_scope_reaches_real_audit_path`)."""
        bad_entry = OutOfScopeRegulation(
            id="CCPA",
            reason="test counterexample: a fabricated caught_by",
            owner="logan",
            review="2027-01-21",
            caught_by="a nonexistent control (FAKE999)",
        )
        model = KernelModel(nodes=(Node(id="api", trust="trusted"),))
        with patch("frob.strata._audit.COMPLIANCE_OUT_OF_SCOPE", (bad_entry,)):
            result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok
        assert not report.proved
        compliance004_gaps = [g for g in report.gaps if g.rule == "COMPLIANCE004"]
        # one COMPLIANCE004 gap per configured compliance view (mirrors the
        # per-view repetition every other family gap already gets).
        assert compliance004_gaps
        assert all("FAKE999" in g.detail for g in compliance004_gaps)

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
    def test_security_only_capability_does_not_fire_threat002_in_quality_view(self):
        """T-0171: `exec` is classified in `CWE_CATALOG` (CWE-78, security
        family) but has NO entry in `QUALITY_CATALOG` at all (comment above
        `DEFAULT_BENIGN_CAPABILITIES` in `_threat.py`) -- reproduces the
        logand.app pilot's shape: a node declaring a security-family-only
        capability must not fire THREAT002 against a quality-family view
        just because that family's OWN narrower catalog has no matching
        entry. `evaluate_exhaustiveness` proves the model clean of THREAT002
        gaps for `web-quality-security-baseline` (a quality view) even
        though `exec` is genuinely unclassified by `QUALITY_CATALOG` alone
        -- it IS classified by the taxonomy overall (`ALL_CATALOG`), which
        is the fact THREAT002 is supposed to test (docs/strata/threat.md
        #phasing item B: "every capability kind ... is classified", not
        "classified by this one family's subset")."""
        model = KernelModel(nodes=(Node(id="worker", trust="trusted", may=("exec",)),))
        result = evaluate_exhaustiveness(model, quality_views=DEFAULT_QUALITY_VIEWS)
        assert result.is_ok
        report = result.danger_ok
        threat002_gaps = [g for g in report.gaps if g.rule == "THREAT002"]
        assert threat002_gaps == []

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
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
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
            "group=ops",
            "sudoers=ALL=(root) NOPASSWD: /bin/true",
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
            "group=ops",
        ),
    )
    return KernelModel(nodes=(api, worker))


def _isolated_hardened_two_user_model() -> KernelModel:
    """Two service users with disjoint owns/listens/groups and no
    declared sudoers grant (`test_host_isolation.py::
    _isolated_hardened_model`'s convention) that discharges cleanly with
    no waivers needed at all (T-0272 closed the shared-group/sudoers
    honest gap), including the blast-radius scenario claims."""
    api = Node(
        id="api",
        trust="trusted",
        attrs=(
            "runs_as=svc-a",
            "unit",
            "owns=/etc/api:0640",
            "listens=8080",
            "group=api-grp",
        ),
    )
    worker = Node(
        id="worker",
        trust="trusted",
        attrs=(
            "runs_as=svc-b",
            "unit",
            "owns=/etc/worker:0640",
            "listens=8081",
            "group=worker-grp",
        ),
    )
    return KernelModel(nodes=(api, worker))


class TestGroupGaps:
    """T-0173: `frob sys audit` was printing an IDENTICAL WARNING block once
    per configured view whenever the same underlying gap held under every
    view in that family -- `_vulnerable_model`'s undischarged CWE-639 fires
    on all three `DEFAULT_QUALITY_VIEWS` views identically. `group_gaps_by_
    view` must collapse that into ONE group naming every affected view,
    while a genuinely single-view gap (the security CWE-89 gap, which only
    fires under `owasp-top-10`) stays its own single-view group -- and the
    underlying `report.gaps` count (the verdict) must stay untouched."""

    # frob:tests \
    # tests/unit/strata/test_audit.py::TestGroupGaps.test_group_gaps_by_view kind="unit"
    def test_group_gaps_by_view(self):
        model = _vulnerable_model()
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok

        # the raw gap set is untouched -- the verdict-affecting count.
        # (1 security CWE-89 + 3 quality CWE-639, one per DEFAULT_QUALITY_
        # VIEWS view + 4 compliance COPPA, one per DEFAULT_COMPLIANCE_VIEWS
        # view + 1 lint LINT001 -- measured via `pytest -s` on this model.)
        assert len(report.gaps) == 9

        grouped = group_gaps_by_view(report.gaps)

        # no two groups render an identical (family, rule, detail) block --
        # that is exactly the bug: the same content printed N times.
        blocks = [(g.family, g.rule, g.detail) for g in grouped]
        assert len(blocks) == len(set(blocks)), (
            "duplicate verbatim block in grouped output"
        )

        # the CWE-639 quality gap fired under all 3 configured quality
        # views -- it must collapse into ONE group naming all three.
        quality_group = next(
            g for g in grouped if g.family == "quality" and "CWE-639" in g.detail
        )
        assert set(quality_group.views) == set(DEFAULT_QUALITY_VIEWS)
        assert len(quality_group.views) == len(DEFAULT_QUALITY_VIEWS)

        # the CWE-89 security gap is genuinely single-view -- it must NOT
        # be collapsed away or merged with anything else.
        security_group = next(
            g for g in grouped if g.family == "security" and "CWE-89" in g.detail
        )
        assert security_group.views == ("owasp-top-10",)

        # the compliance COPPA gap fired under all 4 configured compliance
        # views -- it must also collapse into ONE group.
        compliance_group = next(g for g in grouped if g.family == "compliance")
        assert len(compliance_group.views) == 4

        # the full set of genuinely distinct gaps is preserved: security,
        # quality, compliance, and lint groups are all still present, and
        # grouping shrank the 9 raw gaps down to exactly 4 printed blocks.
        families = {g.family for g in grouped}
        assert families == {"security", "quality", "compliance", "lint"}
        assert len(grouped) == 4

        # T-0512 (strata audit G6): a default run's security views are
        # STILL narrower than the full catalog baseline (`cwe-top-25` is
        # not among `DEFAULT_SECURITY_VIEWS`) -- that must be DISCLOSED,
        # not silently true.
        assert report.narrower_than_baseline == ("cwe-top-25",)


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
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok
        assert report.proved
        assert report.gaps == ()
        # T-0272: no waivers needed -- disjoint groups and no declared
        # sudoers grant structurally prove both sub-targets false.
        assert report.waived == ()

    def test_no_runs_as_no_gaps(self):
        """A model with no `runs_as` service users (e.g. `design/frob.
        strata`'s own self-audit model) declares no HOST001/HOST002/
        blast-radius obligation at all -- confirms T-0280's wiring adds
        zero regression for models outside its scope."""
        model = KernelModel(nodes=(Node(id="solo", trust="trusted"),))
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok
        assert report.proved
        assert "host:model" in report.views_checked
        assert not any(v.startswith("host:blast-radius:") for v in report.views_checked)

    def test_owns_without_runs_as_no_blast_radius_scenario(self):
        """T-1164 regression: a node declaring `owns`/`acl` with no
        `runs_as` service-account claim has a manifest (`host_manifest_for`
        returns non-None once ANY std.host construct is present) but no
        real compromised-user identity -- `_blast_radius_gaps_per_user`
        must not synthesize a spurious `host:blast-radius:None` scenario
        from the bare `None` `runs_as` value. Mirrors `design/frob.strata`'s
        `tickets_ledger` writer nodes (T-1158), which declare `owns` with
        no `runs_as`."""
        node = Node(id="writer", trust="trusted", attrs=("owns=/data/x:0644",))
        model = KernelModel(nodes=(node,))
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        report = result.danger_ok
        assert not any(v.startswith("host:blast-radius:") for v in report.views_checked)
        assert not any(v == "host:blast-radius:None" for v in report.views_checked)
        assert not any(g.rule == "HOST-BLAST" for g in report.gaps)


# frob:ticket T-0630
class TestCodeBoundWiring:
    """T-0630's acceptance repro: `evaluate_exhaustiveness` -- the exact
    function `frob.app.sys_runner._evaluate_audit` calls for `frob sys
    audit` -- must actually FIRE THREAT003's G1 code-bound-predicate join
    (docs/audits/strata.md, T-0595) when a real `root` is supplied, not
    only when a unit test constructs a `CodeBinding` by hand and calls
    `check_discharge_completeness` directly (`test_threat.py::
    TestCodeBoundMitigationPredicate`, which this class deliberately does
    NOT duplicate -- it proves the join exists; this proves the join is
    actually WIRED to the production entrypoint, closing the catalogued-
    is-not-enforced gap T-0595's Done report disclosed)."""

    def _model(self, claim_id: str) -> KernelModel:
        """The same Evil->Web/ENDORSE-boundary/CWE-79 fixture shape
        `test_threat.py::TestCodeBoundMitigationPredicate._model` uses."""
        evil = Node(id="Evil", trust="foreign")
        web = Node(
            id="Web", trust="trusted", may=("html_render",), attrs=("code=api/**",)
        )
        return KernelModel(
            nodes=(evil, web),
            flows=(
                Flow(
                    id="f1",
                    src="Evil",
                    dst="Web",
                    # T-0155 LINT001: a foreign-sourced flow needs a
                    # declared rate to stay clean under the lint family
                    # (matches `_hardened_model`'s own scope note above).
                    rate=Quantity(value=5, unit="req/s"),
                ),
            ),
            boundaries=(
                Boundary(
                    id="b1",
                    flow_id="f1",
                    direction=BoundaryDirection.ENDORSE,
                    from_level="foreign",
                    to_level="trusted",
                    predicate="output_encoding",
                    obligations=(claim_id,),
                ),
            ),
            claims=(
                Claim(
                    id=claim_id,
                    body=NoFlow(src="foreign", dst="Web"),
                    required_rung=Rung.L4,
                ),
            ),
        )

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_root_wires_real_code_binding_and_surfaces_threat003(self, tmp_path: Path):
        """`output_encoding` resolves to a real claim (T-0498 weaker half)
        but is never CALLED anywhere in Web's bound code on this fixture
        repo -- passing `root=tmp_path` to `evaluate_exhaustiveness` (the
        real `frob sys audit` gate path) must fail closed with a named
        THREAT003 gap citing the unbound boundary, exactly like the
        `binding=`/`root=`-supplied unit call to `check_discharge_
        completeness` already does. Before T-0630, `evaluate_exhaustiveness`
        took no `root` at all and this repo would report PROVED."""
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = self._model(claim_id)
        _write(
            tmp_path,
            "api/handler.py",
            '"""Uses output_encoding somewhere in a comment, never calls it."""\n'
            "def render(x):\n"
            "    return x\n",
        )
        result = evaluate_exhaustiveness(
            model, known_rule_ids=_KNOWN_RULE_IDS, root=tmp_path
        )
        assert result.is_ok
        report = result.danger_ok
        assert not report.proved
        gap_details = [g.detail for g in report.gaps]
        assert any(
            "b1" in detail and "no OBSERVED sanitizer" in detail
            for detail in gap_details
        ), gap_details

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_root_with_real_call_site_still_proves_clean(self, tmp_path: Path):
        """The positive twin: `output_encoding(...)` really is CALLED in
        Web's own bound code on the same fixture repo shape -- `frob sys
        audit`'s real gate path must still report PROVED, confirming the
        new `root=` wiring is not a blanket new failure, only a real join."""
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = self._model(claim_id)
        _write(
            tmp_path,
            "api/handler.py",
            "def render(x):\n    return output_encoding(x)\n",
        )
        result = evaluate_exhaustiveness(
            model, known_rule_ids=_KNOWN_RULE_IDS, root=tmp_path
        )
        assert result.is_ok
        assert result.danger_ok.proved

    # frob:tests src/frob/strata/_audit.py::evaluate_exhaustiveness kind="unit"
    def test_no_root_preserves_pre_t0630_model_only_posture(self, tmp_path: Path):
        """Omitting `root` (the pre-T-0630 default) must keep discharging
        via T-0498's weaker half alone -- a design-level-only caller with
        no code tree is not newly broken by this wiring."""
        claim_id = _discharge_claim_id("CWE-79", "Web")
        model = self._model(claim_id)
        _write(
            tmp_path,
            "api/handler.py",
            '"""Uses output_encoding somewhere in a comment, never calls it."""\n'
            "def render(x):\n"
            "    return x\n",
        )
        result = evaluate_exhaustiveness(model, known_rule_ids=_KNOWN_RULE_IDS)
        assert result.is_ok
        assert result.danger_ok.proved
