---
id: T-0369
title: 'exports: demote true package-internal helpers flagged by frob-exports (needs
  tests/ touch)'
state: done
kind: bug
origin: human
created: '2026-07-20'
priority: medium
parent: T-0204
tier: ticket
sprint: null
scope:
- src/frob/**
- tests/**
- docs/**
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_dup_cache.py::TestConnectionReuse::test_close_all_drops_cached_connections
- tests/unit/test_dup_core.py::TestR3CanonicalHash::test_identical_token_streams_hash_equal
- tests/test_pii_structural_gate.py::TestGateIsGreenOnItself::test_own_module_source_produces_no_self_finding
- tests/test_secrets_gate.py::TestRedact::test_never_returns_the_token
- tests/test_graph.py::TestDigests::test_reformat_identical_digests
- tests/unit/test_lang_primitives.py::test_span_of_is_one_based_inclusive
- tests/unit/strata/test_host.py::TestHostAttrs::test_desugars
- tests/unit/strata/test_waive.py::TestSplitWaiverRule::test_bare_rule_has_no_sub_target
- tests/unit/test_ticket_store.py::TestSerializeAndParse::test_round_trip
- tests/test_vet.py::TestVerdictCache::test_store_and_retrieve_latest
- tests/test_capability_registry.py::TestValidateRegistryKinds::test_known_kinds_pass
designated_repro_test: null
threat: null
component: null
---
T-0362 follow-up: 74 src symbols remain un-exported after T-0362 (dup._core.*, gates._pii_structural.*, gates._secrets.redact, gates.decisions.{Decision,DecisionStatus}, gates.invariants.Criticality, graph.digest.{digest_body,digest_doc,digest_sig}, lang._common.{collapse_ws,find_enclosing_symbol,find_following_symbol,leading_doc_comment,leaf_tokens,span_of,strip_comment_delims}, logging.filter.BelowLevelFilter, logging.formatter.FrobFormatter (appears fully dead -- also worth a dead-code check), strata._ast.*, strata._host.host_attrs, strata._krb.krb_attrs, strata._waive.*, tickets._store.{parse_ticket_file,serialize_ticket,store_mode}, vet._allow.load_vet_config, vet._cache.*, vet._capability.{decode_to_exec_signal,scan_directory_capabilities,scan_directory_fingerprints,scan_file_fingerprints,scan_file_operations}, vet._capability_registry.{DangerousOperation,MatrixCell,MatrixExcuse,unexcused_empty_cells,validate_registry_kinds}, vet._ecosystem.*, vet._lifecycle.scan_lifecycle_scripts, vet._lockfile.*, vet._models.HookAction, vet._obfuscation.*, vet._osv.*, vet._registry.*, vet._source.*, vet._typosquat.*. Each is genuinely package-internal (0-1 intra-package consumer files, never imported outside its own package) but is ALSO imported directly by name in one or more tests/ files (e.g. from frob.vet._typosquat import find_typosquat), so demoting with a leading underscore is out of T-0362's src-only scope: it requires updating those test imports too. Plan: rename each symbol to _name in its defining module, update the sole intra-package consumer, and update the matching tests/ import. frob.perf._harness.main and frob.__main__.main were intentionally left un-exported with an inline rationale comment (script/console-script entrypoints, not package-import API) -- not part of this follow-up.