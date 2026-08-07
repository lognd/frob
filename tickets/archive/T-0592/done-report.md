## Done report

`frob check --only registry` started at 115 warnings (114 REG008 + 1 REG010, 0
errors) after merging main (tip 80179a6, later re-verified against 3f92b12)
and `make core`. Batched by registry file, verifying each anchor against the
real enforcing function before adding it:

- arch-checks.yaml (2 entries): DUP001/ACC-2-1-DUPLICATED-CODE anchored at
  `frob.dup._rules.DUP001`; ARCH001/ACC-2-1-LONG-FUNCTION anchored at
  `frob.gates._arch.arch_gate`. Also anchored the reflexive
  CHK-GATE-ARCH001/DUP001/DUP002 check-coverage entries at the same
  functions.
- pii.yaml (7 entries) + secrets.yaml (2 entries): all 7 pii.yaml corpus
  entries anchored at `frob.gates._pii_structural.pii_structural_gate`
  (verified it is the sole PII010/SEC110 enforcer). secrets.yaml's two
  entries (DETECT_SECRETS_PLUGINS, PROVIDER_TOKEN_FORMATS) were
  dispositioned `handled_by:SEC002`, which is FALSE -- SEC002 is the
  tracked-.env-file check, unrelated to plugin/token-format detection; the
  actual enforcer is the `_PATTERNS` regex table (SEC001, with SEC003 for
  the unwaivable Stripe-live carve-out). Flipped both dispositions to
  `handled_by:SEC001` with an inline comment explaining why, then anchored
  `secrets_gate` for SEC001/SEC002/SEC003 plus the two corrected entries.
- weaknesses.yaml (16 entries): all 16 SEC-CVE-FINGERPRINT-* needle
  categories anchored at `frob.gates._cve_fingerprint_scan.
  cve_fingerprint_scan_gate`, cross-checked against the needle ids in
  `frob.strata._cve_fingerprint.CVE_FINGERPRINTS`.
- check-coverage.yaml (87 entries): anchored each CHK-GATE-<rule> at its
  verified enforcing function across `frob.gates.__init__`,
  `frob.gates._registry_exhaustiveness` (REG001-007), `frob.gates.
  decisions`, `frob.gates._docblocks`, `frob.gates._exclude_hazard`,
  `frob.gates._lang_conformance`, `frob.gates._refs`, `frob.gates.
  _render_lint`, `frob.gates._walk_lint`, `frob.fuzz._rules` (FUZZ001-003),
  and `frob.perf._rules.perf_rules` (PERF001-007, which composes
  `recursion_rules`/`redundant_computation_violations`).
- REG010 (4 live rules -- TEST012-015 -- with no CHK-GATE entry at all):
  ran `frob registry audit --sync-gate-rules` to file the 4 missing
  entries, then anchored TEST012/013/014/015 at their enforcing functions
  in `frob.gates.__init__`.

Final `frob check --only registry`: 0 errors, 0 warnings for gate:REG (was
114 REG008 + 1 REG010). The 2 remaining WAIVE002 warnings in the tool
summary are pre-existing, unrelated `frob:waive DEAD001` typos in
tests/test_dup_cross_lang.py and tests/unit/test_dup_cache.py -- outside
this ticket's scope, not touched.

`frob check --ticket T-draft-f8aabdf0` (full check): registry gate clean;
6 unrelated COV003 errors surfaced (T-0583/T-0585 evidence referencing
pytest node ids that do not collect even after a fresh `pytest
--collect-only`) -- pre-existing on main, not caused by this diff (my diff
never touches those tests or tickets). Filed T-draft-959e1bcd for it rather
than silently fixing or ignoring.

Counts: anchored 114 (2 arch-checks + 7 pii + 2 secrets(via corrected
disposition) + 16 weaknesses + 87 check-coverage, including the 4
REG010-filed TEST012-015), disposition-flipped 2 (secrets.yaml SEC002 ->
SEC001), entry-added 4 (TEST012-015 via --sync-gate-rules).

### Changed
```
 docs/design/registry/check-coverage.yaml   |  18 +-
 docs/design/registry/secrets.yaml          |  11 +-
 src/frob/dup/_rules.py                     |   3 +
 src/frob/fuzz/_rules.py                    |   3 +
 src/frob/gates/__init__.py                 |  53 +++++
 src/frob/gates/_arch.py                    |   2 +
 src/frob/gates/_cve_fingerprint_scan.py    |  17 ++
 src/frob/gates/_docblocks.py               |   1 +
 src/frob/gates/_exclude_hazard.py          |   1 +
 src/frob/gates/_lang_conformance.py        |   3 +
 src/frob/gates/_pii_structural.py          |   9 +
 src/frob/gates/_refs.py                    |   3 +
 src/frob/gates/_registry_exhaustiveness.py |   7 +
 src/frob/gates/_render_lint.py             |   1 +
 src/frob/gates/_secrets.py                 |   5 +
 src/frob/gates/_walk_lint.py               |   1 +
 src/frob/gates/decisions.py                |   2 +
 src/frob/perf/_rules.py                    |   7 +
 tickets.md                                 | 351 ++++++++++++++++++++++++++++-
 19 files changed, 491 insertions(+), 7 deletions(-)
```

### Evidence
(no evidence recorded)
