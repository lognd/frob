## Done report

Changed:
- src/frob/tickets/__init__.py::new_ticket -- now scans `_load_merged` (active
  + archive) to allocate the next id instead of `load_all` (active only); a
  malformed archive aborts allocation loudly (Err) rather than being ignored
- src/frob/tickets/__init__.py::_next_ticket_id -- docstring clarified: the
  caller controls which id space is protected against collision

Evidence:
- tests/test_tickets.py::TestArchive::test_new_ticket_id_continues_past_archived_max
  (archives T-0001..T-0136, files a new ticket, asserts id == T-0137 and the
  merged queue still loads -- verified this FAILS on pre-fix code, id comes
  back T-0001, via `git stash push -- src/frob/tickets/__init__.py` then
  rerunning; passes after the fix, stash popped back)
- tests/test_tickets.py::TestArchive::test_new_ticket_fresh_repo_no_archive_file
  (no tickets-archive.md at all -- allocator must not error just because the
  file is absent; first id is T-0001)
- tests/test_tickets.py::TestArchive::test_new_ticket_corrupt_archive_fails_loudly
  (archive with a ticket marker but no yaml frontmatter fence -- `new_ticket`
  must return Err, not silently skip the unreadable archive and allocate
  a possibly-colliding id; vacuous-pass doctrine)

Filed: none (no out-of-scope work discovered).

Gates:
- `uv run pytest tests/test_tickets.py -q` -- 78 passed
- `uv run ruff check src/frob/tickets/__init__.py tests/test_tickets.py` -- clean
- `uv run ruff format --check src/frob/tickets/__init__.py tests/test_tickets.py` -- clean
- `uv run ty check src/frob/tickets/__init__.py` -- clean
- `frob check --ticket T-0140` -- exit 0 ("pass gates 87 violation(s), 55
  waived"); the 87/55 total is repo-wide baseline noise unlocked by
  `make core` building strata_core in this worktree (native-extension-gated
  TEST/PERF checks that don't run without it) -- zero unwaived violations
  landed in src/frob/tickets/__init__.py or tests/test_tickets.py, the only
  files this diff touches besides this ledger entry
- Evidence recorded via `frob ticket evidence T-0140 ...` after building the
  native extension in this worktree (`make core`; `import strata_core`
  succeeded afterward) so `pytest --collect-only` spans the whole repo
  cleanly

Not closed, not committed, per instructions.
