---
id: T-2270
title: frob ticket evidence silently drops the Done report body when re-serializing
  ticket.md -- hit twice in one ticket, survived only because the agent noticed
state: done
kind: bug
origin: human
created: '2026-08-17'
priority: high
parent: null
tier: ticket
sprint: null
runs_last: false
scope:
- src/frob/tickets/_store.py
evidence_scope:
- tests/unit/test_ticket_store.py
scope_breadth_ack: false
scope_breadth_ack_reason: null
evidence:
- tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_keeps_done_report_split_out
- tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archived_ticket_keeps_done_report_split_out
- tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_prunes_removed_ticket
- tests/unit/test_ticket_store.py::TestV2DoneReport::test_write_then_read_back_byte_for_byte
designated_repro_test: tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_keeps_done_report_split_out
acceptance:
- text: Recording evidence on a ticket that HAS a Done report body preserves it byte-for-byte
    (fails today)
  evidence:
  - tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_keeps_done_report_split_out
  - tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archived_ticket_keeps_done_report_split_out
- text: 'MUST-STILL-PASS: a ticket with no report body still records evidence cleanly;
    set_done_report still replaces the body as today'
  evidence:
  - tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_prunes_removed_ticket
  - tests/unit/test_ticket_store.py::TestV2DoneReport::test_write_then_read_back_byte_for_byte
- text: Every ticket.md writer audited for the same round-trip loss; state which were
    checked and which were affected
  evidence:
  - tests/unit/test_ticket_store.py::TestWriteArchivedTicket::test_v2_write_archived_ticket_keeps_done_report_split_out
- text: Any writer that legitimately must drop the body says so loudly -- silence
    is the defect
  evidence:
  - tests/unit/test_ticket_store.py::TestV2WriteTicket::test_write_all_v2_keeps_done_report_split_out
threat: null
component: null
anchor: false
anchor_reason: null
land_commit: 209c1138eb9535035da177f8c9c6a60e16af54b8
---
# `frob ticket evidence` silently drops the Done report body when it re-serializes `ticket.md`

## Measured evidence (2026-08-17)

Reported unprompted by the implementer that landed T-2256:

> the ticket-store's evidence-write path re-serializes `ticket.md` and silently
> dropped my Done report body **twice**; I re-added it each time before the
> final land committed.

Twice, in one ticket, in one session. The Done report survived on main (132
lines) ONLY because the agent noticed and manually restored it both times. An
agent that did not check its own file after recording evidence would have
landed with the body gone -- and the land would have succeeded, because a
missing report body is not something any gate refuses.

The write path is under `src/frob/tickets/_store.py`, which already knows about
this content explicitly (`_find_done_report_heading`,
`_done_report_section_end`, `replace_done_report_section`, all imported at
:45-47) and serializes under the lock described at :204 ("`add_evidence`,
`set_done_report`, ... acquires this BEFORE its own"). So the machinery to
preserve the section exists and the evidence path is not using it correctly.

## Why this is worse than it looks

- **It is silent.** No warning, no refusal, no diff the agent is prompted to
  review. The only signal is the body being gone if you happen to look.
- **It destroys the one artifact that explains the work.** A Done report is the
  reviewable record of what was changed and why; the ledger keeps the state
  transition either way, so the loss is invisible in every status view.
- **It lands.** Nothing gates on report-body presence, so a dropped body is
  published permanently.
- **The recovery is manual and undocumented.** This agent knew to re-add it.
  Nothing told it to.

## Do NOT fix it this way

- **Do NOT make it a land-time gate ("refuse a land whose report body is
  empty").** That catches the symptom one step too late, punishes tickets that
  legitimately have no report yet, and leaves the data loss intact for every
  non-landing path.
- **Do NOT have the caller re-write the body after every evidence call.** That
  is the manual workaround this agent had to invent; pushing it onto callers
  guarantees the next one forgets.
- **Do NOT reconstruct the body by re-reading and string-splicing the file.**
  `_store.py` already has `replace_done_report_section` /
  `_find_done_report_heading` for exactly this. Use the existing structured
  path -- do not add a second, text-based one. Standing user directive:
  token/grammar, never lexical.
- **Do NOT fix only `add_evidence`.** Identify every writer that
  re-serializes `ticket.md` and confirm which of them round-trip the body.
  State the full list; if only one is broken, say so and prove it.

## Acceptance criteria

1. (MUST FAIL FIRST) Recording evidence on a ticket that HAS a Done report body
   preserves that body byte-for-byte. Fails today -- reproduce with the real
   shape: a ticket with a committed report, then
   `frob ticket evidence <id> <node> --accepts N`.
2. MUST-STILL-PASS CONTROLS: a ticket with NO report body still records
   evidence cleanly (no fabricated empty section), and `set_done_report`
   continues to replace the body as it does today.
3. Every `ticket.md` writer is audited for the same round-trip loss; state
   which were checked and which were affected.
4. If any writer legitimately must drop the body, it says so loudly rather
   than silently -- silence is the defect, not the rewrite.

## Scope note

`src/frob/tickets/_store.py` owns the serializer and already imports the
done-report section helpers. The evidence entry point may live elsewhere in
`src/frob/tickets/`; trace it rather than guessing from module names, and widen
scope with a measured reason if the real writer is a sibling.

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
