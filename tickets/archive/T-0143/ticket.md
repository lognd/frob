---
id: T-0143
title: 'std.cwe catalog: transcribe the cwe-top-25 view (and stub-free ASVS decision)'
state: done
kind: security
origin: human
created: '2026-07-18'
priority: medium
parent: null
tier: ticket
sprint: null
runs_last: false
milestone: null
runs_last_parallel_safe: false
runs_last_parallel_safe_reason: null
scope_breadth_ack: false
scope_breadth_ack_reason: null
no_scope_declared: false
no_scope_declared_reason: null
body_changes:
- mode: append
  reason: condense VIEWS design rationale into T-0143 body
  actor: logan
  at: '2026-09-19'
  old_length: 963
  new_length: 2022
- mode: append
  reason: condense cwe-top-25 transcription rationale into T-0143 body
  actor: logan
  at: '2026-09-19'
  old_length: 2022
  new_length: 5744
evidence:
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_is_satisfied
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_has_25_members
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_view_not_merged_into_default_views
- tests/unit/strata/test_threat.py::TestCweTop25::test_missing_out_of_scope_entry_is_a_violation
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_top_25_catalog_never_leaks_into_owasp_top_10_view
- tests/unit/strata/test_threat.py::TestCweTop25::test_out_of_scope_entries_have_specific_nonempty_reasons
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_reuses_the_exec_capability_join
- tests/unit/strata/test_threat.py::TestCweTop25::test_memory_safety_entries_name_the_missing_kernel_concept
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_77_discloses_duplicate_coverage_of_cwe_78
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_fires_and_discharges_on_exec_capability
- tests/unit/strata/test_threat.py::TestCweTop25::test_cwe_94_fires_and_is_undischarged_with_no_claim
designated_repro_test: null
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: null
---
Phase A shipped the 9 charter core-reframe CWEs backing owasp-top-10 only; cwe-top-25 / owasp-asvs / cwe-1000 were deliberately not stubbed so THREAT001 cannot lie. User asks for fuller coverage. Scope: transcribe the current MITRE CWE Top 25 into WeaknessEntry rows -- each with real cite URL, accurate title, meaningful mitigation, capability_kind where the charter's instantiation semantics genuinely apply, and honest OutOfScopeEntry rows (with specific reasons) for entries whose preconditions the kernel cannot yet express (matching the T-0114 discipline). Add the cwe-top-25 view; extend tests: view completeness proves, per-entry data spot checks, and at least two new fired-obligation cases for newly-instantiable kinds. owasp-asvs/cwe-1000: make an explicit documented decision (transcribe, or keep unstubbed with rationale in threat.md) rather than silence. Pin the catalog to a named CWE release version per the charter's staleness-review requirement.

<!-- narrative-moved:src/frob/strata/_threat_catalog_cwe.py:454:T-0143 -->
: Baseline VIEWS: the id set a selected view holds the catalog to. Phase A
: ships one view, the OWASP Top-10 subset actually cataloged above;
: `owasp-asvs`/`cwe-1000` remain deliberately unstubbed -- see docs/
: strata/threat.md#the-catalog-stdcwe for the recorded decision (ASVS is a
: verification standard, not a weakness list; cwe-1000 is a ~900-entry
: research view where transcription without kernel preconditions would be
: out-of-scope spam) -- so THREAT001 never lies about a view it cannot
: check. `cwe-top-25` (T-0143) is intentionally NOT merged into this dict:
: `_audit.py::DEFAULT_SECURITY_VIEWS` iterates `tuple(VIEWS)` and checks
: every member against the bare `CWE_CATALOG` default -- exactly the
: `QUALITY_CATALOG`/`QUALITY_VIEWS` split's rationale above, reused here
: since `cwe-top-25` needs the combined `CWE_CATALOG + CWE_TOP_25_CATALOG`
: catalog, not the default alone (see `CWE_TOP_25_VIEWS` below).
frob:doc docs/strata/threat.md#the-catalog-stdcwe

