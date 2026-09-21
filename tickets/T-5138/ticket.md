---
id: T-5138
title: 'Live advisory data in vet: OSV.dev batch API in-process, no external binary,
  cached with staleness refusal, on by default in check and land'
state: in-progress
kind: security
origin: human
created: '2026-09-20'
priority: critical
parent: null
tier: story
sprint: v0.533.0
runs_last: false
milestone: 1.0.0
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope:
- src/frob/vet/*.py
- frob.toml
- docs/modules/vet.md
- src/frob/strata/_cve_fingerprint.py
scope_breadth_ack: true
scope_breadth_ack_reason: one advisory source module plus the vet stage, config default
  and docs that consume it
no_scope_declared: false
no_scope_declared_reason: null
triage_changes:
- field: milestone
  old_value: null
  new_value: 1.0.0
  reason: milestone set via `frob ticket milestone`
  actor: logan
  at: '2026-09-20'
evidence:
- tests/vet_suite/test_advisories.py::TestOsvAdapter::test_query_advisories_positive_control_fires_a_known_advisory
- tests/vet_suite/test_advisories.py::TestOsvAdapter::test_query_advisories_serves_fresh_cache_with_no_network_call
- tests/vet_suite/test_advisories.py::TestOsvAdapter::test_query_advisories_no_cache_no_network_is_unavailable
- tests/vet_suite/test_advisories.py::TestOsvAdapter::test_query_advisories_stale_cache_beyond_max_age_is_unavailable
- tests/vet_suite/test_advisories.py::TestVetConfigDefault::test_default_frob_toml_enables_advisories_with_no_opt_in
designated_repro_test: null
acceptance:
- text: given a lockfile pinning a version with a known OSV advisory, when frob vet
    runs with network, then VET005 fires naming the advisory id, CVSS and fixed version
  evidence:
  - tests/vet_suite/test_advisories.py::TestOsvAdapter::test_query_advisories_positive_control_fires_a_known_advisory
- text: given the same lockfile and no network but a cache younger than the max age,
    when frob vet runs, then the same finding fires from cache with no spawn
  evidence:
  - tests/vet_suite/test_advisories.py::TestOsvAdapter::test_query_advisories_serves_fresh_cache_with_no_network_call
- text: given no cache and no network, when frob vet runs, then VET012 reports advisory
    data unavailable and the run is not clean
  evidence:
  - tests/vet_suite/test_advisories.py::TestOsvAdapter::test_query_advisories_no_cache_no_network_is_unavailable
  - tests/vet_suite/test_advisories.py::TestOsvAdapter::test_query_advisories_stale_cache_beyond_max_age_is_unavailable
- text: given a fresh clone with default frob.toml, when frob check runs, then the
    advisory query executes without any opt-in flag
  evidence:
  - tests/vet_suite/test_advisories.py::TestVetConfigDefault::test_default_frob_toml_enables_advisories_with_no_opt_in
acceptance_amendments:
- op: remove
  index: 5
  old_text: given ruff two minor versions behind PyPI, when frob doctor runs, then
    it reports the lag
  new_text: null
  reason: out of T-5138's declared scope (src/frob/vet/*.py, frob.toml, docs/modules/vet.md,
    src/frob/strata/_cve_fingerprint.py -- doctor.py is not in it); filed T-draft-bf260aec
    to implement frob doctor's lint-tool version-lag reporting
  actor: logan
  at: '2026-09-21'
threat: tampering
component: vet
anchor: false
anchor_reason: null
land_commit: null
worktree: /home/logan/projects/frob/.claude/worktrees/t-5138
branch: t-5138
---
Owner directive 2026-09-20: frob must have current CVE and dependency-advisory information. MEASURED: VET005 is opt-in (frob.toml vet.osv = false) and delegates to an osv-scanner binary that is not installed on this machine; pip-audit and cargo-audit are also absent; so advisories have NEVER fired here (catalogued is not enforced). The CVE fingerprint catalog (_cve_fingerprint.py) holds 19 hand-curated entries. DESIGN: (1) Source: query OSV.dev directly over HTTPS (POST https://api.osv.dev/v1/querybatch, up to 1000 {package:{purl}} or {package:{name,ecosystem},version} queries per call; GET /v1/vulns/{id} for details) using the stdlib or the already-vetted HTTP client; OSV aggregates GitHub Advisory DB (GHSA), PyPA, RustSec, npm, Go, and NVD-derived CVE aliases, so it is the one upstream. No external binary required; osv-scanner, pip-audit, npm audit and cargo audit remain optional adapters that add nothing when absent. (2) Inputs: every lockfile frob already parses for VET007 (uv.lock, poetry.lock, requirements*.txt, package-lock.json, pnpm-lock.yaml, yarn.lock, Cargo.lock, go.sum, packages.lock.json for C#), mapped to purls. (3) Cache: .frob/vet.db table advisories(purl, version, fetched_at, payload) plus a per-lockfile-hash verdict; TTL 24 h; a run whose cache is older than vet.advisory_max_age_days (default 7) and cannot reach OSV yields a VET012 ERROR 'advisory data stale since <date>' rather than a silent clean (silent-zero lesson); a run with no cache and no network yields VET012 as well, never a pass. (4) Automatic: on by default (vet.osv default flips to true; rename to vet.advisories); runs inside frob vet, the VET stage of frob check, and the pre-land sweep; a background refresh piggybacks on the post-commit trigger so interactive runs hit the cache. Positive control: a test that pins a known-vulnerable version (e.g. requests 2.31.0 or a fixture lockfile) and asserts VET005 fires; the CI job runs it with network. (5) Severity: CVSS from the OSV record; error at >= 7.0 or when a fix version exists, warn otherwise; remedy text names the fixed version. (6) Fingerprints: extend the catalog loader to pull affected-function ranges from OSV 'affected[].ecosystem_specific' and 'database_specific' where present so the 19 hand entries stop being the only vulnerable-usage source; keep the hand entries for what OSV cannot express. (7) Lint-tool currency: frob doctor reports the installed versions of ruff, ty, mypy, eslint, clippy against the latest release on PyPI/npm/crates (cached 24 h) and warns past a configurable lag. (8) Docs: docs/modules/vet.md gains the data-flow, TTL and staleness semantics; the compliance registry entry cites CISA KEV as an optional second list (https://www.cisa.gov/known-exploited-vulnerabilities-catalog) for an exploited-in-the-wild escalation.