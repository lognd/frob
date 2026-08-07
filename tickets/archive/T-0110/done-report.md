## Done report

Data source + degrade design: `src/frob/vet/_osv.py::cve_ids` extracts
CVE-shaped ids from an osv-scanner advisory's own id plus its `aliases`
field (now carried on `OsvAdvisory`) -- a GHSA/PYSEC/RUSTSEC advisory with
no CVE alias yields an empty tuple and never enters the join, honestly,
rather than being guessed at. `src/frob/vet/_nvd.py::fetch_cwe_for_cve`
maps each CVE to its CWE ids via NVD's `cves/2.0` REST API, cache-first
(7d TTL, same `.frob/vet.db` `_registry.py` already uses, new
`nvd_cache` table) with the EXACT offline-first degrade posture
`_registry.py::fetch_publish_date` set for VET011: any network/parse
failure returns `ok=False` with a note, never a silent "no weaknesses"
result, and `fetch=False` (offline CI/tests) restricts to the existing
cache, degrading to `ok=False` on a miss rather than calling out.
`NVD-CWE-Other`/`NVD-CWE-noinfo` placeholders are filtered so they never
masquerade as real catalog CWE ids.

Join semantics: `src/frob/vet/_containment.py::build_containment_report`
is the thin join module. For each advisory's CVE id(s), it resolves CWE
ids via NVD, intersects them against `frob.strata.CWE_CATALOG` (import
only), and asks `find_importing_nodes` which node's `code=` glob binds a
file that imports the vulnerable dependency (heuristic top-level-module
match, e.g. `foo-bar` -> `foo_bar`; a divergent import name like
`pyyaml`/`yaml` is honestly `UNMODELED`, not guessed). It then reuses
`frob.strata.check_discharge_completeness` (no re-implementation of
THREAT003's firing/discharge logic) to classify: `state="live"` (a
covering node's obligation for that CWE is undischarged -- high
severity, no proof the weakness is mitigated where the vulnerable code
runs), `state="contained"` (discharged -- defense-in-depth), or
`state="unmodeled"` (no covering node, or no catalog entry for the
mapped CWE -- never conflated with "contained", deny-by-default).
`render_containment_report` gives a LIVE-first text rendering. This
module is an import-only consumer of the phase A-C public API
(`CWE_CATALOG`, `FOREIGN`, `bind_code`, `check_discharge_completeness`)
-- no `frob/strata/**` internals touched, no new kernel primitive. A
lazy `_strata()` import (called inside functions, not at module load)
was required to avoid a circular import: `frob.strata._effects` imports
`frob.vet._capability` at ITS module top level, so a module-level
`from frob.strata import ...` in `_containment.py` would close a cycle
through `frob.vet`'s own `__init__.py`.

Changed:
- src/frob/vet/_osv.py::OsvAdvisory (added `aliases` field)
- src/frob/vet/_osv.py::cve_ids (new)
- src/frob/vet/_nvd.py (new module: NvdResult, fetch_cwe_for_cve)
- src/frob/vet/_containment.py (new module: ContainmentFinding,
  ContainmentReport, LIVE/CONTAINED/UNMODELED, find_importing_nodes,
  build_containment_report, render_containment_report)
- src/frob/vet/__init__.py (exports for all of the above)
- docs/modules/vet.md (public API entries + "Containment (CVE->CWE join,
  phase D)" mechanics bullet)
- docs/strata/threat.md (phase D marked SHIPPED with join-semantics
  writeup)
- tests/test_vet_containment.py (new, 19 tests, network mocked
  throughout via monkeypatch on `_nvd.urllib.request.urlopen` and
  pre-seeded `.frob/vet.db` cache entries -- no real network call)

Evidence: 19 pytest node ids under
`tests/test_vet_containment.py::{TestCveIds,TestFetchCweForCve,
TestFindImportingNodes,TestBuildContainmentReport,
TestRenderContainmentReport}`, recorded via `frob ticket evidence
T-0110 ...`; bound via `frob:tests` directives on the exercising test
methods (`src/frob/vet/_osv.py::cve_ids`,
`src/frob/vet/_nvd.py::fetch_cwe_for_cve`,
`src/frob/vet/_containment.py::find_importing_nodes`,
`src/frob/vet/_containment.py::build_containment_report`,
`src/frob/vet/_containment.py::render_containment_report`, all
`kind="unit"`).

