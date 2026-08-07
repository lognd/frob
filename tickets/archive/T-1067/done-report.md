## Done report

Re-measured `frob check --only arch --json` first, per the dispatch
instructions: after T-1068's language-parity detector-precision fix
landed, abstraction-opportunity findings actually rose to 87 (not the
84 T-0393's agent originally measured) -- T-1068 only excludes groups
where EVERY member carries a DISTINCT per-language tag from a fixed set
(py/rust/kt/ts/cpp); it correctly leaves mixed/coincidental groups and
same-tag-collision groups flagged, and unrelated code changes elsewhere
added a few more findings in the interim.

Extracted two genuine near-duplicate families this pass:

1. `frob.gitio.excerpt` (public) -- was a byte-identical private
   `_excerpt` defined separately in `gitio.py` and
   `testing/_runners.py`; the latter already imports from `gitio`, so
   made the gitio copy public and deleted the duplicate, updating all
   call sites.
2. `frob.vet._cache.ttl_cache_get`/`ttl_cache_set` -- extracted from
   near-identical private `_cache_get`/`_cache_set` sqlite TTL-cache
   helpers duplicated in `vet/_nvd.py` and `vet/_registry.py` (already
   flagged with a prior T-0977 ARCH103 waiver acknowledging the
   duplication existed but treating it as acceptable at the time);
   parametrized by table name and TTL so both callers keep their own
   table/TTL values with no behavior change. Updated
   `tests/test_vet_containment.py`'s fixtures (which called the old
   private `_nvd._cache_set` directly) to use the new shared helper.

This dropped abstraction-opportunity from 87 to 84 (net -3; the
extraction removed the specific groups these functions were flagged in).
The remaining 84 is genuinely too large for one pass -- filed four
per-package follow-up tickets with exact counts and per-file breakdowns
so a future pass can work them incrementally without re-triaging from
scratch: T-1082 (gates/**, 29), T-1084 (arch/**, 27),
T-1085 (app/**, 5), T-1083 (remaining single-file
packages, 23). Each ticket's body flags where a genuine extraction looks
likely vs. where the finding is probably a new detector-precision FP
class (documented same-name forwarding wrappers in render/_renderer.py,
a per-language-tag naming gap in testing/_collect.py that T-1068's
`_LANGUAGE_TAGS` doesn't cover, and a suspected local-nested-closure
false-positive pattern in vet/_capability.py) so the next agent does not
have to re-derive that triage.

Gates: `frob check --only lint/static/gates-fast/gates-native
--ticket T-1067` all pass (post-merge-main; the one pre-existing
gates-fast COV003 failure, T-0666's stale evidence ids, is unrelated
pre-existing debt already tracked as T-1080, confirmed present on main
before this ticket touched anything). Tests: full pass on
tests/test_vet.py, tests/test_vet_containment.py, tests/test_gitio.py,
tests/test_testing.py.

### Changed
```
 docs/modules/testing.md       |   8 ++++
 docs/modules/vet.md           |  11 +++++
 src/frob/gitio.py             |  15 ++++--
 src/frob/testing/_runners.py  |  17 ++-----
 src/frob/vet/_cache.py        |  74 ++++++++++++++++++++++++++++-
 src/frob/vet/_nvd.py          |  65 ++++---------------------
 src/frob/vet/_registry.py     |  67 +++++---------------------
 tests/test_vet_containment.py |  19 +++++---
 tickets.md                    | 107 +++++++++++++++++++++++++++++++++++++++++-
 9 files changed, 248 insertions(+), 135 deletions(-)
```

### Evidence
- `tests/test_gitio.py::TestWorkingDiff::test_bad_base_ref_is_git_failed` (pytest node id, verified passing when recorded)
- `tests/test_gitio.py::TestWorkingDiff::test_diff_command_failure_propagates` (pytest node id, verified passing when recorded)
- `tests/test_testing.py::TestRunners::test_exit_code_is_data` (pytest node id, verified passing when recorded)
- `tests/test_vet_containment.py::TestFetchCweForCve::test_cached_body_parses_cwe_ids` (pytest node id, verified passing when recorded)
- `tests/test_vet_containment.py::TestFetchCweForCve::test_malformed_cached_body_degrades_without_raising` (pytest node id, verified passing when recorded)
- `tests/test_vet_containment.py::TestFetchCweForCve::test_expired_cache_entry_triggers_a_fresh_fetch` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 6 passed (from 6 evidence id(s))
- gates: 1 error(s), 6645 warning(s), 419 waived
- error-findings: TICK006@tickets.md
