## Done report

Changed: docs/guides/agent-playbook.md (section 1 step 0, section 13
correction block replacing the "FEWER THAN 2 in flight" rule with the
wait_for_land_slot.py + FROB_LAND_DEADLINE_S procedure; the
merge-driver text at what is now line ~990 was already correct --
verified against .gitattributes and `git config --get
merge.frob-tickets.driver` returning nothing -- so no change was
needed there).

Evidence:
- `uv run python scripts/wait_for_land_slot.py --max-in-flight 1 --timeout 10 --fleet-status-cmd false` -> exit 2 (EXIT_MEASUREMENT_FAILED), observed live.
- `uv run python scripts/wait_for_land_slot.py --max-in-flight 1 --timeout 480` -> exit 0 (EXIT_SLOT_FREE) when no land is in flight, observed live.
- `uv run python scripts/wait_for_land_slot.py --max-in-flight 1 --timeout 3 --fleet-status-cmd "python3 /tmp/fake_land_busy.py"` (fake probe always reporting 5 in flight) -> exit 1 (EXIT_TIMEOUT), observed live.
- `_derive_post_land_sweep_budget_s(Path('.'))` -> 300, matching the ticket's cited estimated_work_s.
- `_resolve_land_lock_wait_budget_s(root)` with FROB_LAND_DEADLINE_S unset -> Ok(500.0); with FROB_LAND_DEADLINE_S=540 -> Ok(240.0), matching min(500, 540-300).

Filed: none.
Gates: gate:SCOPE clean (0 errors) for this ticket's touched set. Repo-wide
DRIFT/SEC/PERF/lint/cycle failures observed during `frob check --only
<stage>` are pre-existing and outside this ticket's scope
(docs/guides/agent-playbook.md only) -- not introduced by this change.
gate:PRE001 read stale in an unscoped `--only gates-fast` invocation after
`frob ticket sweep T-2779`; `load_prework`/`active_ticket` called directly
against the worktree root both resolve correctly (digest matches, sweep
found), so this is a pre-existing check-invocation quirk, not a defect in
this ticket's own state.
