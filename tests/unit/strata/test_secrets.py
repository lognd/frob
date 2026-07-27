"""Unit tests for std.secrets (docs/strata/surface.md#std-secrets, T-0082).

Covers: issued-by/audience/lifetime/revocation elaboration
(`_secrets.py::elaborate_secret`), the mandatory-revocation deny-by-default
(same rule as `MissingInvalidation`), the auto-generated `readers() == S`
exact-set-closure claim (`_claims.py::_eval_set_equality`), and reuse (not a
fork) of the existing clearance-violation machinery for
secret-in-logs/repo/artifact.
"""

from __future__ import annotations

from frob.strata import (
    Boundary,
    BoundaryDirection,
    Claim,
    Flow,
    KernelModel,
    Metric,
    Node,
    Quantifier,
    Quantity,
    Reach,
    SecretSpec,
    StrataError,
    Verdict,
    build_facts,
    elaborate_secret,
    evaluate_claims,
)
from frob.strata._models import BoundClaim


def _issuer_and_readers(*reader_ids: str) -> dict[str, Node]:
    """A trusted issuer plus one trusted node per reader id, keyed by id."""
    known = {"vault": Node(id="vault", trust="trusted", clearance="Secret")}
    for reader_id in reader_ids:
        known[reader_id] = Node(id=reader_id, trust="trusted", clearance="Secret")
    return known


class TestSecretElaboration:
    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    def test_issue_flow_carries_lifetime_as_age(self):
        known = _issuer_and_readers("api")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        issue = next(f for f in expansion.flows if f.id == "db_cred__issue")
        assert issue.src == "vault"
        assert issue.dst == "db_cred"
        assert issue.age == Quantity(value=1.0, unit="h")
        assert issue.label == "Secret"

    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    def test_revocation_edge_is_mandatory(self):
        known = _issuer_and_readers("api")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=None,
        )
        result = elaborate_secret(spec, known)
        assert result.danger_err is StrataError.MissingRevocation

    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    def test_revocation_edge_present_when_declared(self):
        known = _issuer_and_readers("api")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        revoke = next(f for f in expansion.flows if f.id == "db_cred__revoke")
        assert revoke.src == "vault"
        assert revoke.dst == "db_cred"
        assert "revocation" in revoke.attrs

    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    def test_unknown_issuer_fails_closed(self):
        spec = SecretSpec(
            id="db_cred",
            issued_by="nobody",
            audience=(),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        result = elaborate_secret(spec, {})
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    def test_unknown_audience_member_fails_closed(self):
        known = _issuer_and_readers()
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("ghost",),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        result = elaborate_secret(spec, known)
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    # frob:waive DUP001 reason="parallel secrets-gate case table: independent \
    # fire/no-fire cases sharing an arrange-act scaffold; extracting would obscure \
    # per-case intent"
    def test_lifetime_wrong_dimension_fails_closed(self):
        known = _issuer_and_readers("api")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=5.0, unit="MiB"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        result = elaborate_secret(spec, known)
        assert result.danger_err is StrataError.UnitMismatch

    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    # frob:waive DUP001 reason="parallel secrets-gate case table: independent \
    # fire/no-fire cases sharing an arrange-act scaffold; extracting would obscure \
    # per-case intent"
    def test_revoke_wrong_dimension_fails_closed(self):
        known = _issuer_and_readers("api")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="MiB"),
        )
        result = elaborate_secret(spec, known)
        assert result.danger_err is StrataError.UnitMismatch

    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    def test_auto_generated_readers_claim(self):
        known = _issuer_and_readers("api", "worker")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api", "worker"),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        assert len(expansion.claims) == 1
        claim = expansion.claims[0]
        assert claim.id == "db_cred__readers"


class TestAgePropagationReuse:
    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    def test_lifetime_joins_existing_age_bound_claim(self):
        """A credential's TTL desugars to the same AGE bound T-0065 already checks."""
        known = _issuer_and_readers("api")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=2.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        model = KernelModel(
            nodes=(*known.values(), expansion.node),
            flows=expansion.flows,
            claims=(
                Claim(
                    id="lifetime_ok",
                    body=BoundClaim(
                        metric=Metric.AGE,
                        target="db_cred",
                        limit=Quantity(value=3.0, unit="h"),
                    ),
                ),
                Claim(
                    id="lifetime_too_tight",
                    body=BoundClaim(
                        metric=Metric.AGE,
                        target="db_cred",
                        limit=Quantity(value=1.0, unit="h"),
                    ),
                ),
            ),
        )
        results = {r.claim_id: r for r in evaluate_claims(model).danger_ok}
        assert results["lifetime_ok"].verdict == Verdict.PROVED
        assert results["lifetime_too_tight"].verdict == Verdict.REFUTED


