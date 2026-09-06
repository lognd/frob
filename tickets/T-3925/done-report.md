## Done report

COORDINATOR'S BRIEFING GAP CLOSED: T-3847 wired frob.testing.LANGUAGE_
COLLECTORS into VERIFICATION only. The consumer report (F-134, an F-039
recurrence) measured that vitest ids were STILL rejected by `frob ticket
evidence`/`close`, because three real BINDING/RESOLUTION call sites never
consulted the registry at all:

  - `_apply_evidence` (src/frob/app/ticket_runner/_verify.py) builds the
    `collected` set handed to `add_evidence`'s `collected=` param, which
    feeds `_check_evidence_resolution` -> `matches_collected`. It built
    `collected_ids = python_ids | rust_ids` -- a vitest id was never in
    that set, so it was rejected as `Err(UnknownEvidence)` BEFORE
    verification (the part T-3847 fixed) was ever reached.
  - `_apply_replace_evidence` (same file) had the identical pattern
    feeding `replace_evidence`.
  - `_land_collected_fn` (src/frob/app/ticket_runner/_land_cmd.py) had
    the identical pattern feeding `frob.tickets._land_verify`'s D-05
    post-merge resolution re-check -- a vitest id would have resolved
    pre-merge and then been reported "no longer resolves post-merge",
    refusing an otherwise-good land.

FIX: added `_other_language_collected_ids(root, *, exclude)` (src/frob/
app/ticket_runner/_verify.py) -- the union of every `LANGUAGE_COLLECTORS`
entry NOT already collected some other way, best-effort per language (a
collector `Err` logs and contributes nothing, never blocks binding, same
posture `_verify_unbucketed_ids` already established). Wired into all
three call sites by unioning it into their existing `collected_ids`.

`matches_collected` itself is UNCHANGED, per the coordinator's explicit
directive (D-11: gates and tickets deliberately share one resolver so
they cannot desync) -- the fix is entirely in how the collected SET is
BUILT before it reaches that shared matcher, never inside the matcher.

RE-CHECKED `collected=None` (src/frob/tickets/_evidence.py:1395, item 3):
left AS-IS, no code change -- and now demonstrably the right call. Audited
every real `add_evidence`/`replace_evidence` call site in the repo:
  - `_apply_evidence`/`_apply_replace_evidence`/`_land_collected_fn`:
    all three now supply a concrete multi-language set (never `None`) --
    fixed by this ticket.
  - `src/frob/refactor/_transaction.py::_route_evidence_rebinds_through_
    replace_evidence`: calls `replace_evidence` with NO `collected` arg
    (defaults to `None`) DELIBERATELY -- it is rebinding an evidence id
    to a symbol a rename refactor is itself creating, which by
    definition may not exist in any collected set yet at refactor time.
    Confirmed this is an intentional, unrelated use, not a language-
    collector gap.
  So `collected=None`'s warn-only posture is now cleanly decoupled from
  "is every language's collector wired" (that question is closed by this
  ticket) and reserved for its one remaining genuine caller.

THE MATRIX, EXTENDED to all three paths (collect / BIND / verify) per the
coordinator's request -- collect and verify were T-3847's; BIND is new:

| Language | collects? | BINDS? (add/replace/land-D05) | verifies? |
|----------|-----------|--------------------------------|-----------|
| python   | yes       | yes (always was)               | yes |
| rust     | yes       | yes (always was)                | yes |
| cpp      | yes       | yes (NEW, this ticket)          | yes (T-3847) |
| kotlin   | yes       | yes (NEW, this ticket)          | yes (T-3847) |
| ts (vitest) | yes    | yes (NEW, this ticket)          | yes (T-3847) |
| ts (jest)   | no     | no                               | no (T-3921) |
| csharp/go   | no     | no                               | no (no walker/collector) |

## Done report

Changed:
src/frob/app/ticket_runner/_verify.py::_other_language_collected_ids
src/frob/app/ticket_runner/_verify.py::_apply_evidence (collected_ids union)
src/frob/app/ticket_runner/_verify.py::_apply_replace_evidence (collected_ids union)
src/frob/app/ticket_runner/_land_cmd.py::_land_collected_fn
src/frob/app/ticket_runner/__init__.py (re-export)

Evidence:
tests/test_tickets_evidence_cli.py::TestTicketEvidenceVitestOracle::test_vitest_node_id_from_fake_collect_ts_resolves
tests/test_tickets_evidence_cli.py::TestTicketEvidenceVitestOracle::test_non_python_rust_collection_failure_degrades_to_others
tests/unit/test_verify_language_buckets.py::TestOtherLanguageCollectedIds::test_unions_every_non_excluded_registered_language
tests/unit/test_verify_language_buckets.py::TestOtherLanguageCollectedIds::test_excluded_languages_are_never_collected
tests/unit/test_verify_language_buckets.py::TestOtherLanguageCollectedIds::test_collector_error_degrades_to_empty_not_raise

Filed: none (T-3921 already covers jest, filed under T-3847)

Gates: frob check --ticket T-3925 -- ARCH001/FMT001/LANDPARITY002/AFFECT001/
WIRE001/SCOPE001/PRE001 clean. Remaining findings are pre-existing and
unrelated to this diff: 40 SCOPE002 findings on other pre-existing symbols
co-resident in the large shared files this ticket touched
(src/frob/app/ticket_runner/_land_cmd.py, _verify.py, __init__.py) whose
own doc/test targets live outside this ticket's scope -- the same
unwaivable-on-a-giant-shared-file gap T-3903/T-3902 already document (not
filing a duplicate). gate:DEPR (fmt_runner.py) and gate:DRIFT
(verify/_worker.py) are pre-existing and untouched by this diff.

### Changed
```
 src/frob/app/ticket_runner/__init__.py     |  2 +
 src/frob/app/ticket_runner/_land_cmd.py    | 19 ++++++-
 src/frob/app/ticket_runner/_verify.py      | 70 ++++++++++++++++++++++-
 tests/test_tickets_evidence_cli.py         | 87 +++++++++++++++++++++++++++++
 tests/unit/test_verify_language_buckets.py | 90 ++++++++++++++++++++++++++++++
 tickets/T-3925/ticket.md                   | 28 +++++++++-
 6 files changed, 291 insertions(+), 5 deletions(-)
```

### Evidence
- `tests/test_tickets_evidence_cli.py::TestTicketEvidenceVitestOracle::test_vitest_node_id_from_fake_collect_ts_resolves` (pytest node id, verified passing when recorded)
- `tests/test_tickets_evidence_cli.py::TestTicketEvidenceVitestOracle::test_non_python_rust_collection_failure_degrades_to_others` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_language_buckets.py::TestOtherLanguageCollectedIds::test_unions_every_non_excluded_registered_language` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_language_buckets.py::TestOtherLanguageCollectedIds::test_excluded_languages_are_never_collected` (pytest node id, verified passing when recorded)
- `tests/unit/test_verify_language_buckets.py::TestOtherLanguageCollectedIds::test_collector_error_degrades_to_empty_not_raise` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 5 passed (from 5 evidence id(s))
- gates: 3 error(s), 4382 warning(s), 934 waived
- error-findings: DEPR003@src/frob/app/fmt_runner.py, DRIFT001@src/frob/verify/_worker.py, SCOPE002@tickets.md
