"""Unit tests for the L4 policy sublanguage (docs/strata/policy.md)."""

from __future__ import annotations

from frob.strata import (
    AtCallRequire,
    ConfineUse,
    ForbidCall,
    ForbidImport,
    Mediate,
    StrataError,
    compile_policies,
    elaborate,
    find_policy_weakenings,
    parse_module,
)


def _module(text: str):
    return parse_module(text).danger_ok


class TestGrammarRoundTrip:
    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_forbid_call_round_trips(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on component api {
                forbid call eval, exec, importlib.import_module
            }
            """
        )
        rule = module.policies[0].rules[0]
        assert isinstance(rule, ForbidCall)
        assert rule.idents == ("eval", "exec", "importlib.import_module")

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_forbid_import_round_trips(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on component api {
                forbid import ctypes, cffi
            }
            """
        )
        rule = module.policies[0].rules[0]
        assert isinstance(rule, ForbidImport)
        assert rule.idents == ("ctypes", "cffi")

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_confine_use_round_trips(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on component api {
                confine use psycopg to "src/api/db.py"
            }
            """
        )
        rule = module.policies[0].rules[0]
        assert isinstance(rule, ConfineUse)
        assert rule.ident == "psycopg"
        assert rule.home == "src/api/db.py"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_at_call_require_arg_round_trips(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on component api {
                at call subprocess.run require arg timeout
            }
            """
        )
        rule = module.policies[0].rules[0]
        assert isinstance(rule, AtCallRequire)
        assert rule.ident == "subprocess.run"
        assert rule.arg == "timeout"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_mediate_round_trips(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on component api {
                mediate db.write via "db.py::TenantScopedSession"
            }
            """
        )
        rule = module.policies[0].rules[0]
        assert isinstance(rule, Mediate)
        assert rule.ident == "db.write"
        assert rule.mediator == "db.py::TenantScopedSession"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_enables_and_rationale_split_out_of_rules(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on component api {
                forbid call eval;
                enables extraction_soundness;
                rationale "no dynamic dispatch"
            }
            """
        )
        decl = module.policies[0]
        assert len(decl.rules) == 1
        assert decl.enables == ("extraction_soundness",)
        assert decl.rationale == ("no dynamic dispatch",)


