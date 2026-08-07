---
id: T-0138
title: strata claim ids cannot carry ':' or '-' -- discharge claims unauthorable from
  .strata source
state: done
kind: bug
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- strata-core/src/**
- src/frob/strata/**
- design/litmus/**
- tests/**
- docs/strata/surface.md
- docs/strata/threat.md
- docs/commands/sys.md
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/strata/test_litmus_audit_hardened.py::TestAuditHardenedGolden::test_string_quoted_claim_ids_round_trip
- tests/unit/strata/test_litmus_audit_hardened.py::TestAuditHardenedGolden::test_proves_clean_in_security_and_quality
- tests/unit/strata/test_litmus_audit_vuln.py::TestAuditVulnGolden::test_may_sql_parses_and_elaborates
- tests/unit/strata/test_litmus_audit_vuln.py::TestAuditVulnGolden::test_fires_undischarged_in_security_and_quality
- strata-core/src/parse/mod.rs::tests::parses_string_quoted_claim_id
- strata-core/src/parse/mod.rs::tests::parses_string_quoted_claim_id_on_assume
- strata-core/src/parse/mod.rs::tests::bare_ident_claim_id_still_parses
- strata-core/src/parse/mod.rs::tests::error_unterminated_string_claim_id
- strata-core/src/parse/mod.rs::tests::error_malformed_claim_id_neither_ident_nor_string
- strata-core/src/parse/mod.rs::tests::parses_string_quoted_claim_id
- strata-core/src/parse/mod.rs::tests::parses_string_quoted_claim_id_on_assume
- strata-core/src/parse/mod.rs::tests::bare_ident_claim_id_still_parses
- strata-core/src/parse/mod.rs::tests::error_unterminated_string_claim_id
- strata-core/src/parse/mod.rs::tests::error_malformed_claim_id_neither_ident_nor_string
designated_repro_test: null
threat: null
component: null
---
T-0132 precedent: STRING-quoted values via TokKind::Str. Extend parse_claim (strata-core/src/parse.rs) to accept a string-quoted claim id (assert "weakness:CWE-79:web" noflow(...)) alongside the bare-IDENT form -- quoted form only in the claim-id position, no grammar loosening elsewhere. Wire through _ast/_elaborate if the claim id passes through them.

Tests: rust tests (quoted id round-trips; bare id still works; malformed/unterminated fails with line/col); python: author a surface-level discharge claim in a litmus-style fixture and verify check_discharge_completeness accepts it end-to-end (T-0115 hardened-twin lives in .strata -- add design/litmus/audit_hardened.strata with the discharge claim and a test that frob sys audit PROVES it via the real parse path, complementing audit_vuln.strata).

Every existing litmus golden byte-identical.