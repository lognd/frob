## Done report

NEGEXIST001 burn-down for T-3519. Measured 2026-08-30 via
uv run frob check --only docblocks --json, filtering severity=warning:

Before: 16 findings across the 10 in-scope files (18 total minus
docs/modules/gates.md and docs/modules/lang.md, dropped from scope at
start-time -- both collide with T-3492's in-progress lease).
After: 0 in-scope findings. gate:NEGEXIST: 0 errors, 2 warnings (both
out-of-scope), 0 waived.

Per docs/modules/gates.md's own NEGEXIST001 section (a phrase-only
heuristic -- "a false negative here just means an unrelated claim goes
unflagged, never a false failure" -- with no semantic understanding of
"deferred capability" vs "permanent design fact"), each of the 16
findings reviewed individually:

- 5 real deferred-capability claims, bound to their tracking ticket:
  sys.md capacity --at DATE and reliability.md's own growth-rate-grammar
  gap both bound to T-3527 (filed fresh -- T-2016, done, only produced
  the design, never the implementation, and no ticket tracked that
  gap); macos-portability.md Bucket C bound to T-3528 (filed fresh --
  T-3500, done, closed against the same bucket but its own Done report
  shows it only fixed a scope typo and reran the Linux path, no darwin
  branch was ever added); entity_architecture.md's cross-file
  resolution bound to T-3529 (filed fresh -- T-3006, the epic that
  built the first slice, never filed a follow-up for this).
- 4 STALE claims, fixed at the doc (not just bound) after verifying the
  cited ticket against the actual shipped code: sys.md's `threats`
  residue bullet (T-1925, done -- confirmed `_run_threats`/
  `threat_violations_for_boundary` wired in sys_runner.py),
  tickets-landing.md's scope-demote CLI flag (T-1975, done -- confirmed
  `--demote-to-evidence-only` in _cli_parsers/_ticket/_metadata.py) and
  BUG003 wiring (T-2215, done -- confirmed `must_still_pass_violations`
  wired into _land.py/_close_cmd.py), tickets-verify-sweep.md's CLI
  visibility bullet (T-1697, done -- confirmed `status`/`explain`
  subcommands in _cli_parsers/_verify.py).
- 6 permanent-fact claims, reworded to drop the trigger phrase (these
  do not describe a future capability any ticket will build):
  process.md (SIGKILL absent on Windows), coordinator-scripts.md x2
  (a ticket absent from main; the --ticket flag absent from land's
  argparse), testing.md (a worker-crash false positive), tickets-
  verify-sweep.md (a bisect miss), surface.md (a SYS003 wiring gap
  already closed, described in past tense).

Promoted: no. NEGEXIST001 is WARN-only by design (docs/modules/
gates.md's own posture, matching INV003/INV004's identical framing);
promoting to ERROR was not asked for, and the family is not at a
genuine repo-wide zero (2 out-of-scope files remain, leased by T-3492).

Filed: T-3527 (growth-rate grammar for frob sys capacity --at DATE),
T-3528 (macOS live-process detection fallback), T-3529 (cross-file
entity/architecture resolution for strata).

### Changed
```
 docs/commands/sys.md                 | 14 +++++++++-----
 docs/design/macos-portability.md     |  1 +
 docs/guides/coordinator-scripts.md   |  6 +++---
 docs/modules/process.md              |  2 +-
 docs/modules/testing.md              |  2 +-
 docs/modules/tickets-landing.md      | 22 +++++++++++-----------
 docs/modules/tickets-verify-sweep.md |  4 ++--
 docs/strata/entity_architecture.md   |  2 ++
 docs/strata/reliability.md           |  2 ++
 docs/strata/surface.md               |  4 ++--
 tickets/T-3519/ticket.md             |  3 +++
 11 files changed, 37 insertions(+), 25 deletions(-)
```

### Evidence
- `cmd:bash /tmp/claude-1000/-home-logan-projects-frob/f4d0128f-ef81-45f6-8336-64623fe5712f/scratchpad/check_negexist_zero.sh exit=0 sha256=bc8e34f9dd85` (cmd evidence, exit=0)

### Captured claims
- tests: 0 passed (from 0 evidence id(s))
- gates: 24 error(s), 4284 warning(s), 894 waived
- error-findings: ARCH102@src/frob/process/_lock.py, ARCH103@src/frob/tickets/_leases.py, COV001@src/frob/tickets/_land_queue.py, COV003@tests/unit/test_scaffold_project.py, DEPR006@frob-deprecated-baseline.lock.json, DOC001@docs/design/macos-portability.md, DOC007@src/frob/verify/_bisect.py, DOC007@tests/unit/test_process_lock.py, DRIFT001@src/frob/app/ticket_runner/_rapid_sweep.py, DRIFT001@src/frob/app/ticket_runner/_verify.py, DRIFT001@src/frob/process/_lock.py, DRIFT002@src/frob/verify/_bisect.py, DRIFT002@tests/unit/test_process_lock.py, DSL001@CHANGELOG.md, LARGE001@.claude/hooks/root-write-guard.py, LARGE001@src/frob/arch/_mayraise.py, OPAQUE001@src/frob/_cli_parsers/_ticket/_metadata.py, PII012@tests/test_ticket_leases.py, PRE001@tickets/T-3519, REF001@docs/design/macos-portability.md, REL001@src/frob/__init__.py, TICK004@tickets.md, WAIVE009@src/frob/arch/_normalized.py, WAIVE011@frob-ratchet.lock.json
