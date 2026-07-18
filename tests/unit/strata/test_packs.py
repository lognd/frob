"""Unit tests for std.policy.analyzable and the enables cascade.

docs/strata/policy.md#packs, docs/strata/evidence.md#the-enables-cascade.
"""

from __future__ import annotations

import logging

from frob.strata import (
    ANALYZABLE_POLICY_ID,
    ForbidCall,
    Verdict,
    compile_policies,
    elaborate,
    evaluate_claims,
    parse_module,
    require_analyzable,
)


def _module(text: str):
    return parse_module(text).danger_ok


class TestAutoInjection:
    # frob:tests src/frob/strata/_packs.py::require_analyzable kind="unit"
    def test_trusted_component_without_pack_gets_it_injected(self, caplog):
        module = _module(
            """
            module m
            node api : trusted
            """
        )
        with caplog.at_level(logging.WARNING):
            elaborated = elaborate(module)
        assert elaborated.is_ok
        assert any(
            "auto-injecting mandatory base pack" in rec.message
            for rec in caplog.records
        )
        # require_analyzable is the explicit seam a caller uses on the
        # surface module before compile_policies -- elaborate() logs the
        # same decision internally but returns a KernelModel, which has
        # no `policies` field (kernel stays vocabulary-free, law 1).
        injected = require_analyzable(module).danger_ok
        assert any(p.id == ANALYZABLE_POLICY_ID for p in injected.policies)

    # frob:tests src/frob/strata/_packs.py::require_analyzable kind="unit"
    def test_no_trusted_component_no_injection_no_warning(self, caplog):
        module = _module(
            """
            module m
            node edge : foreign
            """
        )
        with caplog.at_level(logging.WARNING):
            elaborate(module)
        assert not any(
            "auto-injecting mandatory base pack" in rec.message
            for rec in caplog.records
        )
        injected = require_analyzable(module).danger_ok
        assert injected.policies == ()

    # frob:tests src/frob/strata/_packs.py::require_analyzable kind="unit"
    def test_already_declared_pack_is_not_duplicated(self):
        module = _module(
            f"""
            module m
            node api : trusted
            policy {ANALYZABLE_POLICY_ID} on component api {{ forbid call eval }}
            """
        )
        injected = require_analyzable(module).danger_ok
        matches = [p for p in injected.policies if p.id == ANALYZABLE_POLICY_ID]
        assert len(matches) == 1
        # the user's declared rule set survives untouched (override, not merge)
        rule = matches[0].rules[0]
        assert isinstance(rule, ForbidCall)
        assert rule.idents == ("eval",)


class TestEnablesCascade:
    def _cascade_setup(self):
        module = _module(
            """
            module m
            node evil : foreign
            node api : trusted { capacity 1000 req/s replicas 1..1; }
            assert c1 noflow evil -> api
            assert c2 bound utilization api <= 80 %
            """
        )
        module = require_analyzable(module).danger_ok
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        return model, compiled

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_unwaived_pack_stays_proved(self):
        model, compiled = self._cascade_setup()
        results = evaluate_claims(
            model, compiled_policies=compiled, waived_policies=frozenset()
        ).danger_ok
        noflow = next(r for r in results if r.claim_id == "c1")
        assert noflow.verdict is Verdict.PROVED

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_waived_pack_downgrades_noflow_but_not_bound(self, caplog):
        model, compiled = self._cascade_setup()
        with caplog.at_level(logging.WARNING):
            results = evaluate_claims(
                model,
                compiled_policies=compiled,
                waived_policies=frozenset({ANALYZABLE_POLICY_ID}),
            ).danger_ok
        noflow = next(r for r in results if r.claim_id == "c1")
        bound = next(r for r in results if r.claim_id == "c2")
        assert noflow.verdict is Verdict.ASSUMED
        assert noflow.detail == (
            "soundness dependency extraction_soundness waived via "
            f"{ANALYZABLE_POLICY_ID}"
        )
        assert noflow.quantifier.value == "forall"  # quantifier-preserving downgrade
        assert bound.verdict is Verdict.PROVED
        assert any(
            "downgraded PROVED -> ASSUMED" in rec.message for rec in caplog.records
        )

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_waiving_a_policy_that_enables_nothing_downgrades_nothing(self):
        module = _module(
            """
            module m
            node evil : foreign
            node api : trusted { capacity 1000 req/s replicas 1..1; }
            policy Harmless on component api { forbid call eval }
            assert c1 noflow evil -> api
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        results = evaluate_claims(
            model, compiled_policies=compiled, waived_policies=frozenset({"Harmless"})
        ).danger_ok
        noflow = next(r for r in results if r.claim_id == "c1")
        assert noflow.verdict is Verdict.PROVED

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_waiving_a_nonexistent_policy_id_is_a_logged_no_op(self, caplog):
        model, compiled = self._cascade_setup()
        with caplog.at_level(logging.WARNING):
            results = evaluate_claims(
                model,
                compiled_policies=compiled,
                waived_policies=frozenset({"no-such-policy"}),
            ).danger_ok
        noflow = next(r for r in results if r.claim_id == "c1")
        assert noflow.verdict is Verdict.PROVED
        assert not any(
            "downgraded PROVED -> ASSUMED" in rec.message for rec in caplog.records
        )

    # frob:tests src/frob/strata/_claims.py::evaluate_claims kind="unit"
    def test_end_to_end_parse_elaborate_compile_evaluate(self):
        text = """
        module m
        node evil : foreign
        node api : trusted
        assert c1 noflow evil -> api
        """
        module = parse_module(text).danger_ok
        module = require_analyzable(module).danger_ok
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        assert any(p.id == ANALYZABLE_POLICY_ID for p in compiled.policies)
        results = evaluate_claims(
            model,
            compiled_policies=compiled,
            waived_policies=frozenset({ANALYZABLE_POLICY_ID}),
        ).danger_ok
        assert results[0].verdict is Verdict.ASSUMED
