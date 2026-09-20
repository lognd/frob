---
id: T-0540
title: 'PII012 keyword-sweep residual burndown: 102 findings, token/secret homonyms
  in app code'
state: done
kind: bug
origin: agent
created: '2026-07-21'
priority: low
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/gates/_pii_structural.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: 'T-4770: preserve homonym list trimmed from _keywords.py'
  actor: logan
  at: '2026-09-19'
  old_length: 2714
  new_length: 3872
evidence:
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_identifier_keyword_fires_at_suggestion_severity
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_function_parameter_keyword_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_comment_keyword_fires
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_unrelated_identifier_does_not_fire
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_tokenizer_identifier_does_not_falsely_match_token
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_data_structure_field_not_double_reported
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_frob_directive_comment_does_not_fire
- tests/test_pii_structural_gate.py::TestKeywordSweep::test_ordinary_comment_mentioning_secret_still_fires
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
## Description

T-0539 calibrated PII011/PII012 down from ~336 raw findings to 116 (103
unwaived), via: (1) reusing `is_self_pattern_path`'s root-identity-gated
discriminator (T-0253) to exclude detector-definition/corpus/fixture files
(`_secrets.py`, `_cve_fingerprint.py` + their dedicated tests) from the
PII scan; (2) an RFC 2606 reserved-test-domain exclusion for PII011
(killed 57/66 email-shape findings); (3) `frob:secret-fake` markers on the
9 remaining non-reserved-domain test git-identity fixtures (PII011 -> 0);
(4) excluding `# frob:*` directive comments from the PII012 comment sweep
(the `frob:secret-fake` marker itself contains "secret").

Residual after all of the above: 102 unwaived PII012 findings (WARN/
suggestion severity, non-blocking) across ~50 ordinary application files,
dominated by two overloaded single-word keywords that mean something
else entirely in most of these sites:

- `token` (67 hits): overwhelmingly a LEXER/PARSE token (AST/tree-sitter
  token, hash/dedup token, git-ref token), not an auth token. Top files:
  `src/frob/gates/_refs.py` (11), `src/frob/dup/_pipeline.py` (7),
  `src/frob/graph/dsl.py` (3), `src/frob/perf/_rules.py` (3),
  `src/frob/dup/_exhaustiveness.py` (2), `src/frob/graph/_models.py` (2),
  `src/frob/lang/_walk_rust.py` (2), plus ~25 files with 1 hit each.
- `secret` (21 hits): overwhelmingly the CONCEPT of a declared std.secrets
  node (this codebase's own strata secrets-declaration feature), not a
  literal secret value. Top files: `src/frob/strata/_threat.py` (6),
  `src/frob/deploy/_conform.py` (5), `src/frob/gates/__init__.py` (5),
  `src/frob/vet/_hook.py` (4).
- `passwd` (6), `diagnosis` (5, frob's own `frob doctor` diagnosis
  feature name), `fingerprint_scan` (1), `email` (1), `password` (1):
  small residuals, plausibly real per-site waives.

## Plan

1. Investigate whether `token`/`secret` warrant a narrower keyword shape
   in `FIELD_SIGNATURES` (T-0353 precedent: `fingerprint` was narrowed to
   `fingerprint_scan`/`fingerprint_template` for the same over-broad-
   homonym reason) WITHOUT weakening PII010's deny-by-default value for a
   field genuinely named `token`/`secret` -- this needs care since
   `FIELD_SIGNATURES` is shared across PII010/PII011/PII012.
2. For sites where no narrower keyword shape is safe, disposition each of
   the ~50 files' findings individually: `frob:waive PII012 reason="..."`
   with a specific, honest per-site reason (this rule is WARN/advisory by
   design -- module docstring's "no hard fail on names alone" -- so a
   waive here is not weakening a real gate, just quieting a confirmed
   non-finding).
3. Target: 0 unwaived PII012, or a further-narrowed honest remainder.

```


T-4770 follow-up (condensed from _PII012_REVIEWED_NON_PII's docstring in
src/frob/gates/_pii_structural/_keywords.py, trimmed for DOCARCH002's
12-line cap): "token" covers frob.dup's duplicate-code tokenizer,
frob.lang's tree-sitter walkers, frob.gates._refs's symref tokens,
frob.map's LLM context-length estimate. "secret" covers
frob.graph.EdgeKind.SECRET, a strata Secret-clearance node id, or
elaboration/threat-model prose describing that construct. The homonyms:
passwd/passwd_added/passwd_removed (raw /etc/passwd text captured for
deploy-state diffing, already PII010-waived at the same fields per
T-0539's precedent -- no real password ever lives in /etc/passwd);
run_diagnosis/test_run_diagnosis_* (frob doctor's self-diagnostic
feature name, docs/guides/install.md); email (a docstring's tag-format
EXAMPLE string "identifier.email", not a data-structure field);
_cve_fingerprint_scan (a MODULE NAME mentioned in a prose comment, not a
biometric scan); password (a CWE catalog entry TITLE string,
strata/_threat.py's WeaknessEntry table). Each site was individually
read at its call site before being added here, never a blanket keyword
mute.