Filed: none (no out-of-scope discoveries; a `frob vet --containment` CLI
flag through `src/frob/app/vet_runner.py`/`__main__.py` is noted as a
follow-up in both docs touch-ups but NOT filed as a new ticket -- it is
plain CLI wiring of an already-public, already-tested function
(`render_containment_report`), not a design decision, and next free
ticket id T-0137 was reserved for this dispatch, not consumed).

Gates (round 1): `uv run ruff check` / `uv run ruff format --check` --
clean on touched files. `uv run ty check` -- clean. `uv run pytest
tests/test_vet_containment.py` -- 19 passed. `uv run pytest
tests/test_vet.py tests/unit/strata/` -- 419 passed (no regressions).
`frob test --base main` -- touched-set selection (61 touched symbols,
package fallback) green, `exit=0`. `frob ticket sweep T-0110` re-run
after implementation (prework had gone stale against the final scope;
PRE001 now clean). `frob check --ticket T-0110` -- ruff-check,
ruff-format, ty, frob-cycle, frob-dup, frob-arch, and all
frob-exports(*) tool checks PASS; zero unwaived violations attributable
to any file this ticket touched (`_osv.py`, `_nvd.py`, `_containment.py`,
`vet/__init__.py`, `test_vet_containment.py`, the two docs files) --
every remaining `gates` FAIL entry (TEST003 interface-coverage gaps,
PERF001-004 findings, TEST006 coverage-stamp) is pre-existing repo-wide
baseline in files this ticket never touched (`src/frob/strata/_elaborate.py`,
`strata-core/src/lib.rs`, etc.), i.e. the repo's A/B gate posture is
honestly unchanged by this ticket, not silently laundered. 4 new
`frob:waive` directives added, each with a specific PERF-rule reason
(2x PERF003 false-positive-nesting, 2x PERF004 hoisted-single-sort),
matching this file's existing waiver idiom exactly.

## Round 2 (reviewer REJECT -- addressed)

Reviewer verdict on round 1: REJECT. Degrade plumbing, tri-state vs
`"contained"`, imports, and cache design were all separately verified
clean; the finding was that a genuinely-failed NVD lookup and a
genuinely-no-coverage dependency were BOTH reported as `state="unmodeled"`
-- an NVD outage could silently read as "nothing here" instead of "we
don't know," which a triage consumer scanning for the worst finding must
never do.

**0. Merge-up**: `git add -A && git commit -m "wip"` then `git merge main
--no-edit` (worktree
`/home/logan/projects/frob/.claude/worktrees/agent-a41c19254bd3ce2fe`).
Clean auto-merge, no conflicts (main had landed T-0084 "frob sys plan"
and T-0114 "quality anti-pattern families" since my base at T-0113); my
Done report and evidence survived the merge intact.

**1. Fourth state `UNVERIFIED`**: added to `_containment.py` alongside
`LIVE`/`CONTAINED`/`UNMODELED`, with a module-docstring and inline
comment explaining WHY it must stay distinct from `UNMODELED` (an outage
is "we could not check," never "there is nothing here"). Placed directly
after `LIVE` in `_STATE_ORDER`/`_STATE_LABEL` (order: LIVE=0,
UNVERIFIED=1, CONTAINED=2, UNMODELED=3) -- justified in both the constant
comment and `render_containment_report`'s docstring: a triage consumer
scanning top-to-bottom must hit every unresolved data-source outage
before anything the join actually resolved (verified-live is still the
single most urgent thing; verified-unresolvable is the second most
urgent, ahead of either resolved answer). `build_containment_report`'s
`lookup.ok is False` branch now emits `state=UNVERIFIED` (was
`UNMODELED`); `_finding_for_pair`'s genuine-no-coverage branches
(no covering node / no catalog entry for the mapped CWE) are untouched
and still emit `UNMODELED`. Split the one test that pinned the
conflation (`test_unmodeled_when_nvd_lookup_fails`) into
`test_unverified_when_nvd_lookup_fails` (asserts `state == UNVERIFIED`
and `!= UNMODELED`) alongside the pre-existing
`test_unmodeled_when_no_node_imports_the_package` (now docstring'd as the
genuine-no-coverage case), plus a new render-order test
(`test_unverified_sorts_between_live_and_contained`) asserting all four
states render in LIVE/UNVERIFIED/contained/unmodeled order from one
mixed-order input.

