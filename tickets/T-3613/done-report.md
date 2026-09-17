## Done report

Made ENQUEUE the default agent land path (T-1444's queue/drain mechanics already existed, opt-in only).

_apply_land_default_queue (src/frob/app/ticket_runner/_land_cmd.py) runs before _land's mode dispatch and
promotes a bare 'frob ticket land <id> --worktree PATH' call to --queue when FROB_AGENT is set in the
environment (same var frob.app.check_runner/_verify already treat as agent-worktree detection) or
AppConfig.ticket_land_default == 'queue' ([tool.frob] land_default = "queue" in pyproject.toml, wired
through _config_external.py's existing CLI/pyproject merge). Any explicit --plan/--queue/--drain/--status/
--run-mutation-sweep flag or --dry-run always wins, checked first; verified with
tests/unit/test_land_default_queue.py::TestApplyLandDefaultQueue (6 cases: env promotes, config promotes,
neither keeps sync default, explicit flags/dry-run never redirected).

Added --status <id> (_land_status_cmd, AppConfig.ticket_land_status, parser flag in _progress.py) printing
the per-intent completion record via frob.render.Renderer (not a bare print, avoiding RENDER001).

Added per-intent completion records: _write_intent_record (src/frob/tickets/_land_queue.py) mirrors each
QueueEntry to .frob/land-queue/<ticket_id>.json on every transition (enqueue's initial write, drain_next's
pop-to-landing step, its landed/failed outcome step) -- a cheap single-file poll target, separate from the
shared lock-guarded land-queue.json. read_intent_record reads it back, exported through
frob/tickets/__init__.py.

Added drainer crash recovery: QueueEntry gained a pid field recorded at the pop-to-landing step
(os.getpid()); _reclaim_dead_landing_entries (called under _queue_lock before drain_next looks for the next
queued entry) resets any 'landing' entry back to 'queued' iff pid_alive_tristate(pid) is False (confirmed
dead) -- never on None/True, mirroring frob.tickets._land's own land.lock reclaim posture exactly. The
shared queue file itself needed no change to survive a crash (T-1345's existing write-whole-file-once
contract already covers that).

Docs: docs/modules/tickets-landing.md gained a new section "Merge queue as the default agent path, with
pollable completion records (T-3613)" (anchor
merge-queue-as-the-default-agent-path-with-pollable-completion-records-t-3613) covering all 3 mechanisms
plus what did NOT change; frob:doc directives added on enqueue/drain_next/read_intent_record/
_apply_land_default_queue/_land_status_cmd pointing at it.

Tests: 33 in tests/unit/test_land_queue.py (24 pre-existing + 9 new: TestDrainNext dead/live-pid reclaim
cases, TestIntentRecord x5), all passing serially (-p no:xdist) and under xdist; 9 new in
tests/unit/test_land_default_queue.py (new file, plain AppConfig/tmp_path unit tests, no git/subprocess
harness needed -- avoided tests/ticket_land_suite/'s heavier fixture-repo shape since none of this needed
real git plumbing). ruff check/format clean on every touched file.

frob check --only gates --files <9 touched files> <WT> (run twice; the first run's 7 real findings in my
files were all fixed before the second): COV002 on _land (frob:ticket T-3613 added) and from_args
(defensive frob:ticket T-3613 add, adjacent diff noise); ARCH001/LANDPARITY002 on drain_next (90 lines,
frob:waive ARCH001 added -- every new line threads into the SAME pop/run/record sequence, not a second
concern); RENDER001 on the --status print (switched to Renderer.for_stream, matching frob ack --list's own
precedent); SEC110 on the new FROB_AGENT read (frob:waive, same posture as check_runner's own FROB_AGENT
waiver). Second run: 0 unwaived errors remain in any of the 9 touched files -- every FAIL-gate error left
in the full 94-error run (down from 100) is either pre-existing on dev (config.py:56/88's
_pyproject_file_for_args, unrelated to this diff, confirmed via git show dev) or belongs to other tickets'
files entirely (lang/_project_detect.py DOC002, milestone deadlocks on unrelated T-45xx tickets, test dup
in other agents' new test files) -- none touch a file this ticket scoped.

Out of scope found, not fixed: the brief's amendment (c) via-list/ratchet-lock requirement did not apply --
the new test file (tests/unit/test_land_default_queue.py) uses only AppConfig/tmp_path/monkeypatch, no
exec/subprocess, staying under testsuite's ambient fs.read/fs.write grant (T-2503), so design/frob.strata
and docs/design/registry/capability-via-ratchet.lock.json (added to scope defensively, per the brief) were
left untouched -- nothing to change there.

'ticket work T-3613' hit the brief's documented KNOWN BUG (T-draft-0c976639) once during setup: the FIRST
worktree it created had no .git at all (git -C on it silently discovered the ROOT repo instead via upward
directory search) -- removed and re-ran per the brief's own recipe, second attempt created a proper
worktree branched cleanly from dev with no bug.

Also hit two ticket-ledger mirror races, both self-resolved: a killed 'frob ticket accept --criterion' call
had actually landed server-side before the kill, so retrying created 4 duplicate acceptance criteria
(cleaned via --remove); 3 of those --remove calls' worktree-local commits then failed to mirror onto main
(LandInProgress mid-wait), which a plain retry of the SAME failed --remove could not fix (already applied
locally, "index out of range" on retry) -- resolved by making one more worktree-side accept call (add-then-
remove a throwaway placeholder criterion) once the blocking land finished, which flushed all pending
unmirrored commits onto main in one shot; root and worktree now agree (4 clean criteria, all bound).

### Changed
```
 docs/modules/tickets-landing.md            |  86 ++++++++++++++++
 src/frob/_cli_parsers/_ticket/_progress.py |  16 +++
 src/frob/app/_config_external.py           |   4 +
 src/frob/app/config.py                     |  23 +++++
 src/frob/app/ticket_runner/_land_cmd.py    | 114 +++++++++++++++++++++-
 src/frob/tickets/__init__.py               |   2 +
 src/frob/tickets/_land_queue.py            | 151 ++++++++++++++++++++++++++++-
 tests/unit/test_land_default_queue.py      | 127 ++++++++++++++++++++++++
 tests/unit/test_land_queue.py              | 114 ++++++++++++++++++++++
 tickets/T-3613/ticket.md                   |  23 ++++-
 10 files changed, 649 insertions(+), 11 deletions(-)
```

### Evidence
- `tests/unit/test_land_default_queue.py::TestApplyLandDefaultQueue::test_frob_agent_env_promotes_to_queue` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_default_queue.py::TestLandStatusCmd::test_status_prints_queued_record` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestIntentRecord::test_enqueue_writes_a_readable_intent_record` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestDrainNext::test_dead_drainer_landing_entry_is_reclaimed_and_redrained` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestDrainNext::test_live_drainer_landing_entry_is_not_reclaimed` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_default_queue.py::TestApplyLandDefaultQueue::test_neither_signal_keeps_synchronous_default` (pytest node id, verified passing when recorded)
- `tests/unit/test_land_queue.py::TestEnqueue::test_enqueue_returns_queued_entry` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 7 passed (from 7 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)

### Acceptance amendments
- [8] remove: removed 'docs section and tests per acceptance criterion' (reason: duplicate from a killed-then-retried accept call; logan, 2026-09-16)
- [7] remove: removed "drainer crash recovery: the queue file survives, the next --drain picks up, a dead drainer's landing entry is reclaimed via pid liveness (reusing the existing land.lock reclaim logic's posture)" (reason: duplicate from a killed-then-retried accept call; logan, 2026-09-16)
- [6] remove: removed 'a per-intent completion record file under .frob/land-queue/<ticket>.json (state queued/landing/landed/failed, refusal text verbatim, commit sha) that agents poll cheaply, plus frob ticket land --status <id> printing it' (reason: duplicate from a killed-then-retried accept call; logan, 2026-09-16)
- [5] remove: removed 'frob ticket land <id> under FROB_AGENT (or [tool.frob] land_default="queue") ENQUEUES and returns in seconds with the intent recorded, and one drainer process does the serial work' (reason: duplicate from a killed-then-retried accept call; logan, 2026-09-16)
- [5] remove: removed 'placeholder-resync-trigger' (reason: remove resync-trigger placeholder criterion; logan, 2026-09-16)
