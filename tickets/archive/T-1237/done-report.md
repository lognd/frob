## Done report

Investigated the recipe's forensics-preservation shape directly: the
`coverage:` Makefile recipe writes junitxml under `.frob/last-coverage-
run.xml` / `.frob/last-coverage-rerun.xml` BEFORE either of its two
`frob clean -y` calls (Makefile:249,259) -- and both calls are bare `-y`
with no `--all`/`--deep`, i.e. SAFE/tier-1 only. Tier 1's own pattern set
(src/frob/clean/_rules.py's `_TIER1_PATTERNS`) never includes `.frob`
itself (that is tier 3, `_TIER3_PATTERNS`, only reachable via `--deep`) --
so the junitxml files this ticket is about were already structurally safe
from the recipe's own clean call. No test previously locked this in,
though: a future edit that escalated either `frob clean` invocation to
`--all`/`--deep`, or that added `.frob` (or a subpattern of it) to the
tier-1 allowlist, would silently destroy the forensics with nothing
catching it before a real incident.

Added two tests:
- tests/test_clean.py::test_safe_tier_clean_preserves_frob_junitxml_forensics
  -- direct proof that a SAFE-tier `clean()` call preserves `.frob/*.xml`
  fixtures while still removing sibling `.coverage.*` fragments (tier 1's
  own legitimate job).
- tests/test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier
  -- reads the REAL Makefile `coverage:` recipe text and asserts every
  `frob clean` invocation inside it omits `--all`/`--deep`, so a future
  edit that widens the tier is caught here rather than discovered as
  missing forensics.

On the acceptance's second half (the "34->27 fragment loss, unresolved"
investigation): traced the recipe's OWN command sequence and found no path
where a `.coverage.*` fragment is deleted mid-run. The one `rm -f .coverage
.coverage.*` in the recipe runs at the very TOP, before pytest starts
(clearing STALE files from a prior separate invocation, not this run's
fragments); the recipe's own `frob clean -y` calls run only AFTER `coverage
combine`/`coverage xml` have already consumed every fragment from this
run. This matches T-1353's already-landed finding (Makefile:150-176, same
file) that fragment loss traces to xdist workers going "node down" under
CPU/memory oversubscription (a crash bypasses coverage's own SIGTERM-
triggered flush) -- not to `frob clean` or any other in-recipe deletion.
I found no additional code path in src/frob/clean/** that could explain a
mid-run loss beyond what T-1353 already fixed (COVERAGE_WORKERS capping +
--timeout-method=signal). Not forcing a second fix for a root cause that
does not reproduce against the current recipe text; if a future run still
shows fragment loss with COVERAGE_WORKERS respected and no node-down in
the log, that would need a fresh ticket with its own repro, not a
speculative change here.

### Changed
```
 tests/test_clean.py                  | 55 ++++++++++++++++++++
 tests/unit/test_makefile_coverage.py | 99 ++++++++++++++++++++++++++++++++++++
 tickets.md                           | 86 ++++++++++++++++++++++++++++---
 3 files changed, 234 insertions(+), 6 deletions(-)
```

### Evidence
- `tests/test_clean.py::test_safe_tier_clean_preserves_frob_junitxml_forensics` (pytest node id, verified passing when recorded)
- `tests/test_clean.py::test_makefile_coverage_recipe_never_escalates_clean_tier` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 2 passed (from 2 evidence id(s))
- gates: 1 error(s), 7664 warning(s), 696 waived
- error-findings: SELFAUDIT001@design
