## Done report

T-0785 exposed a gate-integrity hole: .frob/dup.db verdicts survived dup
rule changes because the T-0517 fingerprint is package-version-only.
_dup_code_fingerprint (sha256 over sorted src/frob/dup/*.py name+bytes
with NUL separators) is folded into _check_fingerprint's stored value, so
any in-tree dup-code edit invalidates the cache wholesale through the
existing T-0517 path. Threshold edits need no coverage: verdicts cache
raw scores; config comparison happens at read time (reviewer-verified).
Cold rebuild reproduces the 117-group baseline unchanged.

### Changed
```
 src/frob/dup/_cache.py | 39 +++++++++++++++++++++++++++++++++++----
 tests/test_dup.py      | 48 ++++++++++++++++++++++++++++++++++++++++++++++++
 tickets.md             | 10 +++++++---
 3 files changed, 90 insertions(+), 7 deletions(-)
```

### Evidence
- `tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_dup_code_fingerprint_change_invalidates_cached_verdict` (pytest node id, verified passing when recorded)
- `tests/test_dup.py::TestVerdictCacheRulesFingerprintInvalidation::test_unchanged_dup_code_fingerprint_still_serves_cached_verdict` (pytest node id, verified passing when recorded)
