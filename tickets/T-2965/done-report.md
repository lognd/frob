## Done report

T-2965 -- frob ticket set-parent needs a --clear path to detach a
mis-parented ticket to root

STATUS: DONE (all in-scope work committed, evidence bound, worktree and
root clean). T-4521 landed on dev (c9955a58f), which released the lease
on src/frob/_cli_parsers/_ticket/_metadata.py, so the previously-BLOCKED
CLI-wiring leaf is now finished too.

Worktree: /home/logan/projects/frob/.claude/worktrees/t-2965
Branch: t-2965
Final HEAD: a5e6dbdfa (chore(tickets): record evidence for T-2965)

Commit history for this ticket (oldest to newest):
  6312c43e9  chore(tickets): record T-2965 start transition
  f8641576d  feat(tickets): add set_parent --clear path to detach to root
  5e40edff0  Merge branch 'dev' into t-2965  (picked up T-4521's land,
             released the _cli_parsers/_ticket/_metadata.py lease;
             merge was clean, no conflicts on CHANGELOG.md/uv.lock/
             .frob-release.json/pyproject.toml or anything else)
  2f15bc482  chore(tickets): scope T-2965 (added
             src/frob/_cli_parsers/_ticket/_metadata.py once T-4521's
             lease released)
  f24910e0d  feat(tickets): wire --clear on frob ticket set-parent CLI
  a5e6dbdfa  chore(tickets): record evidence for T-2965

What changed, by file:

1. src/frob/tickets/_models.py
   Added TicketError.ParentAlreadyRoot -- the refusal for `--clear`
   called on a ticket that already has parent=None.

2. src/frob/tickets/_setters.py
   set_parent(root, ticket_id, parent_id: str | None, *, reason) now
   accepts None: refuses Err(ParentAlreadyRoot) if already root,
   otherwise writes parent=None through the same ledger-locked,
   land-in-progress-refusing, single-writer path the attach case
   already used, skipping _validate_parent_edge entirely for a null
   target. _write_parent_change mirrors the same behavior.

3. src/frob/app/config.py / src/frob/app/_config_external.py
   AppConfig.ticket_parent_clear: bool = False, registered in
   _BOOL_FLAGS (same family as the existing ticket_anchor_clear
   precedent).

4. src/frob/app/ticket_runner/_mutate.py
   _set_parent(root, cfg) now enforces "exactly one of parent-id or
   --clear" itself (argparse's add_mutually_exclusive_group cannot
   hold a positional, so this could not be enforced at parse time):
   refuses (sys.exit(1)) if both cfg.ticket_parent_clear and
   cfg.ticket_parent_id_value are set, or if neither is set. Forwards
   parent_id=None to set_parent when --clear is given.

5. src/frob/_cli_parsers/_ticket/_metadata.py
   _add_ticket_set_parent_parser: ticket_parent_id_value is now
   nargs="?" (optional), and a new --clear flag (dest
   ticket_parent_clear, store_true) was added. Docstring explains why
   the mutual-exclusion check lives in _set_parent instead of an
   argparse mutually-exclusive-group.

6. docs/modules/tickets.md
   Updated the frob:describes-tracked set_parent signature/doc block
   under #public-api for the new `parent_id: str | None` parameter and
   --clear/ParentAlreadyRoot behavior.

7. tests/test_tickets_parent.py
   - TestSetParentClear (6 cases): library-level set_parent(..., None,
     ...) behavior -- detach, triage entry, already-root refusal,
     reason-missing refusal, skips structural validation, archived
     ticket routing.
   - TestSetParentCliClearFlag (6 cases): CLI-surface coverage --
     parser accepts --clear alone, parent-id alone, and both together
     (documents that argparse itself does not refuse the conflict);
     _set_parent handler refuses both-given and neither-given: exits
     with code 1; handler actually detaches via an AppConfig shaped
     like what from_external would build from parsed --clear args.

Verification (ruff/ty/pytest only, per coordinator instruction -- no
frob check, no done-report, no land):
   ruff check <all touched files>: All checks passed!
   ruff format --check <all touched files>: clean after one
     `ruff format` auto-pass (2 files needed reformatting, applied)
   ty check <all touched files>: All checks passed!
   PYTHONPATH=<WT>/src pytest -q -p no:cacheprovider -p no:xdist
     tests/test_tickets_parent.py
     -> SUITE-RESULT: exitstatus=0 collected=27 failed=0
     (21 pre-existing/first-pass + 6 new TestSetParentCliClearFlag
     cases)

Evidence bound (frob ticket evidence T-2965 <node-ids...> --base-ref
dev --path <WT>): the ticket carries no numbered acceptance-criteria
list (no `acceptance:` entries in its frontmatter), so evidence was
bound as a flat list rather than per --accepts INDEX. All 12 new test
node ids resolved and are now recorded:
   tests/test_tickets_parent.py::TestSetParentClear::
     test_clear_detaches_to_root
     test_clear_records_a_triage_entry
     test_clear_on_already_root_ticket_refuses
     test_clear_requires_a_reason
     test_clear_skips_structural_validation
     test_clear_on_archived_ticket_routes_to_archive_path
   tests/test_tickets_parent.py::TestSetParentCliClearFlag::
     test_parser_accepts_clear_with_no_parent_id
     test_parser_accepts_parent_id_with_no_clear
     test_parser_accepts_both_together_argparse_alone_does_not_refuse
     test_handler_refuses_both_parent_id_and_clear
     test_handler_refuses_neither_parent_id_nor_clear
     test_handler_clear_detaches_via_the_cli_config_shape

Final state:
   git -C <WT> status --short: empty
   git -C /home/logan/projects/frob status --short: empty
   HEAD: a5e6dbdfa

No frob check, no done-report, no land run, per coordinator
instruction. Reporting READY.

### Changed
```
 docs/modules/tickets.md                    |   9 +-
 src/frob/_cli_parsers/_ticket/_metadata.py |  53 ++++++--
 src/frob/app/_config_external.py           |   2 +
 src/frob/app/config.py                     |   6 +
 src/frob/app/ticket_runner/_mutate.py      |  33 ++++-
 src/frob/tickets/_models.py                |   6 +
 src/frob/tickets/_setters.py               |  58 +++++---
 tests/test_tickets_parent.py               | 208 +++++++++++++++++++++++++++++
 tickets/T-2965/ticket.md                   |  13 ++
 9 files changed, 351 insertions(+), 37 deletions(-)
```

### Evidence
- `tests/test_tickets_parent.py::TestSetParentClear::test_clear_detaches_to_root` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentClear::test_clear_records_a_triage_entry` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentClear::test_clear_on_already_root_ticket_refuses` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentClear::test_clear_requires_a_reason` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentClear::test_clear_skips_structural_validation` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentClear::test_clear_on_archived_ticket_routes_to_archive_path` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_parser_accepts_clear_with_no_parent_id` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_parser_accepts_parent_id_with_no_clear` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_parser_accepts_both_together_argparse_alone_does_not_refuse` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_handler_refuses_both_parent_id_and_clear` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_handler_refuses_neither_parent_id_nor_clear` (pytest node id, verified passing when recorded)
- `tests/test_tickets_parent.py::TestSetParentCliClearFlag::test_handler_clear_detaches_via_the_cli_config_shape` (pytest node id, verified passing when recorded)

### Captured claims
- tests: 12 passed (from 12 evidence id(s))
- gates: unmeasured (no parsable gate-summary from a fresh check)
