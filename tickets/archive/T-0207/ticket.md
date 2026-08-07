---
id: T-0207
title: 'structural PII/secrets detection: waivable checks over data structures, schemas,
  and env access'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/**
- src/frob/strata/**
- src/frob/vet/**
- src/frob/lang/**
- design/frob.strata
- tests/**
- docs/**
- frob.toml
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_pii_structural_gate.py::TestFieldNames::test_password_field_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_pydantic_email_type_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_typeddict_ssn_field_fires
- tests/test_pii_structural_gate.py::TestFieldNames::test_plain_class_not_scanned
- tests/test_pii_structural_gate.py::TestFieldNames::test_unrelated_field_name_does_not_fire
- tests/test_pii_structural_gate.py::TestFieldNames::test_tokenizer_field_does_not_falsely_match_token
- tests/test_pii_structural_gate.py::TestEnvAccess::test_os_getenv_fires
- tests/test_pii_structural_gate.py::TestEnvAccess::test_os_environ_subscript_fires
- tests/test_pii_structural_gate.py::TestEnvAccess::test_os_environ_get_fires
- tests/test_pii_structural_gate.py::TestEnvAccess::test_direct_import_getenv_fires
- tests/test_pii_structural_gate.py::TestEnvAccess::test_unrelated_call_does_not_fire
- tests/test_pii_structural_gate.py::TestSelfMatchExclusion::test_own_file_not_scanned
- tests/test_pii_structural_gate.py::TestGateIsGreenOnItself::test_own_module_source_produces_no_self_finding
designated_repro_test: null
threat: info-disclosure
component: null
---
User mandate 2026-07-18 ('if it passes, it's safe'): extend T-0154 (PII flow proofs) and T-0157 (secrets token scan) with STRUCTURAL detection over data surfaces, every rule waivable via frob:waive with a written reason so zero-unwaived means every PII/secret surface is either declared or consciously waived. Detector families: (1) DATA-STRUCTURE FIELDS: pydantic/dataclass/TypedDict/attrs field names and types across supported languages (name keyword table: email, phone, ssn, dob, address, ip, password, token, api_key, secret, salt, card/pan/cvv...; type-based: EmailStr, SecretStr, and TS/rust equivalents) -- a detected PII-shaped field on a node without a matching T-0154 PII category declaration (or waiver) fires; declared-but-never-observed goes stale like SYS101. (2) DATABASE SCHEMA: CREATE TABLE / column DDL in migrations (alembic, raw SQL) and ORM models (sqlalchemy columns) scanned with the same keyword+type tables -- schema headers are the highest-value PII surface. (3) ENV/SECRET SOURCES: os.environ[...]/os.getenv/load_dotenv() call sites (and process.env, std::env::var) are secret-source observations that must map to declared strata secret nodes (T-0082 std.secrets) or be waived -- an unmapped env read fires. (4) EMAIL-SHAPE VALUES: detect email-shaped string literals in code/fixtures WITHOUT naive regex (user explicit: regex is bad for email matching) -- use a structural parse (local@domain.tld via a real address parser, e.g. email.utils/parseaddr semantics or the WHATWG algorithm) with the T-0157 fake-marker escape (frob:secret fake / placeholder shapes stay writable). (5) KEYWORD SWEEP: identifier/comment keyword hits at suggestion severity only (no hard fail on names alone). DISCIPLINE (non-negotiable, per registry precedent): single-source keyword/type registry (no duplication between detectors); litmus fire+discharge fixtures per detector (T-0145 style); per-entry parametrized drift-lock (T-0182 style) so a registry keyword without a firing fixture fails; exhaustiveness matrix (detector x language) with written exclusions for unpatterned cells (T-0158 style); self-match exclusion for the registry file itself designed in from day one (T-0201 lesson -- the keyword table must not detect itself); wire into frob check as a new gate family (PII0xx/SEC1xx) default-on at WARN for adoption, severity dial in frob.toml; sys audit gains the joined view (structural observations vs declared PII/secret model). Split into child tickets per detector family at plan time if needed; this is the umbrella.