## Done report

Not self-closed -- reviewer signs off.

Changed (all within scope):
- `src/frob/strata/_threat.py`: `QUALITY_CATALOG` gains a `CWE-295`
  (Improper Certificate Validation) `WeaknessEntry` -- `family="security"`,
  `capability_kind=None` (fired only via the `std.cve` fingerprint layer,
  not a `may`-capability auto-instantiation), `mitigation=
  "certificate_verification_enabled"`. Honest views placement: it belongs
  to neither the verified `owasp-top-10` (`CWE_CATALOG`) nor `cwe-top-25`
  (`CWE_TOP_25_CATALOG`, `_CWE_TOP_25_IDS` -- CWE-295 is not one of the 25)
  membership without a fresh, dated re-verification against those specific
  pinned lists, so it is cataloged in `QUALITY_CATALOG` with NO
  `QUALITY_VIEWS` entry -- the same "catalog entry need not belong to any
  named view" precedent `CWE-639`/`REL-001`/`PERF-002` already establish
  (confirmed against `check_catalog_completeness`'s per-view contract, not
  "every entry needs a view").
- `src/frob/strata/_cve_fingerprint.py`: `CVE_FINGERPRINTS` gains three
  entries joined to `CWE-295` -- `FP-TLS-VERIFY-001` (python
  requests/httpx/aiohttp `verify=False`, cites CVE-2024-35195),
  `FP-TLS-VERIFY-002` (TypeScript/Node `rejectUnauthorized: false`, cites
  CVE-2021-22939), `FP-TLS-VERIFY-003` (Rust reqwest
  `danger_accept_invalid_certs(true)`, cites CVE-2026-30794). Every CVE
  citation web-searched and checked against a vendor/NVD/advisory source at
  authoring time, never hand-guessed. Module docstring updated: the
  "curated, not exhaustive" disclosed-gap list now names only CWE-916
  (weak-hash password storage) and CWE-611 (XXE) as still-cut; CWE-295 is
  recorded as the T-0188 follow-up that unblocked it. CWE-916 reconciled by
  clarifying the docstring's disclosed-gap wording (still no `WeaknessEntry`
  for CWE-916 in any catalog tuple -- the docstring no longer bundles it
  with CWE-295 now that CWE-295 has shipped).
- `docs/strata/threat.md`: the CVE-fingerprints section's "curated, not
  exhaustive" paragraph updated to match -- nine to twelve fingerprints,
  CWE-295's gap-then-follow-up recorded, CWE-916/CWE-611 remain the
  disclosed cut.
- `tests/unit/strata/test_threat.py`: `TestQualityFamilies::
  test_cwe_295_is_cataloged_with_no_capability_kind_or_view` -- entry
  shape, `capability_kind is None`, and absence from `owasp-top-10`,
  `cwe-top-25`, `CWE_CATALOG`, and every `QUALITY_VIEWS` member set.
- `tests/test_vet.py`: six new `TestFingerprintScan` cases -- one
  positive/negative pair per language (python `verify=False`, TypeScript
  `rejectUnauthorized: false`, Rust `danger_accept_invalid_certs(true)`),
  mirroring the class's existing positive/negative-source pattern for
  `FP-DESERIALIZE-YAML-001`/`FP-CODEEVAL-TEMPLATE-001`.

Filed: none -- CWE-916/CWE-611 remain an intentionally disclosed gap per
the ticket's own scope (T-0189 already exists for CWE-611; CWE-916 is
described, not filed, per the ticket wording "add it or fix the
docstring" -- the docstring fix was chosen since a genuine CWE-916 catalog
addition needs its own citation-verification pass, out of this ticket's
narrower CWE-295 scope).

Evidence (7 ids, all resolved against a fresh `pytest --collect-only`,
recorded via `frob ticket evidence T-0188`):
- `tests/unit/strata/test_threat.py::TestQualityFamilies::test_cwe_295_is_cataloged_with_no_capability_kind_or_view`
- `tests/test_vet.py::TestFingerprintScan::test_matches_tls_verify_false_python`
- `tests/test_vet.py::TestFingerprintScan::test_no_match_on_verified_tls_python`
- `tests/test_vet.py::TestFingerprintScan::test_matches_tls_reject_unauthorized_false_node`
- `tests/test_vet.py::TestFingerprintScan::test_no_match_on_reject_unauthorized_true_node`
- `tests/test_vet.py::TestFingerprintScan::test_matches_tls_danger_accept_invalid_certs_rust`
- `tests/test_vet.py::TestFingerprintScan::test_no_match_on_default_reqwest_builder_rust`

Gates: `make core` (natives were unbuilt in this fresh worktree, per
playbook section 1) + `frob test --collect` (2904 python node ids, 0
missing natives) run first. `ruff format`/`ruff check` clean on all changed
files. `make coverage` (FOREGROUND, not backgrounded) green: full suite
2904 passed (2 skipped) with branch coverage; `.frob/coverage-stamp`
restamped (`stamp_coverage: stamped 404 file(s)`). `frob check --ticket
T-0188`: 1 error, 10 warnings, 203 waived (`archgate`/`clones`/etc. all
`pass`; the 10 warnings and 203 waived entries are pre-existing,
unaffected by this ticket's diff -- confirmed by a `git stash` A/B: 0
errors on the pre-edit tree, same warning/waiver counts otherwise).

Open item for the reviewer (NOT fixed, disclosed rather than silently
worked around): the one remaining error is **REL001** -- "public API
changed (major) since 0.13.0; bump the version to >= 0.14.0". Adding a new
`WeaknessEntry`/three `CveFingerprint` entries is a genuine additive
public-API surface change, so REL001 firing is correct. Discharging it
requires editing `pyproject.toml`, `CHANGELOG.md`, `.frob-release.json`,
and `uv.lock` (via `frob release stamp`) -- NONE of which are in T-0188's
declared `scope` (`src/frob/strata/**`, `tests/**`,
`docs/strata/threat.md`, `tickets.md`). I attempted the bump once
(0.13.0 -> 0.14.0, CHANGELOG entry, `frob release stamp`) to verify the
mechanics work, confirmed `frob release check` goes green, then REVERTED
all four files per the hard rule against expanding scope on my own
(`git checkout -- pyproject.toml CHANGELOG.md .frob-release.json
uv.lock`) rather than silently widening scope or leaving an
undisclosed partial state. Note for whoever picks this up: `frob release
stamp` invokes a `uv build`, which in this worktree UNINSTALLED the
editable `strata_core`/`frob_core` natives mid-run (the exact T-0333
failure class already documented in the playbook/CHANGELOG) -- after
reverting, `make core` + `frob test --collect` were re-run before the
final `make coverage` pass above, so the green coverage run reported here
is against the reverted (in-scope-only) tree, not the transient
release-stamp state. Recommend the reviewer either extend T-0188's scope
to include the four release files and land the bump in this same ticket,
or open a follow-up ticket for the version bump alone.