class TestReadersExactSetClosure:
    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_readers_claim_proved_on_exact_match(self):
        known = _issuer_and_readers("api", "worker")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api", "worker"),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        model = KernelModel(
            nodes=(*known.values(), expansion.node),
            flows=expansion.flows,
            claims=expansion.claims,
        )
        result = evaluate_claims(model).danger_ok[0]
        assert result.verdict == Verdict.PROVED
        assert result.quantifier == Quantifier.FORALL

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_readers_claim_refutes_on_extra_reader(self):
        """A downstream flow forwarding the secret past its declared audience refutes."""
        known = _issuer_and_readers("api", "worker", "leaky")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        forward_leak = Flow(
            id="api__forward_leak", src="api", dst="leaky", label="Secret"
        )
        model = KernelModel(
            nodes=(*known.values(), expansion.node),
            flows=(*expansion.flows, forward_leak),
            claims=expansion.claims,
        )
        result = evaluate_claims(model).danger_ok[0]
        assert result.verdict == Verdict.REFUTED
        assert "leaky" in result.detail

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_readers_claim_refutes_on_missing_reader(self):
        """A declared audience member the flow graph never actually reaches refutes."""
        known = _issuer_and_readers("api", "unreached")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api", "unreached"),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        # Drop the "reads" flow to "unreached" to simulate a declared-but-
        # unreachable audience member (deny by default: the mismatch must
        # be caught, not silently ignored).
        flows = tuple(f for f in expansion.flows if f.id != "db_cred__reads_unreached")
        model = KernelModel(
            nodes=(*known.values(), expansion.node),
            flows=flows,
            claims=expansion.claims,
        )
        result = evaluate_claims(model).danger_ok[0]
        assert result.verdict == Verdict.REFUTED
        assert "unreached" in result.detail

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_readers_claim_refutes_across_a_declassify_boundary(self):
        """readers() uses through_barriers=True deliberately: a forward past
        a DECLASSIFY boundary still counts as a reader of the secret, so an
        un-declared downstream node still refutes even though the boundary
        would stop a plain (through_barriers=False) taint closure. Pins the
        `_eval_set_equality` docstring's claim that it reuses `reach`'s own
        barrier-respecting traversal rather than a stricter one.
        """
        known = _issuer_and_readers("api", "public_dashboard")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        declassify_forward = Flow(
            id="api__declassify_forward",
            src="api",
            dst="public_dashboard",
            label="Secret",
        )
        declassify = Boundary(
            id="b1",
            flow_id="api__declassify_forward",
            direction=BoundaryDirection.DECLASSIFY,
            from_level="trusted",
            to_level="public",
        )
        model = KernelModel(
            nodes=(*known.values(), expansion.node),
            flows=(*expansion.flows, declassify_forward),
            boundaries=(declassify,),
            claims=expansion.claims,
        )
        result = evaluate_claims(model).danger_ok[0]
        assert result.verdict == Verdict.REFUTED
        assert "public_dashboard" in result.detail


class TestSecretLabelViolations:
    """Secret-in-logs/repo/artifact reuse the existing clearance-violation
    machinery (`_facts.py::_structural_diagnostics`) -- no bespoke secret
    check exists, matching the ticket's "extend, don't fork" requirement.
    """

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_secret_resting_at_public_clearance_node_is_flagged(self):
        log_sink = Node(id="log_sink", trust="trusted", clearance="Public")
        vault = Node(id="vault", trust="trusted", clearance="Secret")
        leak = Flow(id="leak_to_logs", src="vault", dst="log_sink", label="Secret")
        model = KernelModel(nodes=(vault, log_sink), flows=(leak,))
        facts = build_facts(model).danger_ok
        assert any(
            "leak_to_logs" in d and "exceeds clearance" in d for d in facts.diagnostics
        )

    # frob:tests src/frob/strata/_facts.py::build_facts kind="unit"
    def test_secret_resting_at_secret_clearance_node_is_not_flagged(self):
        vault = Node(id="vault", trust="trusted", clearance="Secret")
        other_vault = Node(id="other_vault", trust="trusted", clearance="Secret")
        ok_flow = Flow(id="rotate", src="vault", dst="other_vault", label="Secret")
        model = KernelModel(nodes=(vault, other_vault), flows=(ok_flow,))
        facts = build_facts(model).danger_ok
        assert not any("rotate" in d for d in facts.diagnostics)


class TestRevocationReachability:
    # frob:tests src/frob/strata/_secrets.py::elaborate_secret kind="unit"
    def test_revocation_edge_is_a_real_reach_claim_target(self):
        """The mandatory revocation edge is a genuine path a `reach` claim can find."""
        known = _issuer_and_readers("api")
        spec = SecretSpec(
            id="db_cred",
            issued_by="vault",
            audience=("api",),
            lifetime=Quantity(value=1.0, unit="h"),
            revoke=Quantity(value=5.0, unit="min"),
        )
        expansion = elaborate_secret(spec, known).danger_ok
        model = KernelModel(
            nodes=(*known.values(), expansion.node),
            flows=expansion.flows,
            claims=(
                Claim(id="revocation_exists", body=Reach(src="vault", dst="db_cred")),
            ),
        )
        result = evaluate_claims(model).danger_ok[0]
        assert result.verdict == Verdict.PROVED
