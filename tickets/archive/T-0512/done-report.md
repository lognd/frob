## Done report

(See prior Done report content below for the full design rationale --
this update only covers the mid-ticket main merge.)

Merged main mid-ticket (main had advanced with T-0433/T-0358/T-0412/
T-0456/T-0507 landing since this worktree's warm-up, bumping frob to
0.56.0). Resolved conflicts in pyproject.toml/.frob-release.json/uv.lock/
CHANGELOG.md by taking main's content and re-numbering this change's
version bump to the next free number, 0.57.0 (was 0.54.0, now stale).
Moved the T-0510/T-0511/T-0512 CHANGELOG entries into the correct
0.57.0 section (they had briefly landed in a duplicate "[0.57.0
continued]" header during conflict resolution -- consolidated). Ran
`make core`, `uv run frob release stamp`, re-swept, re-ran the full
gate check and the strata/audit/litmus test suites -- all still green
after the merge. `git diff main --diff-filter=D --stat` empty (no
unintended deletions from the merge).

### Changed
```
 .frob-release.json                           |   4 +-
 CHANGELOG.md                                 |  33 +++
 docs/design/registry/weaknesses.yaml         |  25 +-
 docs/design/security-corpus.md               |  45 ++--
 docs/guides/extending/benign-capabilities.md |  36 ++-
 docs/strata/threat.md                        |  62 +++++
 pyproject.toml                               |   2 +-
 src/frob/app/sys_runner.py                   |  22 +-
 src/frob/strata/_audit.py                    |  91 ++++++-
 src/frob/strata/_cve_fingerprint.py          | 107 ++++++--
 src/frob/strata/_threat.py                   | 197 ++++++++++++--
 tests/unit/strata/test_audit.py              |  40 +++
 tests/unit/strata/test_cve_fingerprint.py    |  77 ++++++
 tests/unit/strata/test_threat.py             | 155 ++++++++++-
 tickets.md                                   | 384 ++++++++++++++++++++++++++-
 uv.lock                                      |   2 +-
 16 files changed, 1180 insertions(+), 102 deletions(-)
```

### Evidence
- `tests/unit/strata/test_audit.py::TestExhaustiveness::test_default_run_discloses_narrower_than_baseline` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_audit.py::TestExhaustiveness::test_explicit_full_security_views_clears_the_disclosure` (pytest node id, verified passing when recorded)
- `tests/unit/strata/test_audit.py::TestGroupGaps::test_group_gaps_by_view` (pytest node id, verified passing when recorded)
