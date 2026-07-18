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
