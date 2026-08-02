"""Unit tests for the strata surface parser (docs/strata/surface.md#parser)."""

# frob:waive OPAQUE001 reason="T-1038: sys.modules replacement below fakes an import \
# target for one test's own fixture module, standard unittest.mock/sys.modules test \
# isolation -- deliberate test infrastructure, not an evasion risk"

from __future__ import annotations

import sys

import pytest

from frob.strata import Module, StrataError, parse_module


class TestParseModule:
    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_bare_module(self):
        result = parse_module("module payments")
        assert result.is_ok
        module = result.danger_ok
        assert isinstance(module, Module)
        assert module.name == "payments"
        assert module.nodes == ()

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_node_with_all_properties(self):
        text = """
        module m
        node api : trusted abstract {
            clearance Secret;
            attr idempotent;
            attr region=us;
            residence us_east;
            capacity 100 req/s replicas 1..8;
        }
        """
        module = parse_module(text).danger_ok
        node = module.nodes[0]
        assert node.id == "api"
        assert node.trust == "trusted"
        assert node.is_abstract is True
        assert node.clearance == "Secret"
        assert node.attrs == ("idempotent", "region=us")
        assert node.residence == "us_east"
        assert node.capacity is not None
        assert node.capacity.rate.value == 100
        assert node.capacity.rate.unit == "req/s"
        assert node.capacity.replicas_min == 1
        assert node.capacity.replicas_max == 8

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_node_code_globs_and_may_capabilities(self):
        # T-0132: `code=<glob>` / `may <capability>` surface grammar,
        # STRING-quoted since globs/capabilities carry `/`, `*`, `.`, `:`.
        text = """
        module m
        node api : trusted {
            code "src/frob/**" "tests/frob/**";
            may "net.out:stripe.com";
            may "fs.read:/etc/tls";
        }
        """
        module = parse_module(text).danger_ok
        node = module.nodes[0]
        assert node.code == ("src/frob/**", "tests/frob/**")
        assert node.may == ("net.out:stripe.com", "fs.read:/etc/tls")

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_node_without_code_or_may_defaults_empty(self):
        # T-0132: pre-existing sources without code/may statements parse
        # identically to before -- both fields default to an empty tuple.
        module = parse_module("module m\nnode api : trusted").danger_ok
        node = module.nodes[0]
        assert node.code == ()
        assert node.may == ()

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_may_bare_ident_is_parse_failed(self):
        # T-0132: capability atoms must be STRING-quoted, not IDENT.
        text = """
        module m
        node api : trusted {
            may net.out;
        }
        """
        result = parse_module(text)
        assert result.is_err
        assert result.danger_err is StrataError.ParseFailed

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_may_via_scopes_a_grant_to_sub_globs(self):
        # T-1440: `may ATOM via GLOB[, GLOB...]` -- one or more comma-
        # separated STRING globs scope this grant below the node's own
        # `code` binding; the flat `may` tuple is unchanged for kind-only
        # readers, `may_grants` carries the (atom, via) pairing.
        text = """
        module m
        node api : trusted {
            code "src/app/**";
            may "net.out" via "src/app/net.py", "src/app/client.py";
            may "fs.write";
        }
        """
        module = parse_module(text).danger_ok
        node = module.nodes[0]
        assert node.may == ("net.out", "fs.write")
        assert len(node.may_grants) == 2
        assert node.may_grants[0].atom == "net.out"
        assert node.may_grants[0].via == ("src/app/net.py", "src/app/client.py")
        # a via-less `may` still parses -- `via` defaults to `()`, the
        # pre-T-1440 whole-node meaning kept for migration.
        assert node.may_grants[1].atom == "fs.write"
        assert node.may_grants[1].via == ()

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_may_via_also_parses_on_store(self):
        # T-1440: `store` has its own `may` clause (grammar_infra.rs,
        # T-0166); `via` must round-trip there too, not just on `node`.
        text = """
        module m
        store db : trusted {
            code "src/db/**";
            may "fs.write" via "src/db/writer.py";
        }
        """
        module = parse_module(text).danger_ok
        store = module.stores[0]
        assert store.may == ("fs.write",)
        assert len(store.may_grants) == 1
        assert store.may_grants[0].atom == "fs.write"
        assert store.may_grants[0].via == ("src/db/writer.py",)

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_flow_with_all_properties_and_units(self):
        text = """
        module m
        flow f1 : a -> b {
            label Pii;
            age 250 ms;
            rate 5 req/s;
            size 4 KiB;
            attr delivery=at_least_once;
            transport tls;
        }
        """
        module = parse_module(text).danger_ok
        flow = module.flows[0]
        assert flow.src == "a"
        assert flow.dst == "b"
        assert flow.label == "Pii"
        assert flow.age is not None and flow.age.value == 250 and flow.age.unit == "ms"
        assert (
            flow.rate is not None and flow.rate.value == 5 and flow.rate.unit == "req/s"
        )
        assert (
            flow.size is not None and flow.size.value == 4 and flow.size.unit == "KiB"
        )
        assert flow.attrs == ("delivery=at_least_once",)
        assert flow.transport == ("tls",)

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_percent_unit_and_bound_claim(self):
        text = "module m\nassert c1 bound utilization api <= 80 %"
        module = parse_module(text).danger_ok
        claim = module.claims[0]
        assert claim.kind == "bound"
        assert claim.metric == "utilization"
        assert claim.target == "api"
        assert claim.limit is not None
        assert claim.limit.value == 80
        assert claim.limit.unit == "%"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_boundary(self):
        text = (
            "module m\n"
            'boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified"'
        )
        module = parse_module(text).danger_ok
        boundary = module.boundaries[0]
        assert boundary.kind == "endorse"
        assert boundary.flow_id == "f1"
        assert boundary.from_level == "foreign"
        assert boundary.to_level == "authenticated"
        assert boundary.predicate == "jwt_verified"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_assert_noflow_and_reach(self):
        text = "module m\nassert c1 noflow evil -> api\nassert c2 reach audit -> log"
        module = parse_module(text).danger_ok
        assert module.claims[0].kind == "noflow"
        assert module.claims[0].src == "evil"
        assert module.claims[0].dst == "api"
        assert module.claims[1].kind == "reach"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parses_assume_with_owner_and_review(self):
        text = 'module m\nassume c1 noflow evil -> api owner alice review "2026-08-01"'
        claim = parse_module(text).danger_ok.claims[0]
        assert claim.assumed is True
        assert claim.owner == "alice"
        assert claim.review == "2026-08-01"

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_module_missing_is_parse_failed(self):
        result = parse_module("node a : trusted")
        assert result.is_err
        assert result.danger_err is StrataError.ParseFailed

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_unknown_keyword_is_parse_failed(self):
        result = parse_module("module m\nbogus x")
        assert result.is_err
        assert result.danger_err is StrataError.ParseFailed

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_duplicate_module_is_parse_failed(self):
        result = parse_module("module a\nmodule b")
        assert result.is_err
        assert result.danger_err is StrataError.ParseFailed

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_round_trip_small_design(self):
        text = """
        module payments
        node api : trusted { clearance Pii; capacity 100 req/s replicas 1..8; }
        node evil : foreign
        flow f1 : evil -> api { label Pii; rate 5 req/s; transport tls; }
        boundary b1 endorse f1 : foreign -> authenticated when "jwt_verified"
        assert c1 noflow evil -> api
        assume c2 bound age api <= 30 s owner alice review "2026-09-01"
        """
        module = parse_module(text).danger_ok
        assert module.name == "payments"
        assert len(module.nodes) == 2
        assert len(module.flows) == 1
        assert len(module.boundaries) == 1
        assert len(module.claims) == 2


class TestParseModuleNativeExtensionUnavailable:
    """T-0134: a standalone tool install has no `strata_core` extension.

    Monkeypatches the module-level `strata_core` binding to `None` -- the
    same state a bare `uv tool install frob` leaves it in -- and checks
    `parse_module` degrades to a typed `Err` instead of crashing with an
    unhandled `ImportError`/`AttributeError`, matching the T-0133 pattern
    for `frob.lang._walk_strata`.
    """

    @pytest.fixture(autouse=True)
    def _no_native_parser(self, monkeypatch: pytest.MonkeyPatch) -> None:
        parse_mod = sys.modules["frob.strata._parse"]
        monkeypatch.setattr(parse_mod, "strata_core", None)

    # frob:tests src/frob/strata/_parse.py::parse_module kind="unit"
    def test_parse_module_returns_native_extension_unavailable(self):
        result = parse_module("module m")
        assert result.is_err
        assert result.danger_err is StrataError.NativeExtensionUnavailable
