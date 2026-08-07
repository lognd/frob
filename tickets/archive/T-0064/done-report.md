## Done report

Changed:
- strata-core/src/parse/mod.rs::Parser::parse_store
- strata-core/src/parse/mod.rs::Parser::parse_cache
- strata-core/src/parse/mod.rs::Parser::parse_queue
- strata-core/src/parse/mod.rs::Parser::parse_cdn
- strata-core/src/parse/mod.rs::Parser::parse_balancer
- strata-core/src/parse/mod.rs::Parser::parse_percent
- strata-core/src/parse/mod.rs::ModuleAst (stores/caches/queues/cdns/balancers fields)
- src/frob/strata/_ast.py::StoreDecl
- src/frob/strata/_ast.py::CacheDecl
- src/frob/strata/_ast.py::QueueDecl
- src/frob/strata/_ast.py::CdnDecl
- src/frob/strata/_ast.py::BalancerDecl
- src/frob/strata/_ast.py::Module (stores/caches/queues/cdns/balancers fields)
- src/frob/strata/_infra.py::elaborate_infra (new module)
- src/frob/strata/_infra.py::InfraExpansion (new module)
- src/frob/strata/_errors.py::StrataError (MissingBound, MissingInvalidation, MutableUnbounded)
- src/frob/strata/_elaborate.py::elaborate (calls elaborate_infra after std.trust mapping)
- src/frob/strata/_elaborate.py::_validate_references (bound-claim targets now include infra decl ids)
- src/frob/strata/__init__.py (exports for the above)
- docs/strata/surface.md (## std.infra section: desugar table, age-collapse,
  mandatory invalidation, immutable-TTL pairing, CDN declassification,
  queue delivery propagation, sticky-balancer contradiction, and the
  documented queue/balancer trust-default deviation)

Evidence:
- cargo test (strata-core), 41/41 green, including new:
  parse::tests::parses_store_with_all_properties,
  parse::tests::parses_bare_store, parse::tests::error_unknown_store_property,
  parse::tests::parses_cache_with_all_properties, parse::tests::parses_cache_ttl,
  parse::tests::error_unknown_cache_property,
  parse::tests::parses_queue_with_all_properties,
  parse::tests::error_unknown_queue_property,
  parse::tests::parses_cdn_with_all_properties,
  parse::tests::parses_cdn_unlimited_staleness,
  parse::tests::error_unknown_cdn_property,
  parse::tests::parses_balancer_with_all_properties,
  parse::tests::parses_bare_balancer,
  parse::tests::error_unknown_balancer_property
- tests/unit/strata/test_infra.py::TestStoreDesugar::test_store_becomes_node_with_markers
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_node_and_fill_flow
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_ttl_and_staleness_must_agree
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_ttl_and_staleness_agreeing_is_ok
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_with_no_bound_is_err
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_without_invalidation_is_err
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_cache_no_inbound_writes_needs_no_invalidation
- tests/unit/strata/test_infra.py::TestCacheDesugar::test_invalidate_on_wrong_dst_is_err
- tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_node_attrs
- tests/unit/strata/test_infra.py::TestQueueDesugar::test_queue_delivery_propagates_to_outbound_flows_and_fires_diagnostic
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_node_and_fill_flow
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_unlimited_on_mutable_is_err
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_unlimited_on_immutable_is_ok
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_missing_provider_is_err
- tests/unit/strata/test_infra.py::TestCdnDesugar::test_cdn_tls_terminates_adds_declassify_boundary
- tests/unit/strata/test_infra.py::TestBalancerDesugar::test_balancer_node_attrs
- tests/unit/strata/test_infra.py::TestBalancerDesugar::test_sticky_balancer_stateless_downstream_is_diagnostic
- tests/unit/strata/test_infra.py::TestEndToEnd::test_cache_staleness_refutes_age_bound_claim
- `uv run pytest tests/unit/strata -q` -- 110 tests green (92 pre-existing + 18 new in test_infra.py)
- `uv run ruff format --check` / `uv run ruff check` clean on all changed files
- `uv run ty check src/` clean
- `cargo fmt -- --check` and `cargo clippy --all-targets -- -D warnings` clean (strata-core)

Filed: T-0093 (strata grammar: explicit trust clause for queue/balancer --
the grammar as specified for this ticket gives queue/balancer no TRUST
clause; `_infra.py` defaults both to `"trusted"`, documented as a
deliberate deviation in docs/strata/surface.md#std-infra rather than left
silent).

Gates: `frob ticket sweep T-0064` recorded (dup=55, xref=8, pre-existing
repo-wide noise unrelated to this diff); `frob check --ticket T-0064` exit
0; plain `frob check` exit 0; `frob graph build` clean (18 describes
anchors resolved in docs/strata/surface.md).

Deviations: (1) queue/balancer trust defaults to `"trusted"` -- see Filed,
above; the ticket's own grammar sketch omits a TRUST clause for these two
constructs, so a default was unavoidable, and it is documented rather than
silent. (2) `MissingBound`'s docstring was worded to cover both the cache
ttl/staleness case and the cdn missing-provider-trust case, since the
ticket specifies exactly three new error members and a fourth was not
warranted for one additional missing-declaration site with the same
deny-by-default shape.
