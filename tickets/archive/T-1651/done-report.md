## Done report

Ranked all 51 remaining LARGE001 files by edit frequency (`git log --format=%H --name-only -400 -- src/frob`, occurrence count per path), not raw size, per this ticket's own instruction -- edit-frequency and line-count order disagree substantially (e.g. src/frob/gates/_waive.py: 34 edits/1564 lines outranks src/frob/tickets/_store.py: 25 edits/2230 lines; src/frob/app/config.py: 31 edits/859 lines outranks four larger, less-touched files). Top of the ranking:

1. src/frob/gates/__init__.py -- 79 edits, 7639 lines
2. src/frob/tickets/_land.py -- 36 edits, 2820 lines
3. src/frob/app/ticket_runner/_land_cmd.py -- 35 edits, 2556 lines
4. src/frob/gates/_waive.py -- 34 edits, 1564 lines
5. src/frob/app/config.py -- 31 edits, 859 lines
6. src/frob/tickets/_store.py -- 25 edits, 2230 lines
7. src/frob/strata/_selfconform.py -- 23 edits, 1925 lines
8. src/frob/tickets/_models.py -- 22 edits, 2062 lines

Examined the top 8 in detail for an honest seam per this ticket's standard (a real responsibility/phase/consumer-set boundary, not a line-count cut).

WAIVED (no honest seam -- 3 files, all landed this round):

- src/frob/app/config.py: one pydantic AppConfig model plus its Subcommand
  enum and one validator helper. The whole file IS the app's single config
  surface; the genuinely separable parts (external-tool kwarg building,
  ARCH_DEFAULT_* constants) already live in _config_external.py/
  _config_meta.py. A line-count split would cut AppConfig's own field/
  validator block in half with nothing to hang the cut on.
- src/frob/gates/_waive.py: already the product of two prior extractions
  (T-1072, T-1081); its own docstring says what remains is deliberately
  "one cluster" (WAIVE001-005 directive validation plus the _match_waiver/
  _apply_waivers matching spine). ~710 of its 1564 lines are
  _KNOWN_GATE_RULES, a frob-zone-managed generated registry
  (frob.tickets._land_merge_zones, marker "known-gate-rules T-1002") read
  by three functions in this file -- moving it would require repointing
  that merge-zone's glob, which investigation during this ticket found
  ALREADY stale (it names src/frob/gates/__init__.py, not this file) --
  a pre-existing defect out of this ticket's scope, not something to
  compound by moving the marker again in the same change. Filed as a
  separate finding below rather than silently worked around.
- src/frob/tickets/_models.py: already carries a LARGE001-adjacent ARCH102
  waiver making exactly this argument (19 of 23 exports form one connected
  cluster around the Ticket/Evidence models and the scope-glob/done-report
  helpers over them). The LARGE001 waiver on this file cites and extends
  that existing reasoning rather than re-deriving it.

NOT split, NOT waived -- real seams found, left for the successor (each is
"its own project" per this ticket's own framing, same as T-1646's single
_fix_engine.py split):

- src/frob/gates/__init__.py (rank 1, 79 edits): the file's own section-
  divider comments (`# --- ... ---`) already group functions by gate
  family -- DRIFT/AFFECT/COV001 through COV007/etc, each family self-
  contained. This is the single highest-value target (matches the
  _fix_engine.py Tier-A-handler-family precedent exactly) but at 7639
  lines/63+ edit sites it is a multi-session project on its own; forcing
  it into this ticket's remaining budget risked a rushed, badly-seamed
  cut, which this ticket's brief explicitly says is worse than the
  warning.
- src/frob/tickets/_store.py (rank 6): its own docstring names two
  backends explicitly ("single" ledger vs legacy "dir"/v2 per-file
  layout) auto-detected by `_store_mode`. The v2-specific function
  cluster (v2_ticket_dir, v2_ticket_path, _v2_rename_source,
  _v2_path_lineage, v2_state_transitions, _write_archive_v2,
  migrate_v1_to_v2, etc -- roughly a third of the file) is a distinct
  consumer set (legacy-layout repos only) from the default single-ledger
  path. Real seam, not attempted this round for the same budget reason
  as __init__.py.
- src/frob/strata/_selfconform.py (rank 7): module docstring documents
  SYS100 through SYS107 as 8 distinct, independently-numbered rules.
  Same rule-family seam shape as gates/__init__.py; not attempted this
  round.
- src/frob/tickets/_land.py (rank 2) and src/frob/app/ticket_runner/
  _land_cmd.py (rank 3): _land.py's own docstring documents it has
  already been split three ways (T-1186, T-1334) and explicitly names
  what remains as one retained cluster (land lock/repair-marker
  machinery, the land()/_land_locked orchestrator, and pre-merge
  preflight validators) -- but those three named groups are themselves a
  plausible further seam (lock/marker machinery vs orchestration vs
  validation), unlike config.py/_waive.py/_models.py's honest "no seam"
  cases. Given this module's history of repeated re-splitting and its
  role as the single highest-risk landing path in the repo, a rushed cut
  here risked exactly the kind of arbitrary/dangerous split this ticket
  warns against; flagged for dedicated investigation, not attempted or
  waived this round.

FINDING filed separately, not fixed (out of scope): _land_merge_zones.py's
"known-gate-rules T-1002" union-zone glob names
`src/frob/gates/__init__.py` but the actual `_KNOWN_GATE_RULES` marker
pair lives in `src/frob/gates/_waive.py` -- the merge-zone auto-resolver
currently cannot match this hotspot at all. Pre-existing, found while
evaluating whether to move that registry; not touched here.

Successor ticket filed: T-1656 ("LARGE001 remainder: 48 files
after T-1651 (3 waived, seams found for 3, 2 flagged risky, 43
unexamined)") -- carries the ranked list, the 3 real-seam split
candidates, the 2 flagged-risky orchestrators, and the merge-zone glob
finding below.

Measured gate:LARGE (`frob check --only archgate`): 0 errors, 50 warnings,
4 waived (was 53 warnings per this ticket's own stated baseline; 3 new
waivers this round plus the pre-existing _land_git_ops.py LARGE001
waiver). 48 of the original 51 files remain, needing the same per-file
judgement call -- ranked above by edit frequency, with two real-seam
split candidates (gates/__init__.py, _store.py, _selfconform.py) and two
flagged-risky orchestrators (_land.py, _land_cmd.py) already scoped out
for whoever picks up the successor.

Verification: `python3 -c "import ast; ..."` parsed all three changed
files cleanly. `pytest tests/test_arch_gate.py -k Large` (3 passed,
0 failed) -- this ticket only added `frob:waive` comments, no behavioral
change, so the existing LARGE001-firing tests are the correct evidence
surface (TestArchGateLargeFile.test_large_file_fires_large001_warn,
test_test_file_exempt_from_large001, test_single_file_mode_matches_
directory_walk already cover the rule this ticket's waivers attach to;
no new test surface was created). `frob check --only archgate` itself
ran clean (0 errors) confirming the three new waivers parse and bind.

### Changed
```
 src/frob/app/config.py      |  10 ++
 src/frob/gates/_waive.py    |  18 ++++
 src/frob/tickets/_models.py |   6 ++
 tickets.md                  | 234 ++++++++++++++++++++++++++++++++++++++++++++
 4 files changed, 268 insertions(+)
```

### Evidence
(no evidence recorded)

### Captured claims
- tests: 3 passed (from 3 evidence id(s))
- gates: 0 error(s), 2555 warning(s), 848 waived
- error-findings: none (measured, zero errors)