<!-- narrative-moved:src/frob/strata/_threat_catalog_cwe.py:141:T-0143 -->
: T-0143/T-0345 (docs/strata/threat.md#the-catalog-stdcwe): the
: `cwe-top-25` view, transcribed from the 2025 MITRE CWE Top 25 Most
: Dangerous Software Weaknesses (https://cwe.mitre.org/top25/archive/2025/
: 2025_cwe_top25.html, pinned release year 2025 -- T-0345 bumped this from
: the stale 2023 pin two releases behind; staleness review against a newer
: release is the charter's obligation, docs/strata/threat.md#the-catalog-
: stdcwe "a versioned vocabulary pack ... pinned to a MITRE CWE release ...
: staleness past a review bound is a gate warning"). Seven of the 25 ids
: are already cataloged in `CWE_CATALOG` above (CWE-79/89/78/22/918/502/
: 352) -- reused here, not duplicated (charter: no duplication). Two more
: are genuinely new obligations (`CWE_TOP_25_CATALOG`, below --
: `capability_kind` where the charter's instantiation semantics apply):
: CWE-94 (unchanged from the 2023 pin, reuses CWE-78's `exec` join) and
: CWE-639 (2025-list-new; reuses `QUALITY_CATALOG`'s existing `sql`-join
: entry rather than duplicating it, the SAME disclosed-reuse convention
: CWE-94 already follows). The remaining 16 are honest `OutOfScopeEntry`
: rows (`CWE_TOP_25_OUT_OF_SCOPE`) whose preconditions the kernel model
: has no vocabulary for yet: memory-safety ids (no pointer/buffer/
: allocator model -- now six of them: CWE-787/416/125/476 carried over
: plus 2025-list-new CWE-120/121/122, all buffer-overflow variants of the
: SAME missing buffer/bounds model), an authn/authz-boundary group (no
: endpoint/route + authn/authz predicate concept, same gap
: `SEC-ROUTE-AUTHZ-001` above already names -- CWE-862/863/306 carried
: over plus 2025-list-new CWE-284 (the generic parent of CWE-862/863 with
: no precondition of its own, the SAME generic-parent shape CWE-20
: already discloses) and CWE-200 (2025-list-new, `Exposure of Sensitive
: Information`; docs/design/registry/weaknesses.yaml's independent
: CWE-1000 disposition sweep classifies this id the same way,
: `out-of-scope:authn-authz-boundary-predicate`, cross-checked here to
: avoid re-litigating a judgment that sweep already made)), a file-upload
: id (no content-type-validation sink), a generic-input-validation id (no
: structural precondition, same "needs hand-written assert claims" class
: as CWE-840, docs/strata/threat.md#what-is-honestly-not-covered), a
: duplicate-coverage id (CWE-77, the generic parent of CWE-78's already-
: cataloged OS-command instance -- disclosed as non-duplicated, the SAME
: discipline the module docstring above applies to stored XSS), and one
: 2025-list-new resource-exhaustion id (CWE-770, needs a resource-
: allocation/rate-limiting model the kernel does not carry). Dropped from
: the 2023 pin (no longer 2025-list members, so no longer `cwe-top-25`
: obligations at all -- their `OutOfScopeEntry`/`CWE_CATALOG` rows are
: removed, not archived, since this view's membership is the CITED
: release's, not a running union of every release ever pinned):
: CWE-798 (still in `CWE_CATALOG` above, just no longer a top-25 member),
: CWE-287/190/119/362/269/276 (were `OutOfScopeEntry` rows here only,
: removed outright).
frob:doc docs/strata/threat.md#the-catalog-stdcwe
frob:ticket T-0143
frob:ticket T-0345
frob:ticket T-0401
frob:tests tests/unit/strata/test_threat.py::TestEvalFiresCwe94.test_eval_capability_is_classified_not_benign_excused  # noqa: E501
frob:tests tests/unit/strata/test_threat.py::TestEvalFiresCwe94.test_eval_capability_fires_a_real_cwe94_obligation  # noqa: E501
frob:tests tests/unit/strata/test_threat.py::TestEvalFiresCwe94.test_eval_capability_discharges_with_a_real_mitigation_claim  # noqa: E501