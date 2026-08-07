## Done report

Before: `frob check --only pii_structural --json` -- 350 raw diagnostics
(PII012=269, PII011=66, SEC110=11, PII010=4), all 4 PII010 already fully
waived, so unwaived starting point was PII012=269, PII011=66.

Calibration (non-vacuous -- an ordinary keyword hit in application code
still fires):

1. Reused T-0253's `is_self_pattern_path` discriminator (root-identity
   gate + path-suffix match) from `frob.vet._capability`, adding a
   `suffixes` parameter so `frob.gates._pii_structural` can pass its OWN
   suffix list (`_PII_SELF_PATTERN_SUFFIXES`) through the SAME machinery
   rather than re-deriving it. Excludes this gate's own module, the
   sibling secrets/fingerprint detector sources, and those detectors'
   dedicated test/fixture files.
2. RFC 2606 reserved-domain exclusion for PII011
   (`_is_reserved_test_domain_email`): an email literal at
   `example.com`/`.net`/`.org`/`.example` can never resolve to a real
   person -- killed 57 of 66 PII011 findings outright.
3. `frob:secret-fake` markers added to the remaining 9 PII011 sites
   (synthetic git-identity fixtures in 6 test files, none RFC-2606-
   reserved) -- PII011 now 0.
4. `# frob:*` directive comments excluded from the PII012 comment sweep
   (`_FROB_DIRECTIVE_RE`): the `frob:secret-fake` marker itself contains
   the word "secret", which was self-triggering PII012 on the very
   comment meant to discharge PII011.

After: PII011 = 0 (was 66). PII010 = 0 unwaived (was already 0 unwaived,
3 pre-existing waives untouched). PII012 = 102 unwaived (was 269),
dominated by "token" (67, overwhelmingly a lexer/parse token, not an auth
token) and "secret" (21, overwhelmingly this codebase's own
std.secrets-declaration concept) spread across ~50 ordinary application
files, none over 11 hits. SEC110 untouched (out of this ticket's scope;
1 unwaived, 10 pre-existing waives).

Not Filed T-draft-4a78008a (never refiled) for the PII012 residual (exact per-keyword/
per-file counts recorded in its Description) rather than hand-waiving
~50 scattered single-line WARN/advisory findings within this ticket's
budget -- PII012 is deliberately suggestion-severity, never gating, per
its own module docstring ("no hard fail on names alone").

Changed:
- src/frob/gates/_pii_structural.py (`_is_pii_self_pattern_file`,
  `_PII_SELF_PATTERN_SUFFIXES`, `_is_reserved_test_domain_email`,
  `_RFC2606_RESERVED_EMAIL_DOMAINS`, `_FROB_DIRECTIVE_RE`, wired into
  `pii_structural_gate`/`_scan_python_email_values`/
  `_scan_comment_keywords`)
- src/frob/vet/_capability.py (`is_self_pattern_path` gained a
  `suffixes` parameter, default-compatible)
- tests/test_pii_structural_gate.py (TestReservedTestDomainEmails,
  TestKeywordSweep additions, TestGateIsGreenOnItself corpus-file
  parametrization)
- 6 test fixture files: `frob:secret-fake` markers on 9 sites
  (tests/integration/test_gitlog.py, tests/integration/test_interfaces.py,
  tests/system/test_cli_gitlog.py, tests/unit/test_app_runners.py,
  tests/unit/test_app_runners_batch5.py, tests/unit/test_gitlog.py)
- pyproject.toml/.frob-release.json/uv.lock: version 0.58.0 -> 0.59.0
  (REL001, `is_self_pattern_path` public API change)

Evidence: 99/99 tests/test_pii_structural_gate.py pass; recorded node
ids (TestReservedTestDomainEmails, TestKeywordSweep new cases,
TestGateIsGreenOnItself corpus parametrization). tests/test_vet.py (145
tests) and the 6 touched fixture test files all still pass.

Gates: `frob check --ticket T-draft-eacc76c5` clean (0 errors), 155
warnings/171 waived repo-wide unchanged in kind. `gate:PII` 0 errors, 102
warnings, 3 waived.

### Changed
(no changed files detected)

### Evidence
- `tests/test_pii_structural_gate.py::TestReservedTestDomainEmails::test_example_com_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestReservedTestDomainEmails::test_lookalike_non_reserved_domain_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_frob_directive_comment_does_not_fire` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestKeywordSweep::test_ordinary_comment_mentioning_secret_still_fires` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestGateIsGreenOnItself::test_corpus_detector_files_produce_no_finding[src/frob/gates/_secrets.py]` (pytest node id, verified passing when recorded)
- `tests/test_pii_structural_gate.py::TestGateIsGreenOnItself::test_own_module_source_produces_no_self_finding` (pytest node id, verified passing when recorded)
