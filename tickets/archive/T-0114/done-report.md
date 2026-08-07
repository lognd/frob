## Done report

Family entries implemented vs disclosed out-of-scope (charter table, docs/strata/threat.md#beyond-security-the-anti-pattern-families):

| Anti-pattern | Family | Status | Mechanism |
|---|---|---|---|
| Misused dynamic ORM condition (CWE-639) | security | IMPLEMENTED (`QUALITY_CATALOG`) | reuses the SAME `sql` `capability_kind` join CWE-89 already fires on (no new detection); mitigation name `tenant_scoping` distinguishes it from CWE-89's `parameterization` |
| Single-dependency bottleneck (REL-001) | reliability | IMPLEMENTED (`QUALITY_CATALOG`, catalog-only) | `capability_kind=None`; actual refutation is the existing capacity/budget arithmetic (T-0066), same pattern as the phase-A CWE-22/352/798 citation-only entries |
| Non-statically-hosted content (PERF-002) | performance | IMPLEMENTED (`QUALITY_CATALOG`, catalog-only) | `capability_kind=None`; actual refutation is the existing std.infra cdn/immutable machinery |
| Stored XSS (two-hop) | security | IMPLEMENTED -- no new entry needed | the existing CWE-79 `NoFlow(src=foreign,dst=node)` chokepoint check already walks `reachable` transitively, so a foreign->store->render path is the SAME obligation the phase-A entry covers; disclosed in threat.md rather than duplicated |
| Uncompressed JSON | performance | disclosed out-of-scope (`PERF-COMPRESS-001`) | needs a new size-threshold + transport/compression precondition predicate, not an existing capability/flow join |
| One-at-a-time DB writes | performance | disclosed out-of-scope (`PERF-BATCH-001`) | needs a write-cardinality (per-item vs batch) distinction the kernel model has no field for |
| Un-optimistic rendering | performance | disclosed out-of-scope (`PERF-OPTIMISTIC-001`) | needs a synchronous `waits_for` render-to-response edge concept, no kernel field |
| Wide-open CORS | security | disclosed out-of-scope (`SEC-CORS-001`) | needs a CORS-specific boundary predicate cross-checked against a flow's credential label, no kernel vocabulary |
| Loose backend URL rules (route-authz + open redirect) | security | disclosed out-of-scope (`SEC-ROUTE-AUTHZ-001`) | needs an endpoint/route concept and redirect-target-taint precondition, no kernel field |

No `compatibility`-family view is stubbed: the charter's concrete table names zero compatibility rows, so a `compat-baseline` view would lie about what it checks (same "never stub an unshipped view" rule the phase-A `VIEWS` table already follows for `cwe-top-25`/`owasp-asvs`/`cwe-1000`).

Changed:
- `src/frob/strata/_threat.py::QUALITY_CATALOG` -- 3 new `WeaknessEntry` rows (CWE-639, REL-001, PERF-002)
- `src/frob/strata/_threat.py::QUALITY_OUT_OF_SCOPE` -- 5 reasoned `OutOfScopeEntry` rows
- `src/frob/strata/_threat.py::QUALITY_VIEWS` -- 3 family-scoped baseline views (`web-performance-baseline`, `reliability-baseline`, `web-quality-security-baseline`), each proved exhaustive by the SAME `check_catalog_completeness` (THREAT001), unmodified
- `src/frob/strata/__init__.py` -- re-exports `QUALITY_CATALOG`/`QUALITY_OUT_OF_SCOPE`/`QUALITY_VIEWS`
- `docs/strata/threat.md` -- phasing item E marked SHIPPED with the same family-entries-vs-disclosed table
- `tests/unit/strata/test_threat.py::TestQualityFamilies` -- 7 new tests

Evidence: 7 test node ids recorded via `frob ticket evidence T-0114` (see `evidence:` block above).

Exact numbers:
- `tests/unit/strata/test_threat.py`: 54 passed (was 47 before this ticket; +7 new)
- Full strata suite (`tests/unit/strata/` + `tests/unit/test_lang_strata.py`): 371 passed (was 364 before this ticket)
- `frob check --ticket T-0114`: 87 violations / 24 waived, all pre-existing repo-wide `frob:waive` entries (PERF003/PERF004 sort/nested-loop waivers on unrelated files, plus baseline `frob-exports` "not exported" warnings) -- zero new unwaived heuristic trips from this change; `frob-dup` moved 46 -> 47 groups (expected: new catalog/test code), no COV/DRIFT/DOC violation tied to this ticket's scope
- `frob test --base main`: touched=15 selected via package fallback, `uv run pytest -q src/frob/strata tests/unit/strata/test_threat.py` exit=0, 3.41s

Filed: none (no out-of-scope work found beyond the charter's own disclosed cuts, which are recorded as `QUALITY_OUT_OF_SCOPE` catalog entries per the charter's own mechanism, not new tickets)

Gates: `frob check --ticket T-0114` clean -- no unwaived violation introduced by this diff; all PERF003/PERF004 hits on `src/frob/strata/_threat.py` are pre-existing waived sort-of-view-members patterns the new code follows exactly (same waive reason, same shape).
