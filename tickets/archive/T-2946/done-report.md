## Done report

Re-measured `frob check --json --only tickets` at the start of this ticket:
the 8 TICK004/TICK007 findings match T-2946's own body exactly (T-0450,
T-0969, T-1273, T-1382, T-2391, T-2501, T-2573, T-2916). Per-finding
disposition below, one at a time -- not a mass close/drop.

T-0450 (TICK004, medium priority, 37d): investigated the "archived
directory but state=queued" anomaly the parent ticket flagged. Confirmed:
tickets/archive/T-0450/ticket.md carries state: queued -- a real ledger
invariant violation (archive's own contract is "move done/dropped tickets
into tickets-archive.md"). No CLI primitive can repair this: `frob ticket
drop T-0450` fails NotFound (drop only looks at the active ledger), and
there is no restore/unarchive command to move it back into tickets/ first.
Hand-editing the ticket directory is against this repo's own rule. Filed a
follow-up ticket for the missing restore primitive and for archive's write
path to refuse a non-terminal move going forward (T-2954, confirmed its
real post-land id). T-0450 itself is left queued-in-archive; no safe
action exists yet. DISPOSITION: cannot safely resolve this pass; follow-up
filed.

T-0969, T-1273 (TICK004, epics, 30d/28d): checked `frob ticket epic` on
both. T-0969 is 1/10 done with 8 more children QUEUED (not terminal),
including T-1273 itself, T-1953, T-2368/2370/2371/2376-2379 -- genuinely
being actively decomposed and worked, exactly as TICK004's own message
already says. T-1273 similarly has a queued (non-terminal) child T-1953.
DISPOSITION: no change. TICK004 is correctly describing real, live work,
not queue rot -- re-prioritizing or dropping either would be wrong.

T-1382 (TICK004, high priority, 25d, "Decouple frob from the Makefile"):
this one needed the deepest check. `frob ticket epic T-1382` reports 3/3
(100%) done via one child, T-2384, which itself has two done grandchildren
(T-2891, T-2892). That LOOKS like grounds to close per T-2372's own
"epic whose descendant tree is fully terminal" pattern -- but reading
T-2384's actual title and body ("frob's enforcement surface is hardcoded
to this repo's layout and sync-skills is not multi-repo safe" -- the
PORT001/src-frob-hardcoding work) shows it has NOTHING to do with Makefile
decoupling. T-1382's own body (still present, unedited) describes a
5-leaf decomposition -- frob coverage in Python, frob build/natives, a
21-call-site Makefile audit, a path/shell portability sweep, and a docs
rewrite -- and its 3 acceptance criteria are all still UNBOUND (zero
evidence). T-2384 is a PARENT MISLINK: some prior ticket-filing attached
an unrelated ticket's id as T-1382's child, which makes the epic falsely
read as "100% done" to any purely-structural check (a real ledger-quality
bug, separate from TICK004 itself, which correctly reported real rot
here). Did NOT touch T-2384's parent field myself -- it is a DONE, closed
ticket outside this ticket's declared scope, and reassigning it correctly
needs more investigation into where it truly belongs than this pass did;
documenting the mislink here is the honest, safe stopping point.
DISPOSITION: no change to T-1382's state/priority -- it is real,
unstarted, high-priority work per a standing 2026-08-01 user directive,
correctly rotting. Closing it (the surface-level "all children done"
reading) would have been wrong.

T-2391 (TICK004, high priority, 8d, "a zero-findings gate result is
ambiguous"): read the full body. This is the "silent zero is the
dominant bug class" epic -- six independently measured incidents from
this repo's own history back its acceptance criteria, and it matches an
explicit standing user doctrine (zero must fail loudly). Not decomposed
yet, but not abandoned or low-value either. DISPOSITION: no change --
genuinely valuable, awaiting decomposition (fleet_status's own "NEEDS
DECOMPOSITION" bucket agrees), not a reprioritize/drop candidate.

T-2501, T-2573 (TICK004, high priority, 8d each, both tier=epic with ZERO
children -- "Declared provenance" and "Milestone sequencing"): both are
real design epics from a 2026-08-18 design review, un-decomposed and
untouched since filing (confirmed via `git log -- tickets/T-2501/`
/`tickets/T-2573/`: only mass ledger-merge commits touch them, no
substantive edits). Also noted: a separate script (scripts/
fleet_status.py, not TICK004 itself) lists these under "NEEDS CLOSE ...
every child ticket is terminal", which is vacuously true over an EMPTY
child set (0/0 done reads as 100%) -- a real precision gap in that
script's heuristic, worth its own follow-up, but scripts/fleet_status.py
is outside this ticket's declared scope so it is disclosed here rather
than touched. DISPOSITION: no change -- 8 days for an unstarted design
epic is not yet clear abandonment, and unilaterally dropping real design
work this session did not author or fully evaluate would be the "mass-
drop to shrink a number" move the parent ticket explicitly forbids. Left
for an owner decision.

T-2916 (TICK007, critical priority, 24h, "frob is Linux-only in
practice"): filed yesterday, unleased, no body beyond the title, but
CRITICAL severity and a real, specific, credible claim (locks no-op,
orphan reaping disabled on non-Linux). TICK007's own two remedies are
"dispatch it or re-prioritize it" -- downgrading a real critical
portability bug just to burn a WARN-tier meta-gate to zero would be
exactly the wrong kind of number-chasing this ticket exists to prevent.
DISPOSITION: no change -- left critical and queued for the next dispatch
wave; not something this triage pass should silently deprioritize.

Re-measured `frob check --json --only tickets` after all of the above:
TICK004 still reports all 7 (T-0450, T-0969, T-1273, T-1382, T-2391,
T-2501, T-2573). TICK007 still reports T-2916. Neither burned to zero --
every remaining finding above got a real, documented, non-mechanical
disposition rather than a forced zero, per this ticket's own explicit
instruction not to mass-close/mass-drop.
Promotion to ERROR is therefore correctly NOT done this pass (T-2372's
own rule: never promote before the count is genuinely zero).

Changed:
- tickets/T-2954/ticket.md (new ticket: archive-restore primitive
  gap, filed as a follow-up from the T-0450 investigation)

Filed: T-2954 (frob ticket archive can strand a non-terminal
ticket with no restore path).

Gates: `frob check --ticket T-2946` clean for every file in this ticket's
scope (tickets/T-0969, T-1273, T-1382, T-2391, T-2501, T-2573, T-2916,
archive/T-0450, T-2954 -- zero errors against any of them);
repo-wide gate-summary carries pre-existing, unrelated findings (COV004
stale attachment shas, DOC005/006 drift, SYS003, LARGE001, frob-cycle --
none touch this ticket's files). `frob check --json --only tickets`
re-measured before and after: the 7 TICK004 + 1 TICK007 findings named in
T-2946's own body are unchanged in count (each received a real
disposition, documented above, rather than a mechanical burn to zero).

### Changed
```
 tickets/T-2946/ticket.md           | 78 ++++++++++++++++++++++++++++++++++++-
 tickets/T-2954/ticket.md | 80 ++++++++++++++++++++++++++++++++++++++
 2 files changed, 156 insertions(+), 2 deletions(-)
```

### Evidence
- `tests/integration/test_interfaces.py::TestInterfaces::test_main_cli_dispatches` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 1 passed (from 1 evidence id(s))
- gates: 25 error(s), 471 warning(s), 854 waived
- error-findings: ARCH103@src/frob/tickets/_new_renumber.py, COV001@scripts/branch_stranded_work_analysis.py, COV004@tickets/T-2195/attachments/01-widened-to-critical-relative-imports-fail-too-zero-cross-file-resolution-repo-wide-t-2156-re-verification-needed.md, COV004@tickets/T-2195/attachments/02-independently-confirmed-frob-cycle-vacuous-on-src-layout-widened-acceptance-criteria-and-fix-guidance-no-src-lexical-special-case.md, COV004@tickets/T-2195/attachments/03-three-confirmed-vacuous-consumers-attribution-cycle-arch-layering-per-consumer-must-still-pass-acceptance-criteria.md, COV004@tickets/T-2197/attachments/01-self-referential-confirmation-two-folded-in-incidents-silent-downstream-success-t-2196-measured-then-discarded-verdict-cross-referenced.md, COV004@tickets/T-2244/attachments/01-t-2244-audit-safe-to-repoint-split-test-typecheck-safe-now-lint-blocked-by-newly-found-t-2387-not-t-2359-format-lint-fix-blocked-by-both-test-fast-stays-raw.md, COV004@tickets/T-2328/attachments/01-second-live-reproduction-t-2329-s-own-land-root-cause-narrowing.md, COV004@tickets/T-2328/attachments/02-third-reproduction-t-2323-confirmed-workaround-pre-commit-the-file-yourself-before-land.md, COV004@tickets/T-2328/attachments/03-clarification-titled-work-loss-defect-remains-open-carried-by-t-2351.txt, COV004@tickets/T-2350/attachments/01-diagnosis-timing-visibility-race-not-identity-matching-both-candidate-fix-files-leased-by-t-2351-no-edit-attempted.md, COV004@tickets/T-2543/attachments/01-class-a-options-and-measured-costs-t-2377-survey.md, COV007@scripts/branch_stranded_work_analysis.py, CYCLE001@src/frob/__init__.py, DOC002@src/frob/tickets/_leases.py, DOC005@README.md, DOC006@docs/guides/coordinator-scripts.md, DOC006@docs/modules/gates.md, DOC006@tickets/T-2886/ticket.md, DOC008@docs/commands/check.md, LARGE001@src/frob/stats/_agentic.py, SELFAUDIT001@design, SYS003@scripts/branch_stranded_work_analysis.py, TEST001@scripts/branch_stranded_work_analysis.py, TICK004@tickets.md
