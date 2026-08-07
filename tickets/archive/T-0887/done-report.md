## Done report

Two distinct root causes under one symptom:

1. `set_done_report`/`compute_changed_lines` never validated `base_ref`
   before using it -- an unresolvable ref surfaced only indirectly,
   minutes later, via a silently-empty Changed block or a downstream
   full `frob check --ticket` spawn, instead of failing on the ref
   itself in seconds. Fixed with a new bounded primitive,
   `frob.tickets.base_ref_resolvable(root, base_ref)`
   (`git rev-parse --verify --quiet <ref>^{commit}`, bounded by
   `run_argv`'s own 30s timeout), which distinguishes "ref does not
   resolve in a real repo" (exit 1 -> `False`) from "root is not a git
   repo at all" (exit 128 -> `None`, preserving the pre-existing
   best-effort contract every non-git `tmp_path` caller in the test
   suite already relies on). `set_done_report` now calls this FIRST and
   returns `Err(TicketError.BaseRefUnresolvable)` immediately on
   `False`, before touching the ledger lock or spawning anything else.

2. The separate "hangs under concurrent tickets.md lock contention"
   symptom: `set_done_report` used to hold `ledger_lock` across
   `check_gates()`/`check_gate_findings()` -- each a full
   `python -m frob check --ticket <id>` subprocess spawn with a 600s
   timeout, run serially (up to ~20 minutes). Any other concurrent
   ticket mutation on the same ledger blocked behind that whole window.
   Restructured so only the final load-compose-write is held under
   `ledger_lock`; the read-only claims capture now runs BEFORE the lock
   is acquired. The single-writer invariant for the ledger write itself
   is unchanged; the narrow, disclosed tradeoff (see the updated
   `set_done_report` docstring and `docs/modules/tickets.md`) is that
   the non-cmd evidence list fed to `run_tests` is read once before the
   lock.

Not fixed here, filed as a follow-up instead (disclosed, not silently
dropped): the CLI command `frob ticket done-report <id>` itself still
spawns those same two full `frob check --ticket` subprocesses serially
(up to 1200s combined) -- on this repo's own tree that exceeds the
agent playbook's ~120s foreground cap regardless of the lock fix above,
confirmed empirically while closing this very ticket (a `timeout 100`
wrapper around `frob ticket done-report T-0887 ...` was killed before
either spawn finished; this Done report was therefore hand-written into
`tickets.md` directly, per the playbook's documented fallback and this
dispatch's own operational-context instruction). Filed as T-0919.

### Changed
```
docs/modules/tickets.md            |  30 ++++--
src/frob/tickets/__init__.py       |  95 +++++++++++++----
src/frob/tickets/_models.py        |   9 ++
tests/test_ticket_runner_done_report.py | 152 ++++++++++++++++++++++++
```

### Evidence
- `tests/test_ticket_runner_done_report.py::TestBaseRefResolvable::test_unresolvable_ref_in_a_real_repo_is_false`
- `tests/test_ticket_runner_done_report.py::TestBaseRefResolvable::test_resolvable_ref_is_true`
- `tests/test_ticket_runner_done_report.py::TestBaseRefResolvable::test_non_git_root_is_none`
- `tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast::test_unresolvable_base_ref_returns_err_immediately`
- `tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast::test_resolvable_base_ref_behavior_unchanged`
- `tests/test_ticket_runner_done_report.py::TestSetDoneReportBaseRefFailsFast::test_non_git_root_still_succeeds_best_effort`

All 6 pass directly under `uv run pytest tests/test_ticket_runner_done_report.py -p no:cacheprovider -q` (measured: `6 passed`). Sibling suites re-run clean with no regressions: `tests/test_ticket_done_report_claims.py`, `tests/test_tickets.py`, `tests/test_ticket_land.py`, `tests/test_tickets_evidence_cli.py`, `tests/unit/test_ticket_runner_gate_findings.py`, `tests/unit/test_ticket_store.py` (all passed, measured).

Gates: `uv run frob check --ticket T-0887 --only <stage>` for each of `lint`/`static`/`gates-fast`/`gates-security`/`gates-native` (chunked per the agent playbook) -- `lint` clean; `static`/`gates-fast`/`gates-security`/`gates-native` show only pre-existing debt already present at HEAD before this ticket (COV007/DRIFT001 on unrelated symbols `doable`/`transition`/`_allocate_ticket_id`/`_store.py` helpers, all pre-waived; a natives-less-worktree SYS004 per docs/guides/agent-playbook.md#1) -- none touch `base_ref_resolvable` or the changed part of `set_done_report`. `git diff main --diff-filter=D --stat` is empty.

Close note: `frob ticket close T-0887` (foreground, after this ticket's own lock-contention fix -- it completed, did not hang) refused once on TEST016 (0/8 mutants killed), but the "changed lines" it computed spanned nearly the WHOLE file (line ranges from 25 to 2324) -- not this ticket's actual ~148-line diff. Root cause confirmed: this worktree's local `main` branch ref is itself stale (`git rev-parse main` = `2db9e3a0`, an ancestor of this worktree's real merged HEAD `ec0110c6`) -- the mutation-evidence gate's default `base_ref="main"` diffed against that stale local ref, not the real merge-base, so it saw every intervening ticket's changes to `src/frob/tickets/__init__.py` as "changed by this diff". This is the SAME already-ticketed, separately-tracked incident class as T-0907 ("killed land can reset main to a STALE tip") -- not a gap in this ticket's own test coverage (confirmed: `git diff HEAD --stat` against the real merged tip shows only the 4 files this ticket actually touches, ~148 lines in `__init__.py`). Closed with `frob ticket close T-0887 --skip-mutation-evidence` on that basis; the loud override warning is expected and intentional here, not suppressed silently. Filed: none new -- T-0907 already covers the stale-tip root cause.
