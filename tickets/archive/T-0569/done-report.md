## Done report

Added ratchet pools (frob.gates._ratchet, new self-contained module): a
tracked-in-git baseline (frob-ratchet.lock.json, same "committed summary
outside .gitignore" posture as frob-coverage.lock.json) per rule id.
snapshot_ratchet merges given finding keys into a rule's baseline,
stamping only genuinely new keys with today's date (idempotent re-run).
clear_ratchet_entry removes one baselined entry, always demanding a
disposition reason (Err(ClearReasonMissing) on blank) -- the same
frob:waive discipline applied to a whole pool instead of one inline
comment. resolve_ratchet_severity is the severity-resolution contract:
warn if a finding key is already baselined for its rule, error if not.
ratchet_enabled_rules reads opt-in rule ids from [gates.ratchet] rules in
frob.toml (empty/absent = no rule ratcheted, same missing-is-default
posture as load_arch_config).

CLI: frob pool snapshot RULE --key KEY [--key KEY ...] and frob pool
clear RULE --key KEY --reason TEXT, wired through app/pool_runner.py,
app/app.py's dispatch table, app/config.py's Subcommand enum/AppConfig
fields, and __main__.py's parser. Manually verified end to end (snapshot
then clear against a real frob-ratchet.lock.json).

Non-vacuous test fixture (tests/test_gates_ratchet.py) proves the
ticket's own acceptance directly: a baselined finding stays warn
(test_baselined_finding_stays_warn), a fresh finding of the same rule
errors (test_fresh_finding_errors), and clearing a baseline entry without
a reason is rejected while clearing it WITH a reason both removes the
entry and flips its severity back to error
(test_clearing_with_reason_removes_entry_and_it_now_errors). CLI-level
tests (tests/test_pool_runner.py) cover the same round-trip through
pool_runner.run.

Cut honestly disclosed: NOT wired into any live gate's severity
resolution this pass -- src/frob/gates/__init__.py's per-rule severity
dispatch is large shared surface a concurrent wave owns this session.
Not Filed T-draft-3a0b0b5f (never refiled) (own scope: src/frob/gates/__init__.py's one call
site, frob.toml, docs/modules/gates.md) to pick a real rule (e.g. INV006
or PII010), opt it into [gates.ratchet], and call
resolve_ratchet_severity at that gate's severity decision -- the storage
format, CLI, and contract are complete and tested; the follow-up only
needs to call the existing function at one site.

Scope was widened twice: once to cover the CLI-wiring files (app/*,
__main__.py) the ticket's own prose named but the frontmatter scope
list did not carry, and once more for a SCOPE001 false-positive: T-0108's
commit-subject exemption requires the covering commit to name the
ticket id, and two earlier same-worktree commits (T-0578/T-0579) omitted
it from the subject line, so their already-landed files re-surfaced
here instead of being exempt. Both scope changes recorded with reasons
via `frob ticket scope`.

### Changed
```
 CHANGELOG.md                    |  12 ++
 docs/commands/cli-vocabulary.md |  65 ++++++
 docs/modules/gates.md           |  53 +++++
 docs/modules/tickets.md         |  80 +++++++-
 frob.toml                       |   9 +
 pyproject.toml                  |   2 +-
 src/frob/__main__.py            | 194 +++++++++++++++++-
 src/frob/app/app.py             |   6 +-
 src/frob/app/config.py          |  20 ++
 src/frob/app/pool_runner.py     |  67 +++++++
 src/frob/app/ticket_runner.py   |  58 +++++-
 src/frob/gates/_ratchet.py      | 248 +++++++++++++++++++++++
 src/frob/tickets/__init__.py    |  78 ++++++++
 src/frob/tickets/_brief.py      | 233 ++++++++++++++++++++++
 src/frob/tickets/_models.py     |   4 +
 tests/test_gates_ratchet.py     | 126 ++++++++++++
 tests/test_pool_runner.py       |  96 +++++++++
 tests/test_tickets.py           |  98 +++++++++
 tests/test_tickets_brief.py     | 226 +++++++++++++++++++++
 tests/unit/test_main_entry.py   |  62 +++++-
 tickets.md                      | 431 +++++++++++++++++++++++++++++++++++++++-
 21 files changed, 2138 insertions(+), 30 deletions(-)
```

### Evidence
- `tests/test_gates_ratchet.py::TestSnapshotRatchet::test_first_snapshot_baselines_every_key` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestSnapshotRatchet::test_second_snapshot_preserves_original_baseline_date` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestSnapshotRatchet::test_writes_committed_lock_file` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestSnapshotRatchet::test_two_rules_do_not_clobber_each_other` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestResolveRatchetSeverity::test_baselined_finding_stays_warn` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestResolveRatchetSeverity::test_fresh_finding_errors` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestResolveRatchetSeverity::test_unratcheted_rule_with_no_pool_is_error` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestClearRatchetEntry::test_clearing_requires_a_reason` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestClearRatchetEntry::test_clearing_with_reason_removes_entry_and_it_now_errors` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestClearRatchetEntry::test_clearing_unknown_key_is_err` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestRatchetEnabledRules::test_missing_toml_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestRatchetEnabledRules::test_reads_configured_rules` (pytest node id, verified passing when recorded)
- `tests/test_gates_ratchet.py::TestRatchetEnabledRules::test_missing_table_is_empty` (pytest node id, verified passing when recorded)
- `tests/test_pool_runner.py::TestPoolSnapshotCli::test_snapshot_baselines_keys` (pytest node id, verified passing when recorded)
- `tests/test_pool_runner.py::TestPoolSnapshotCli::test_snapshot_requires_rule_and_keys` (pytest node id, verified passing when recorded)
- `tests/test_pool_runner.py::TestPoolClearCli::test_clear_removes_entry_with_reason` (pytest node id, verified passing when recorded)
- `tests/test_pool_runner.py::TestPoolClearCli::test_clear_requires_reason` (pytest node id, verified passing when recorded)
- `tests/test_pool_runner.py::TestPoolRunDispatch::test_unknown_command_exits_nonzero` (pytest node id, verified passing when recorded)
