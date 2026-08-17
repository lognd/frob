## Done report

### Important correction to the originating report

The specific incident this ticket was filed from (T-2256's Done report
"disappearing" twice) was **not** data loss. Re-derived the exact sequence
from that session's own transcript and reproduced each step:

- The first apparent loss was a **self-inflicted heading defect**: the
  agent wrote `## Done report (resumed from a prior stalled agent)` as one
  heading line. `_find_done_report_heading`'s strict-heading match never
  matched that line, so `land`'s `_has_done_report` genuinely found no
  report -- correct behavior on malformed input, not silent loss.
- The second apparent loss, after a batch of `frob ticket evidence T-2256
  ... --accepts N` calls, was the agent checking only `ticket.md` and
  concluding the body was gone. It had correctly relocated to the sibling
  `tickets/T-2256/done-report.md` -- exactly what the v2 split is
  supposed to do, confirmed on main right now (`git show main:tickets/
  T-2256/done-report.md` is the full 132-line report). Reproduced this
  exact shape here (a ticket with a Done report embedded in `ticket.md`,
  then two consecutive `frob ticket evidence <id> <node> --accepts N`
  CLI calls) against a scratch repo and against the in-process
  `add_evidence` primitive: both round-trip byte-for-byte every time (see
  `/tmp/repro2270` session). `add_evidence`'s write path (`write_ticket`
  -> `_write_ticket_v2_mode`) was never broken.

Digging further to honor acceptance 3's "audit every writer" anyway (not
just the one path already proven sound) surfaced a **real, independently
confirmed defect** in two OTHER writers, unrelated to what triggered the
original alarm but a genuine instance of the same defect class the ticket
describes (a v2 writer that does not round-trip the Done report through
the section-split helpers).

### Acceptance 1 repro (real shape, on the ACTUAL defective writers)

A ticket with a committed Done report body (embedded in `ticket.md`, or
already split into a sibling `done-report.md`), then a call through
`write_all` or `write_archived_ticket`: the report was silently
re-embedded into `ticket.md` verbatim (duplicated across both files, the
v2 split invariant broken) instead of staying split out.

MUST-FAIL-FIRST confirmed: committed the two new regression tests alone
(`b01b1a195`, `_store.py` still unfixed) -- both failed
(`assert "Done report" not in ticket_text` -> `AssertionError`).
`--check-repro` against that commit: `FAILED_AT_PARENT` (see Evidence).
Applied the fix as a separate commit (`712ddfcf5`) -- both pass.

### Audit: every writer that re-serializes `ticket.md`, and the verdict

| Writer | Loads via merge-aware read? | Splits Done report before write? | Verdict |
|---|---|---|---|
| `write_ticket` -> `_write_ticket_v2_mode` | yes (`_load_one`/`load_all`, callers) | yes (`_split_done_report`, pre-existing) | SOUND |
| `set_done_report` -> `_store_done_report` | yes | yes (v2 branch writes report only to `done-report.md`, never `ticket.md`) | SOUND |
| `add_evidence` / `_append_evidence_and_write` | yes (`_load_one`) | via `write_ticket` above | SOUND (this is the path the originating report suspected; disproven) |
| `replace_evidence` (non-archived) | yes | via `write_ticket` above | SOUND |
| `record_failure_attempt`, `drop_ticket`, land's post-merge claims-recap rewrite (`_reporting.py`, `_land_verify.py`) | yes (`_load_one`) | via `write_ticket` above | SOUND |
| `write_archived_ticket` (used by `evidence --replace --archived`, the primitive T-2256 ran 8+ times against archived tickets) | yes (`load_archive` merges) | **NO** -- wrote `ticket.body` verbatim to the archive's `ticket.md` | **AFFECTED -- fixed here** |
| `write_all` (bulk rewrite: land's draft-id-reference-in-body rewrite runs this over the WHOLE active ledger on every land, `renumber_one`'s bulk id rewrite, any other wholesale-replace caller) | yes (`load_all` merges) | **NO** -- wrote each `ticket.body` verbatim to `ticket.md` | **AFFECTED -- fixed here** |
| `write_archive` -> `_write_archive_v2` | -- | delegates to `write_archived_ticket` per-ticket | inherited the same defect, fixed by the same change |
| `_parse_ticket_file` direct reads (`_orphaned_new_ticket_dir_candidates`) | n/a, read-only, never writes `ticket.md` | n/a | not applicable |

Two writers affected: `write_archived_ticket` (and `write_archive`, which
calls it per-ticket) and `_write_all_v2`. Both now run `_split_done_report`
-- the SAME helper `_write_ticket_v2_mode` already used, no second
text-based path -- before writing `ticket.md`, and write/refresh the
sibling `done-report.md` when a section was found, exactly mirroring
`_write_ticket_v2_mode`'s existing shape.

Practical impact of the pre-fix behavior: not literal data destruction
(nothing was ever deleted), but a silent, undocumented violation of the v2
design's own "ticket.md never carries the report" invariant, hit on EVERY
land (the draft-id-reference rewrite scans and rewrites the whole active
ledger through `write_all` every time) and on every `--replace --archived`
call. A ticket.md and done-report.md that silently diverge after this is
a real (if slower-burning) risk this closes off.

### Acceptance 2 (MUST-STILL-PASS)

- `test_write_all_v2_prunes_removed_ticket` (pre-existing, unmodified):
  a ticket with NO report body (`_ticket()`'s default `"## Description\n
  something\n"`) still writes/prunes cleanly through `write_all` -- no
  fabricated empty Done report section (`_split_done_report` returns
  `(body, None)`, and both fixed writers skip the `done-report.md` write
  entirely when `report_text is None`, same guard `_write_ticket_v2_mode`
  already used).
- `test_write_then_read_back_byte_for_byte` (pre-existing, unmodified):
  `set_done_report` still replaces the body exactly as before -- untouched
  by this change (it writes through `_store_done_report`, not through
  either fixed writer).

### Acceptance 4 (loud disclosure)

Not applicable in the end: neither fixed writer has a case where it must
legitimately drop the body -- both now preserve it in every case (report
present or absent). No writer audited above needed a "drops it, loudly"
branch; where a report is absent, `report_text is None` and the writer
correctly does nothing to `done-report.md`, which is not a drop (there is
nothing to drop).

### Changed
```
src/frob/tickets/_store.py      | 55 +++++++++++++++++++++++++++++++++-----
tests/unit/test_ticket_store.py | 81 ++++++++++++++++++++++++++++++++++++++++++++
```

### Filed
None.

### Gates
`frob check --ticket T-2270 --only static` and `--only lint` clean against
the touched files (`src/frob/tickets/_store.py`,
`tests/unit/test_ticket_store.py`); full suite of `tests/unit/
test_ticket_store.py`, `tests/test_tickets.py`, `tests/test_tickets_
migration.py`, `tests/test_tickets_evidence_cli.py` (310 tests) green.
`tests/test_ticket_land.py -k "draft or renumber or archive"` has 12-13
pre-existing failures in this environment, identical before and after this
change (nested-worktree fixtures spinning up a second `pytest --collect-
only` with no natives built inside it, `returncode=5` "no tests ran" --
the documented worktree-natives-artifact class, not a regression from this
change).