**2. Malformed-NVD-body test**: `test_malformed_cached_body_degrades_
without_raising` seeds `.frob/vet.db` with a truncated JSON string
(`'{"vulnerabilities": [{"cve": {"weaknesses": [{"desc'`) and calls
`fetch_cwe_for_cve` through the real cache-read -> `_result_from_body`
parse path (`fetch=False` so it never hits the network); asserts
`ok=False`, `cwe_ids=()`, and a "could not verify" note -- no exception
propagates, confirming `_result_from_body`'s `try/except
(json.JSONDecodeError, ValueError, KeyError)` actually catches the
truncated-JSON case in practice, not just by inspection.

**3. TTL-expiry test**: `test_expired_cache_entry_triggers_a_fresh_fetch`
writes a valid cache entry via `_cache_set`, then directly back-dates its
`fetched_at` column past `_CACHE_TTL_S` (raw sqlite `UPDATE`, since
`_cache_set` always stamps `time.time()` -- patching `time.time` globally
would also perturb the TTL comparison itself, so back-dating the stored
row is the more direct proof of the TTL boundary than monkeypatching
`time`), then calls `fetch_cwe_for_cve(fetch=True)` with a mocked
`urlopen` and asserts the mock WAS invoked (proving the expired entry was
treated as a miss, not served stale) and that the fresh mocked body's CWE
id is what comes back.

**Out-of-scope discovery, filed not fixed**: while re-verifying against
main after the merge, `tests/unit/strata/test_threat.py` failed to
collect (`ImportError: cannot import name 'check_effect_completeness'
from 'frob.strata'`) -- confirmed via `git show
main:src/frob/strata/__init__.py` that this is a pre-existing regression
on main itself (commit `1b1629e` "restore T-0084's sys-plan surface
reverted by the T-0114 apply" dropped `check_effect_completeness` from
both the `_threat` import block and `__all__` while merging T-0114's
QUALITY exports back in), NOT something my merge introduced and NOT
within T-0110's `src/frob/vet/**`-first scope to fix (the dispatch
explicitly said import-only for `src/frob/strata/**`). Filed **T-0137**
with the root cause and the one-line fix location. Verified the blast
radius is real but contained to that one file: with
`tests/unit/strata/test_threat.py` moved aside (non-destructively, for
verification only, restored immediately after), `frob check --ticket
T-0110` shows every tool-level check PASS and zero unwaived violations
in any file this ticket touched; with it in place, the SAME broken
pytest collection cascades into ~387 unrelated `COV003`/`TEST002` false
failures repo-wide (a pytest-collection failure poisons `frob check`'s
whole-suite collection cache), which is the mechanism, not a T-0110 bug.

Evidence: 22 pytest node ids now (3 new: the malformed-body test, the
TTL-expiry test, the render-order test, plus the renamed
`test_unverified_when_nvd_lookup_fails`), recorded via `frob ticket
evidence T-0110 ...` (ledger's `evidence:` list updated to match).

Filed: T-0137 (pre-existing main-branch regression, see above); no other
out-of-scope discoveries.

Gates (round 2, current): `uv run ruff check` / `uv run ruff format
--check` -- clean on touched files. `uv run ty check` -- clean. `uv run
pytest tests/test_vet_containment.py` -- 22 passed (3 more than round
1's 19). `uv run pytest tests/test_vet.py tests/test_vet_containment.py`
-- all green; `uv run pytest tests/unit/strata -q
--continue-on-collection-errors` -- every strata test file collects and
passes except the pre-existing T-0137 collection failure in
`test_threat.py` (unrelated to this ticket). `frob test --base main` --
touched-set selection (65 touched symbols, package fallback) green,
`exit=0`. `frob ticket sweep T-0110` re-run after the merge (prework had
gone stale against main's landed tickets). `frob check --ticket T-0110`
(with T-0137's broken collection file moved aside for the duration of
the check only, then immediately restored) -- ruff-check, ruff-format,
ty, frob-cycle, frob-dup, frob-arch, and all frob-exports(*) tool checks
PASS; zero unwaived violations attributable to any file this ticket
touched. Not closed, not committed, per instruction.