class TestScopeResolution:
    # frob:tests src/frob/strata/_policy.py::compile_policies kind="unit"
    def test_component_scope_resolves_to_one_node(self):
        module = _module(
            """
            module m
            node api : trusted
            node db : trusted
            policy P on component api { forbid call eval }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        assert compiled.policies[0].node_ids == ("api",)

    # frob:tests src/frob/strata/_policy.py::compile_policies kind="unit"
    # invariant spec: [INV-030](invariants/INV-030.md)
    def test_trust_scope_resolves_via_lattice(self):
        module = _module(
            """
            module m
            node api : trusted
            node edge : authenticated
            node evil : foreign
            policy P on trust >= authenticated { forbid call eval }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        assert compiled.policies[0].node_ids == ("api", "edge")

    # frob:tests src/frob/strata/_policy.py::compile_policies kind="unit"
    def test_label_scope_resolves_via_lattice(self):
        module = _module(
            """
            module m
            node api : trusted { clearance Pii; }
            node cache : trusted { clearance Internal; }
            policy P on label >= Pii { forbid call eval }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        assert compiled.policies[0].node_ids == ("api",)

    # frob:tests src/frob/strata/_policy.py::compile_policies kind="unit"
    def test_unknown_component_scope_fails_closed(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on component ghost { forbid call eval }
            """
        )
        model = elaborate(module).danger_ok
        result = compile_policies(module, model)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_policy.py::compile_policies kind="unit"
    def test_unknown_trust_level_fails_closed(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on trust >= bogus { forbid call eval }
            """
        )
        model = elaborate(module).danger_ok
        result = compile_policies(module, model)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference

    # frob:tests src/frob/strata/_policy.py::compile_policies kind="unit"
    def test_unknown_label_level_fails_closed(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P on label >= Bogus { forbid call eval }
            """
        )
        model = elaborate(module).danger_ok
        result = compile_policies(module, model)
        assert result.is_err
        assert result.danger_err is StrataError.UnknownReference


class TestRefinementMonotonicity:
    """INV-051 (T-1482): find_policy_weakenings over a parent (broader
    trust/label scope) / child (narrower, contained scope) policy pair."""

    # frob:tests src/frob/strata/_policy.py::find_policy_weakenings kind="unit"
    def test_confine_use_broadened_home_detected(self):
        module = _module(
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                confine use psycopg to "src/api/db.py"
            }
            policy Child on component api {
                confine use psycopg to "src/other/place.py"
            }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        violations = find_policy_weakenings(compiled)
        assert len(violations) == 1
        assert violations[0].parent_id == "Parent"
        assert violations[0].child_id == "Child"
        assert violations[0].rule_kind == "confine_use"

    # frob:tests src/frob/strata/_policy.py::find_policy_weakenings kind="unit"
    def test_at_call_require_dropped_arg_detected(self):
        module = _module(
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                at call subprocess.run require arg timeout
            }
            policy Child on component api {
                at call subprocess.run require arg check
            }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        violations = find_policy_weakenings(compiled)
        assert len(violations) == 1
        assert violations[0].rule_kind == "at_call_require_arg"
        assert "timeout" in violations[0].detail

    # frob:tests src/frob/strata/_policy.py::find_policy_weakenings kind="unit"
    def test_mediate_swapped_mediator_detected(self):
        module = _module(
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                mediate db.write via "db.py::TenantScopedSession"
            }
            policy Child on component api {
                mediate db.write via "db.py::OtherSession"
            }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        violations = find_policy_weakenings(compiled)
        assert len(violations) == 1
        assert violations[0].rule_kind == "mediate"

    # frob:tests src/frob/strata/_policy.py::find_policy_weakenings kind="unit"
    def test_no_finding_when_child_only_strengthens(self):
        module = _module(
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                confine use psycopg to "src/api"
            }
            policy Child on component api {
                confine use psycopg to "src/api/db.py"
            }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        assert find_policy_weakenings(compiled) == ()

    # frob:tests src/frob/strata/_policy.py::find_policy_weakenings kind="unit"
    def test_no_finding_when_child_never_overlaps_parent_scope(self):
        module = _module(
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted {
                confine use psycopg to "src/api/db.py"
            }
            policy Sibling on component api {
                confine use ctypes to "src/api/native.py"
            }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        # Sibling never re-confines "psycopg" at all -- inherited
        # unmodified from Parent, not a weakening; its OWN confine_use
        # targets a different ident ("ctypes") entirely.
        violations = find_policy_weakenings(compiled)
        assert violations == ()

    # frob:tests src/frob/strata/_policy.py::find_policy_weakenings kind="unit"
    def test_forbid_call_never_flagged_even_when_child_narrows(self):
        """forbid call/import are purely additive under union-of-policies
        enforcement (docs/strata/policy.md#compilation) -- a child
        re-declaring forbid_call with a DIFFERENT ident set can never make
        the parent's own prohibitions stop applying, so this is
        deliberately never a finding regardless of what the child lists."""
        module = _module(
            """
            module m
            node api : trusted
            node db : trusted
            policy Parent on trust >= trusted { forbid call eval, exec }
            policy Child on component api { forbid call reflect }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        assert find_policy_weakenings(compiled) == ()


class TestEnablesBookkeeping:
    # frob:tests src/frob/strata/_policy.py::CompiledPolicies.enabling kind="unit"
    def test_enabling_finds_policies_declaring_the_atom(self):
        module = _module(
            """
            module m
            node api : trusted
            policy P1 on component api { enables extraction_soundness }
            policy P2 on component api { enables other_atom }
            """
        )
        model = elaborate(module).danger_ok
        compiled = compile_policies(module, model).danger_ok
        assert compiled.enabling("extraction_soundness") == ("P1",)
        assert compiled.enabling("other_atom") == ("P2",)
        assert compiled.enabling("nothing_declares_this") == ()
