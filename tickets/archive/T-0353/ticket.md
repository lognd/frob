---
id: T-0353
title: disposition frob's own PII010/SEC110 findings -- narrow fingerprint FP signature,
  known-non-secret env allowlist, waive/map residue (T-0207 self-adoption)
state: done
kind: bug
origin: agent
created: '2026-07-20'
priority: medium
parent: null
tier: ticket
sprint: null
scope:
- src/frob/gates/_pii_structural.py
- src/frob/**
- tests/**
- tickets.md
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[fingerprint_scan]
- tests/test_pii_structural_gate.py::TestDriftLock::test_signature_fires[fingerprint_template]
- tests/test_pii_structural_gate.py::TestGateIsGreenOnItself::test_own_module_source_produces_no_self_finding
- tests/test_testing.py::TestCargoEnv::test_env_overlay_restores_prior_values
designated_repro_test: null
acceptance:
- text: PII010's bare 'fingerprint' biometric signature (matches fingerprint_id/cache-fingerprint/git-fingerprint
    far more than biometric data) is narrowed to genuine biometric field names (fingerprint_template/fingerprint_image)
    or dropped, so it no longer false-positives on frob's CVE fingerprint fields;
    the per-signature drift-lock test is updated to match
  evidence: []
- text: SEC110 gains a curated KNOWN-NON-SECRET env-var-name allowlist (DISPLAY, WAYLAND_DISPLAY,
    TERM, NO_COLOR, PATH, HOME, LANG, TZ, CI, XDG_*, PYTEST_CURRENT_TEST, VIRTUAL_ENV,
    PYO3_PYTHON, and frob's own non-secret tooling vars) that does NOT fire -- a precision
    improvement (those names definitionally carry no secret), not a weakening; an
    env read of a NON-allowlisted var still fires
  evidence: []
- text: "after the two precision fixes, every remaining PII010/SEC110 finding on frob's\
    \ OWN codebase is dispositioned with an honest per-site frob:waive reason (e.g.\
    \ deploy/_audit.py 'passwd_added/removed' = /etc/passwd-audit COUNTS not stored\
    \ creds), so frob check .  [FAIL]  1 error  0 warnings\n\n## Errors\n  [config]\
    \ unknown --only stage(s) ['pii_structural']; tools: ['arch', 'bind', 'cycle',\
    \ 'dup', 'exports', 'gates', 'ruff', 'ty']; gates: ['clones', 'coverage', 'decisions',\
    \ 'docanchor', 'doclink', 'drift', 'fuzz', 'invariant', 'perf', 'policy', 'prework',\
    \ 'release', 'scope', 'secrets', 'sys', 'test', 'tickets']\n\n## Tool summary\n\
    \  FAIL  config                  unknown --only stage(s): ['pii_structural'] on\
    \ main is 0 warnings"
  evidence: []
threat: null
component: null
---
T-0207 landed the structural PII/secrets gate (PII010 field-name + SEC110 env-access). Adopting it on frob's OWN code surfaced 17 findings (0 errors): 1 clear false positive (strata/_cve_fingerprint.py 'fingerprint_id' matched as biometric), ~14 legitimate-but-non-secret env reads (clipboard DISPLAY/WAYLAND, testing PYO3_PYTHON, logging color env, vet CVE-mirror path, test monkeypatched env), and 3 deploy password-audit metadata fields. Disposition them the SMART way per the anti-evasion 'make the check precise, don't mass-waive' principle: (1) narrow the over-broad fingerprint signature; (2) add the known-non-secret env allowlist; (3) honest per-site waivers for the true residue. Toward the zero-warnings goal. See docs/design/secrets-pii-corpus.md for the signature source of truth.