## Done report

Reviewer round 1 REJECTed on one blocking finding: PID-reuse false-liveness. The traced sequence was real -- a writer crashes leaving journal(pid=100) plus mutant bytes on disk, PID 100 gets recycled by an unrelated process, the original signal-0-only _is_stale probe says live forever, list_stale_journals excludes it, DoctorReport.mutate_journals stays empty, and frob doctor reports CLEAN while a real source file sits in mutant form -- with the only accidental protection being write_journal's own content-hash collision refusal on the next legitimate run, not anything by design. Zero disclosure existed anywhere for this gap.

Fix taken: the reviewer's preferred option (b), a start-time disambiguator. Every journal now also records the writer's /proc/<pid>/stat field-22 starttime (clock ticks since boot) at write time via a new _pid_starttime helper, which splits on the LAST ")" in the stat line (comm can itself contain spaces/parens) and reads offset 19 of the remainder. _is_stale now returns True (restorable) when the PID is dead, OR when the PID is alive but its CURRENT starttime no longer matches the journal's recorded one -- exactly the PID-recycled signature, since the kernel's starttime is stable for a PID's whole lifetime and different for whatever process later reuses the number. This is verified directly by a new test, test_recycled_pid_with_mismatched_starttime_is_treated_stale, which simulates recycling with a genuinely live PID (this test process itself) and a deliberately mismatched recorded starttime -- no actual PID recycling needed to exercise the code path -- and confirms both list_stale_journals and restore_stale_journals correctly treat it as stale and restore it byte-exact.

The route was Linux-only /proc parsing rather than falling back to option (a) outright, because it worked cleanly on the first attempt (no unusual edge cases beyond the comm-parenthesis split, which is a known, well-documented quirk of /proc/pid/stat). The residual from option (a) is still disclosed, layered on top rather than replacing it: write_journal accepts starttime=None explicitly (distinguished from "not passed, compute it" via a private _Unset sentinel type) whenever /proc could not be read at write time (non-Linux, a sandboxed environment), and _is_stale falls back to PID-only liveness in exactly that case. This residual is now disclosed in four places, all using the reviewer's suggested remedy phrasing verbatim: the module docstring of src/frob/mutate/_journal.py (a new PID-REUSE design-note paragraph), docs/modules/mutate.md (a new "PID reuse: why is the writer alive is not enough" section), src/frob/doctor.py's module docstring (a new T-0857 PID-reuse paragraph appended to the existing T-0857 section), and docs/guides/install.md's doctor-side section (a new "Known residual (PID reuse without /proc)" callout). All four end with the exact phrasing: "if frob doctor stays clean but a target keeps refusing with JournalCollision, inspect .frob/mutate-backup/<hash>.json by hand -- the recorded PID may have been reused."

Non-blocking nit also fixed: write_journal's temp-file write now happens inside a try/finally that unlinks the temp path (missing_ok=True) regardless of outcome, so an IO error landing between the write and the os.replace rename no longer leaves a stray .tmpNNN file under .frob/mutate-backup/. Covered by a new test, test_write_journal_cleans_up_temp_file_on_replace_failure, which monkeypatches os.replace to raise mid-call and confirms no leftover temp file after (the underlying OSError itself still propagates -- write_journal does not silently swallow a real replace failure into a Result, only the temp-file cleanup is unconditional).

What changed since round 1: src/frob/mutate/_journal.py (new _pid_starttime helper, _Unset sentinel type, MutationJournalEntry.starttime field, _is_stale extended with the starttime comparison, write_journal accepts an optional starttime override for tests and wraps its temp-file write in try/finally); src/frob/doctor.py (module docstring extended with the PID-reuse disclosure paragraph); docs/modules/mutate.md (new PID-reuse section); docs/guides/install.md (new residual-disclosure callout); tests/test_mutate_journal.py (two new tests: the recycled-PID-simulation stale-detection test and the temp-file-cleanup test).

Evidence: 2 new node ids recorded (test_recycled_pid_with_mismatched_starttime_is_treated_stale, test_write_journal_cleans_up_temp_file_on_replace_failure), bringing the ticket total to 15. Full re-run of uv run pytest tests/test_mutate_journal.py tests/test_mutate.py tests/system/test_cli_doctor.py -p no:cacheprovider -q is green (50 tests, 0 failures) after the rework.

Gates: re-ran the full chunked --only loop (lint, static, gates-fast, gates-native, gates-security) scoped --ticket T-0857 after staging every changed file and re-running frob ticket sweep T-0857. All five groups are 0 errors. Two transient findings surfaced mid-rework and were fixed rather than waived: a ty invalid-assignment on the raw object() sentinel (replaced with a proper _Unset class so the type checker can narrow it via isinstance, no ignore comment needed) and a batch of FMT001 line-length findings on the new frob:tests/frob:doc directive lines, cleared by running frob fmt on the three touched files (canonical backslash-continuation wrapping, verified ruff/pytest still pass identically after).

Filed: none. Deviations: none -- this rework directly implements the reviewer's requested fix (option b) plus the requested residual disclosure and the non-blocking nit, with no additional scope taken.

### Changed
```
 docs/guides/install.md          |  47 ++++
 docs/modules/mutate.md          | 131 +++++++++++-
 src/frob/doctor.py              |  96 +++++++--
 src/frob/mutate/__init__.py     |  48 ++++-
 src/frob/mutate/_journal.py     | 461 ++++++++++++++++++++++++++++++++++++++++
 tests/system/test_cli_doctor.py |  65 ++++++
 tests/test_mutate_journal.py    | 293 +++++++++++++++++++++++++
 tickets.md                      |  99 ++++++++-
 8 files changed, 1220 insertions(+), 20 deletions(-)
```

### Evidence
- `tests/test_mutate_journal.py::test_write_journal_is_idempotent_for_same_content` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_write_journal_refuses_on_content_collision` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_remove_journal_after_restore` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_list_stale_journals_reports_without_restoring` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_restore_stale_journals_is_byte_exact_crlf` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_restore_stale_journals_after_simulated_crash` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_restore_and_list_skip_a_journal_owned_by_a_live_pid` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_run_mutations_restores_stale_journal_from_prior_crash` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_run_mutations_journals_and_cleans_up_on_success` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_run_mutations_journal_collision_aborts_with_journal_collision_error` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_healthy_with_no_mutate_journals` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_unhealthy_with_stale_mutate_journal` (pytest node id, verified passing when recorded)
- `tests/system/test_cli_doctor.py::TestDoctorMutateJournal::test_run_diagnosis_ignores_journal_owned_by_live_pid` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_recycled_pid_with_mismatched_starttime_is_treated_stale` (pytest node id, verified passing when recorded)
- `tests/test_mutate_journal.py::test_write_journal_cleans_up_temp_file_on_replace_failure` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 15 passed (from 15 evidence id(s))
- gates: 0 error(s), 1006 warning(s), 220 waived
- error-findings: none (measured, zero errors)
